'''Translation from expression to intermediate representation (ir)
   Handles lexical scoping of symbols and macro expansion
'''

from __future__ import absolute_import
from __future__ import with_statement

import sys
from functools import partial

from ..runtime.multimethod import MultiMethod, defmethod

from ..runtime.ctxsingleton import CtxSingleton
from ..runtime.symbol import (Symbol, get_sys_symbol, keywordp, attributep,
                              make_keyword)
from ..runtime.cons import Cons, nil, well_form_list_p
from ..runtime.macro import MacroFunction
from ..runtime.builtins import builtinp, get_builtin

from . import ir as I
from . import bind
from .pkg import get_compiler_symbol
from .resolution import compile_time_resolve, UnresolvableError
# import for side effects
from . import untranslate


class TranslationState(CtxSingleton):

    def _cxs_setup_top(self):
        self.translation_table = default_translation_table.copy()
        self.recursion_depth = 0
        self.form_locations = None
        self.filename = None
        self.scope = None
        self.tag_bodies_stack = None
        self.current_loc = None
        self.macro_translation_exception_handler = None
        self._cxs_setup_aux()

    def _cxs_copy(self, **kwds):
        cp = self._cxs_super._cxs_copy(**kwds)
        cp._cxs_setup_aux()
        return cp

    def _cxs_setup_aux(self):
        self.form_locations = self.form_locations or {}
        self.filename = self.filename or '<string>'
        self.scope = self.scope or bind.Scope(manage_locals=True)
        self.tag_bodies_stack = self.tag_bodies_stack or []
        self.current_loc = self.current_loc or (0,0)
        self.macro_translation_exception_handler = (
            self.macro_translation_exception_handler or
            default_macro_translation_exception_handler)



def translate_top_level_form(form, form_locations=None, filename=None):
    '''top level form -> ir
    '''
    with state.top(form_locations=form_locations, filename=filename,
                   recursion_depth=-1, scope=None, tag_bodies_stack=None):
        top = set_ir_context(I.make_toplevel(scope=state.scope), form)
        top.expression = translate(form)
        return top

# # # # # # # # # # # # # #
# High Level Translators  #
# # # # # # # # # # # # # #

def translate(form):
    '''translates any arbitrary (but valid) expression form into
       the corresponding intermediate representation
    '''
    old_loc = state.current_loc
    new_loc = get_a_form_loc(form)
    if new_loc is not None:
        state.current_loc = new_loc
    old_depth = state.recursion_depth
    state.recursion_depth = old_depth + 1
    if isinstance(form, Symbol):
        ir = translate_symbol(form)
    elif not isinstance(form, Cons) or form is nil:
        ir = translate_constant(form)
    elif not well_form_list_p(form):
        syntax_error(form, "not well formed sexp")
    else:
        ir = translate_sexp(form)
    set_ir_context(ir, form)
    state.current_loc = old_loc
    state.recursion_depth = old_depth
    return ir

def translate_symbol(sym):
    #if builtinp(sym):
    #    return I.make_constant(get_builtin(sym))
    if keywordp(sym) or attributep(sym):
        return I.make_constant(sym)
    binding = state.scope.use_symbol(sym)
    if isinstance(binding, bind.Macrolet):
        syntax_error(sym, "using macrolet symbol %s in non-sexp form", sym)
    elif isinstance(binding, bind.SymbolMacrolet):
        return translate(binding.form)
    elif isinstance(binding, bind.BindingUse):
        return I.make_read_binding(binding)
    else:
        raise RuntimeError("unkown binding type %s" % (binding,))

def translate_constant(op):
    return I.make_constant(op)

def translate_sexp(form):
    if isinstance(form.car, Symbol):
        try:
            special_translator = state.translation_table[form.car]
        except KeyError:
            pass
        else:
            return special_translator(form)
    return translate_call(form)

def translate_call(form):
    '''translate a call form (sexp that is not a speical form)
       handles macros and compiler macros
    '''
    callee_ir = translate_callee(form.car)
    try:
        callee_obj = resolve_callee(callee_ir)
    except UnresolvableError:
        return translate_call_ex(callee_ir, form)
    if isinstance(callee_obj, MacroFunction):
        return translate_macro(callee_obj, form)
    macro = get_compiler_macro(callee_obj)
    if macro:
        return translate_compiler_macro(macro, form)
    return translate_call_ex(callee_ir, form)

def translate_callee(form):
    '''translate callee of a call form with special handeling for
       macrolets and symbolmacrolets
       returns a macro for macrolets, otherwise the translated ir
    '''
    if isinstance(form, Symbol):
        binding = state.scope.use_symbol(form)
        if isinstance(binding, bind.Macrolet):
            return binding.macro
        elif isinstance(binding, bind.SymbolMacrolet):
            return translate_callee(binding.form)
    return translate(form)

def resolve_callee(ir_or_macro):
    if isinstance(ir_or_macro, MacroFunction):
        return ir_or_macro
    return compile_time_resolve(ir_or_macro)

def get_compiler_macro(callee):
    return getattr(callee, 'jamenson_compiler_macro', None)

def check_inline(callee):
    return not not getattr(callee, 'jamenson_inline', False)

rest_sym = get_sys_symbol('&rest')
remaining_sym = get_sys_symbol('&remaining-keys')


def translate_call_ex(callee_ir, form):
    args = []
    kwd_names = []
    kwd_values = []
    star_kwds = None
    star_args = None
    ptr = form.cdr
    while ptr:
        if isinstance(ptr.car, Symbol):
            if ptr.car is remaining_sym:
                if not ptr.cdr:
                    syntax_error(form, '%s without form', remaining_sym)
                if star_kwds:
                    syntax_error(form, 'multiple %s', remaining_sym)
                star_kwds = translate(ptr.cdr.car)
                ptr = ptr.cdr.cdr
                continue
            if ptr.car is rest_sym:
                if not ptr.cdr:
                    syntax_error(form, '%s without form', rest_sym)
                if star_args:
                    syntax_error(form, 'multiple %s', rest_sym)
                star_args = translate(ptr.cdr.car)
                ptr = ptr.cdr.cdr
                continue
            if keywordp(ptr.car):
                kwd = ptr.car.print_form
                if not ptr.cdr:
                    syntax_error(form, 'keyword %r without value', kwd)
                if kwd in kwd_names:
                    syntax_error(form, 'mutliple use of keyword %r', kwd)
                kwd_names.append(kwd)
                kwd_values.append(translate(ptr.cdr.car))
                ptr = ptr.cdr.cdr
                continue
        args.append(translate(ptr.car))
        ptr = ptr.cdr
    return I.make_call(callee=callee_ir, args=args,
                       kwd_names=kwd_names, kwd_values=kwd_values,
                       star_args=star_args, star_kwds=star_kwds)

def wrap_macro_expand(macro, form):
    try:
        return macro.macro_expand(form.cdr)
    except Exception:
        state.macro_translation_exception_handler(form)
        raise

def default_macro_translation_exception_handler(form):
    lineno,colno = get_a_form_loc()
    print >>sys.stderr, 'error expanding form from %s %s.%s' % (state.filename,
                                                                lineno, colno)

def translate_macro(macro, form):
    return post_macro_translate(wrap_macro_expand(macro, form))

def post_macro_translate(result):
    #allow macros to perform their own translation
    if isinstance(result, I.node):
        return result
    return translate(result)

def translate_compiler_macro(macro, form):
    '''special handeling of compiler macro, such that they can return
       a call with the same callee without this leading to recursion
    '''
    trans_form = wrap_macro_expand(macro, form)
    if well_form_list_p(trans_form):
        callee_ir = translate_callee(trans_form.car)
        try:
            callee_obj = resolve_callee(callee_ir)
        except UnresolvableError:
            pass
        else:
            #force call when new form compiler macro resolves to original compiler macro
            macro2 = get_compiler_macro(callee_obj)
            if macro2 is macro:
                return translate_call_ex(callee_ir, trans_form)
    return post_macro_translate(trans_form)


# # # # # # # # # # # # #
# Default Special Forms #
# # # # # # # # # # # # #

default_translation_table = {}

# # # # # # # # # # # # # # # # #
# Simple Binary/Unary Operators #
# # # # # # # # # # # # # # # # #

def make_unary(op, form):
    return op(*translate_args(form, 1))

def make_binary(op, form):
    return op(*translate_args(form, 2))

def register_basic():
    for maker,names in [[make_unary, I.unary_op_names],
                        [make_binary, I.binary_op_names +
                                      I.cmp_op_names]]:
        for name in names:
            sym = get_compiler_symbol(name.strip('_').replace('_','-'))
            default_translation_table[sym] = partial(maker, getattr(I, 'make_' + name))

register_basic()
del register_basic

def register_translator(print_form):
    if isinstance(print_form, Symbol):
        sym = print_form
    else:
        sym = get_compiler_symbol(print_form)
    def inner(func):
        default_translation_table[sym] = func
        return func
    return inner

@register_translator(get_sys_symbol("quote"))
def meth(form):
    return I.make_constant(*parse_args(form, 1))

# # # # # # #
# Bindings  #
# # # # # # #

@register_translator("setq")
def meth(form):
    sym,value = parse_args(form, 2)
    if not isinstance(sym, Symbol):
        syntax_error(form, "setq require symbol as first argument; given %s", sym)
    if builtinp(sym):
        syntax_error(form, "can't write to builtin (yet)")
    binding = state.scope.use_symbol(sym)
    value_ir = translate(value)
    return I.make_write_binding(binding, value_ir)

@register_translator("delq")
def meth(form):
    sym, = parse_args(form, 1)
    if not isinstance(sym, Symbol):
        syntax_error(form, "delq requires symbol; given %s", sym)
    if builtinp(sym):
        syntax_error(form, "can't delete builtins")
    binding = state.scope.use_symbol(sym)
    return I.make_delete_binding(binding)

@register_translator("let")
def meth(form):
    if form.cdr is nil:
        syntax_error(form, "let form without bindings")
    bindings = form.cdr.car
    body_forms = form.cdr.cdr
    if not well_form_list_p(bindings):
        syntax_error(form, "invalid let bindings; must be a well formed list")
    lets = []
    for binding in bindings:
        if isinstance(binding, Symbol):
            sym = binding
            value = nil
        elif not well_form_list_p(binding) or not binding.cdr or binding.cdr.cdr:
            syntax_error(binding, "poorly formatted let binding")
        else:
            sym,value = binding
            if not isinstance(sym, Symbol):
                syntax_error(binding, "first item of let binding must be a symbol")
        lets.append([sym, value])
    syms, values = zip(*lets) if lets else ([],[])
    #translate value forms in old lexical enviroment
    values = map(translate, values)
    with state.top(scope=state.scope.create_child(new_locals=False)):
        asses = []
        for sym,value in zip(syms, values):
            if sym in state.scope.bindings:
                syntax_error(form, "rebinding symbol %s without new lexical binding", sym)
            binding = state.scope.register_and_use_local(sym)
            asses.append(I.make_write_binding(binding, value))
        return I.make_progn(asses + map(translate, body_forms))


# # # # # # # #
# Attributes  #
# # # # # # # #

def parse_attrq(form, mx=2):
    args = parse_args(form, mx)
    sym = args[1]
    if not isinstance(sym, Symbol):
        syntax_error(form, "%s requires symbol as second form; given %s",
                     form.car.print_form, sym)
    return args

@register_translator("getattrq")
def meth(form):
    obj,sym = parse_attrq(form, 2)
    return I.make_attrget(sym.print_form, translate(obj))

@register_translator("setattrq")
def meth(form):
    obj,sym,value = parse_attrq(form, 3)
    return I.make_attrset(sym.print_form, translate(obj), translate(value))

@register_translator("delattrq")
def meth(form):
    obj,sym = parse_attrq(form, 2)
    return I.make_attrdel(sym.print_form, translate(obj))


# # # # #
# Item  #
# # # # #

@register_translator("getitem")
def meth(form):
    return I.make_getitem(*translate_args(form, 2))

@register_translator("setitem")
def meth(form):
    return I.make_setitem(*translate_args(form, 3))

@register_translator("delitem")
def meth(form):
    return I.make_delitem(*translate_args(form, 2))

# # # # #
# Slice #
# # # # #

@register_translator("buildslice")
def meth(form):
    return I.make_buildslice(*[x if x is not None else
                               I.make_constant(None) for x in
                               translate_args(form, 0, 3, fill=None)])

@register_translator('unpack_seq')
def meth(form):
    args = parse_args(form, 1, 1024)
    seq = translate(args.pop(0))
    bindings = []
    for sym in args:
        if not isinstance(sym, Symbol):
            syntax_error(sym, 'invalid binding')
        bindings.append(state.scope.use_symbol(sym))
    return I.make_unpack_seq(seq, bindings)


# # # # # # # # #
# Control Flow  #
# # # # # # # # #

@register_translator("progn")
def meth(form):
    return I.make_progn(map(translate, form.cdr))

@register_translator("if")
def meth(form):
    return I.make_if_(*translate_args(form, 2, 3, fill=nil))

@register_translator("return")
def meth(form):
    return I.make_return_(*translate_args(form, 0, 1, fill=nil))

@register_translator("yield")
def meth(form):
    return I.make_yield_(*translate_args(form, 0, 1, fill=nil))

@register_translator("raise")
def meth(form):
    args = translate_args(form, 0, 3)
    if len(args) == 0:
        return I.make_raise0()
    elif len(args) == 1:
        return I.make_raise1(args[0])
    elif len(args) == 2:
        syntax_error(form, "no scemnatics for raise with 2 arguments")
    else:
        assert len(args) == 3
        return I.make_raise3(*args)

@register_translator("trycatch")
def meth(form):
    args = list(form.cdr)
    if len(args) < 2:
        syntax_error(form, "trycatch takes atleast 2 arguments; given %s", len(args))
    body = translate(args.pop(0))
    bindings = args.pop(0)
    def setup_binding(name, bn):
        if bn is None or bn is nil:
            return None
        if not isinstance(bn, Symbol):
            syntax_error(bindings, 'invalid %s binding: must be symbol; given %s',
                         name, bn)
        return state.scope.register_and_use_local(bn)
    tp, value, tb = parse_args(Cons(nil, bindings), 0, 3, fill=None)
    #create a new scope for catch with these bindings
    with state.top(scope=state.scope.create_child(new_locals=False)):
        tp = setup_binding('type', tp)
        value = setup_binding('value', value)
        tb = setup_binding('tb', tb)
        catch = make_prognish(args)
    return I.make_trycatch(body=body, catch=catch,
                           exc_type_binding=tp,
                           exc_value_binding=value,
                           exc_tb_binding=tb)

@register_translator("tryfinally")
def meth(form):
    return I.make_tryfinally(*translate_args(form, 2))


# # # # # # # # # # # #
# Tag Bodies / Jumps  #
# # # # # # # # # # # #

class TagHolder(object):

    def __init__(self, symbol, form):
        self.tag_forms = []
        body = I.make_progn([])
        set_ir_context(body, form)
        tag = I.make_tag(symbol, body)
        set_ir_context(tag, form)
        self.tag = tag

    def finalize_tag(self):
        self.tag.body.exprs.extend(map(translate, self.tag_forms))
        return self.tag

@register_translator('tagbody')
def meth(form):
    tags_map = {}
    th = TagHolder(None, form)
    ths = [th]
    for el in form.cdr:
        if isinstance(el, Symbol):
            if el in tags_map:
                syntax_error(form, 'multipled defintions of tag %s', el)
            th = TagHolder(el, form)
            ths.append(th)
            tags_map[el] = th.tag
        else:
            th.tag_forms.append(el)
    state.tag_bodies_stack.append(tags_map)
    tags = [th.finalize_tag() for th in ths]
    top_tags_map = state.tag_bodies_stack.pop()
    assert top_tags_map is tags_map
    return I.make_tagbody(tags=tags)

def get_tag(op, form):
    if not isinstance(op, Symbol):
        syntax_error(form, '%s requires symbol; given %s', form.car, op)
    for tag_map in reversed(state.tag_bodies_stack):
        try:
            return tag_map[op]
        except KeyError:
            pass
    syntax_error(form, 'undefined tag %s', op)

@register_translator('go')
def meth(form):
    lbl, = parse_args(form, 1)
    return I.make_go(tag=get_tag(lbl, form))

@register_translator('foriter')
def meth(form):
    lbl, binding, itr = parse_args(form, 3)
    if not isinstance(binding, Symbol):
        syntax_error(form, 'second argument to foriter must be a symbol binding; given %s',
                     binding)
    return I.make_foriter(tag=get_tag(lbl, form),
                          binding=state.scope.use_symbol(binding),
                          iter=translate(itr))


# # # # # # #
# Function  #
# # # # # # #

@register_translator("function")
def meth(form):
    #print 'form', form
    [body_form, name_form, doc_form,
     args, kwds, defaults,
     star_args, star_kwds] = parse_args(form, 1, 8, fill=None)
    name = setup_string_form(name_form, 'name', '<function>')
    doc = setup_string_form(doc_form, 'doc', None)
    default_irs = map(translate, form2seq('defaults', defaults))
    #create new scope for argument bindings
    scope = state.scope.create_child(new_locals=True)
    with state.top(scope=scope):
        args_bindings = setup_argument_bindings(form, 'positional', args)
        kwds_bindings = setup_argument_bindings(form, 'keyword', kwds)
        star_args_binding = setup_star_binding('positional', star_args)
        star_kwds_binding = setup_star_binding('keyword', star_kwds)
        body = translate(body_form)
    if len(default_irs) != len(kwds_bindings):
        syntax_error(form, "invalid number of defaults %d for %d keywords",
                     len(default_irs), len(kwds_bindings))
    func = I.make_function(body=body, name=name, doc=doc,
                           args=args_bindings,
                           kwds=kwds_bindings,
                           defaults=default_irs,
                           star_args=star_args_binding,
                           star_kwds=star_kwds_binding,
                           scope=scope)
    return func

def setup_string_form(form, name, default):
    if isinstance(form, str):
        return form
    elif form in [None, nil]:
        return default
    else:
        syntax_error(form, 'invalid form for %s: string required; given %s',
                     name, form)

def form2seq(name, form):
    try:
        return list(form or [])
    except (TypeError, AttributeError):
        syntax_error(form, 'sequence required for %s list; given %s',
                     name, form)

def setup_argument_bindings(form, binding_name, bindings_form):
    acc = []
    for index,bn in enumerate(form2seq(binding_name, bindings_form)):
        if not isinstance(bn, Symbol):
            syntax_error(form, 'invalid %s argument index %s: must be symbol; given %s',
                         binding_name, index, bn)
        acc.append(state.scope.register_and_use_local(bn))
    return acc

def setup_star_binding(binding_name, form):
    if form in [None, nil]:
        return None
    if not isinstance(form, Symbol):
        syntax_error(form, 'invalid remaining %s arguments must be symbol; given %s',
                     binding_name, form)
    return state.scope.register_and_use_local(form)


# # # # # # #
# Eval When #
# # # # # # #

when_map = {make_keyword('compile-toplevel'):  I.W_COMPILE_TOPLEVEL,
            make_keyword('load-toplevel'):     I.W_LOAD_TOPLEVEL,
            make_keyword('execute'):           I.W_EXECUTE}

@register_translator("eval-when")
def meth(form):
    #if state.recursion_depth:
    #    syntax_error(form, 'eval-when must be top level form')
    situations = form.cdr.car
    if not well_form_list_p(situations):
        syntax_error(situations, 'poorly formatted eval-when situations')
    when = []
    for situation in situations:
        try:
            w = when_map[situation]
        except KeyError:
            syntax_error(situation, 'invalid situation %s for eval-when', situation)
        else:
            when.append(w)
    return I.make_evalwhen(when=when, expression=make_prognish(form.cdr.cdr))

def make_prognish(form):
    exprs = map(translate, form)
    if not exprs:
        return I.make_nop()
    if len(exprs)==1:
        return exprs[0]
    return I.make_progn(exprs)

# # # # # # # # # #
# Pre-Evaluation  #
# # # # # # # # # #

@register_translator("load-time-value")
def meth(form):
    return I.make_load_time_value(make_prognish(form.cdr))

@register_translator("compile-time-value")
def meth(form):
    return I.make_compile_time_value(make_prognish(form.cdr))

# # # # # #
# Import  #
# # # # # #

@register_translator('import-name')
def meth(form):
    name, = parse_args(form, 1)
    if not isinstance(name, str):
        syntax_error(form, 'name must be a string; given %s', name)
    return I.make_import_name(name)

# # # # # # #
# utilities #
# # # # # # #

def get_form_loc(form):
    return state.form_locations.get(id(form), None)

def get_a_form_loc(form=None):
    return (get_form_loc(form) if form is not None else None) or state.current_loc or (None,None)

def set_ir_context(ir, form=None):
    ir.lineno, ir.colno = get_a_form_loc(form)
    ir.filename = state.filename
    return ir

def syntax_error_ex(msg='Syntax Error', form=None, loc=None):
    lineno,colno = loc or get_a_form_loc(form)
    raise SyntaxError(msg, (state.filename, lineno, colno,
                            str(form) if form is not None else ''))

def syntax_error(form, msg='Syntax Error', *args):
    syntax_error_ex(msg%args if args else msg, form)


no_fill = object()
def parse_args(form, mn_args, mx_args=None, fill=no_fill):
    if mx_args is None:
        mx_args = mn_args
    assert mx_args >= mn_args
    args = list(form.cdr)
    if not (mn_args <= len(args) <= mx_args):
        n = mn_args if len(args) < mn_args else mx_args
        syntax_error(form, "%s takes %s %d argument%s; given %d",
                     form.car.print_form,
                     'exactly' if mn_args == mx_args else
                         ('atleast' if len(args) < mn_args else
                          'atmost'),
                     n, 's' if n!=1 else '',
                     len(args))
    if fill is not no_fill:
        while len(args) < mx_args:
            args.append(fill)
    return args

def translate_args(form, mn_args, mx_args=None, fill=no_fill):
    return [translate(arg) if arg is not fill else fill
            for arg in parse_args(form, mn_args, mx_args, fill)]

state = TranslationState()
