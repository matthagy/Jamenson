'''Generates Python code from intermediate representation.
   Uses byteplay (by Noam Raphael) for the low-level assembly of
   Python bytecode
'''

from __future__ import absolute_import
from __future__ import with_statement

import byteplay as B
import itertools

from ..runtime.ctxsingleton import CtxSingleton
from ..runtime.multimethod import MultiMethod, defmethod

from . import ir as I
from . import bind
from .walk import IRWalker
from .util import flatten_lists_and_generators
from .asm import first_lineno, finalize_instructions, optimize_instructions
from .validate import validate
from .annotate import annotate
from .optimize import optimize
from .purity import purep
from .declare import OptimizationTradeoffs


class CodeGenState(CtxSingleton):

    def _cxs_setup_top(self):
        self.tag_labels = None
        self.name_translations = None
        self.tradeoffs = None
        self._cxs_setup_aux()

    def _cxs_copy(self, **kwds):
        cp = self._cxs_super._cxs_copy(**kwds)
        cp._cxs_setup_aux()
        return cp

    def _cxs_setup_aux(self):
        self.tag_labels = self.tag_labels or {}
        self.name_translations = self.name_translations or {}
        self.tradeoffs = self.tradeoffs or OptimizationTradeoffs()

state = CodeGenState()

def compile_to_code(ir, **kwds):
    '''Compile to a code object that can be eval_ed to evaluate
       the scemantics of the passed in ir.
       ir is modified inplace
    '''
    with state.top(tag_labels=None, **kwds):
        return construct_code(construct_compilation_ir(ir))

def evaluate_ir(ir, **kwds):
    return eval(compile_to_code(ir, **kwds))

def construct_compilation_ir(ir):
    validate(ir)
    annotate(ir)
    ir = optimize(ir, level=state.tradeoffs.speed)
    ir = translate_bindings(ir)
    return ir

def construct_code(ir):
    free_bindings, cell_bindings = find_non_local_bindings(ir)
    free_bindings -= cell_bindings
    if free_bindings:
        compilation_error(ir, "can't construct_code for ir with free bindings %s",
                          ','.join(sorted(binding.symbol for binding in free_bindings)))
    ops = compile_operations(ir)
    return compile_code(ops, (), (), False, False,
                        None, ir.filename,
                        min(ir.lineno, first_lineno(ops)),
                        None)

def compile_operations(ir):
    ops = list(flatten_lists_and_generators(genops(ir)))
    ops = finalize_instructions(ops)
    if state.tradeoffs.speed >= 1:
        ops = optimize_instructions(ops)
    return ops



# # # # # # # # # # # # #
# Operation Generation  #
# # # # # # # # # # # # #

def genops(ir):
    if ir.lineno is not None:
        yield B.SetLineno, ir.lineno
    yield generate_operations(ir)

generate_operations = MultiMethod('generate_operations',
                                  signature='node',
                                  doc='''
                                  ''')

@defmethod(generate_operations, [I.nop])
def meth(n):
    if not n.result_ignored:
        yield B.LOAD_CONST, None

@defmethod(generate_operations, [I.constant])
def meth(c):
    if not c.result_ignored:
        yield B.LOAD_CONST, c.value


# # # # # # #
# Bindings  #
# # # # # # #

def get_name_translation(binding):
    return state.name_translations[binding]

def get_use_translation(bu):
    return state.name_translations[bu.binding]

def binding_op(bu, loc_op, cell_op, free_op):
    ut = bind.get_binding_use_type(bu)
    if ut == bind.BND_GLOBAL:
        compilation_error(None, 'global binding %r not translated', bu.symbol.print_form)
    name = get_use_translation(bu)
    if ut == bind.BND_LOCAL:
        yield loc_op, name
    elif ut == bind.BND_CELL:
        yield cell_op, name
    elif ut == bind.BND_FREE:
        yield free_op, name
    else:
        raise RuntimeError("unkown binding %s" % (bu,))

def generate_read_binding(binding):
    yield binding_op(binding, B.LOAD_FAST, B.LOAD_DEREF, B.LOAD_DEREF)

def generate_write_binding(binding):
    yield binding_op(binding, B.STORE_FAST, B.STORE_DEREF, B.STORE_DEREF)

def generate_delete_binding(binding):
    if bind.get_binding_use_type(binding) is not bind.BND_LOCAL:
        compilation_error(binding, 'deleting non-local binding')
    yield binding_op(binding, B.DELETE_FAST, None, None)

@defmethod(generate_operations, [I.read_binding])
def meth(rb):
    if not rb.result_ignored:
        yield generate_read_binding(rb.binding)

@defmethod(generate_operations, [I.write_binding])
def meth(wb):
    yield genops(wb.value)
    if not wb.result_ignored:
        yield B.DUP_TOP, None
    yield generate_write_binding(wb.binding)

@defmethod(generate_operations, [I.delete_binding])
def meth(db):
    yield generate_delete_binding(db.binding)
    if not db.result_ignored:
        yield B.LOAD_CONST, None


# # # # # # # # # # #
# Unary Operations  #
# # # # # # # # # # #

unary_op_map = {
    I.neg      : B.UNARY_NEGATIVE,
    I.pos      : B.UNARY_POSITIVE,
    I.not_     : B.UNARY_NOT,
    I.convert  : B.UNARY_CONVERT,
    I.invert   : B.UNARY_INVERT,
    I.get_iter : B.GET_ITER}

@defmethod(generate_operations, [I.unary_base])
def meth(ub):
    if ub.result_ignored:
        yield generate_eval_and_drop_unless_pure(ub.op)
    else:
        yield genops(ub.op)
        yield unary_op_map[type(ub)], None

# # # # # # # # # # #
# Binary Operations #
# # # # # # # # # # #

binary_op_map = {
    I.add           : B.BINARY_ADD,
    I.subtract      : B.BINARY_SUBTRACT,
    I.multiply      : B.BINARY_MULTIPLY,
    I.divide        : B.BINARY_DIVIDE,
    I.floor_divide  : B.BINARY_FLOOR_DIVIDE,
    I.true_divide   : B.BINARY_TRUE_DIVIDE,
    I.modulo        : B.BINARY_MODULO,
    I.iadd          : B.INPLACE_ADD,
    I.isubtract     : B.INPLACE_SUBTRACT,
    I.imultiply     : B.INPLACE_MULTIPLY,
    I.idivide       : B.INPLACE_DIVIDE,
    I.ifloor_divide : B.INPLACE_FLOOR_DIVIDE,
    I.itrue_divide  : B.INPLACE_TRUE_DIVIDE,
    I.imodulo       : B.INPLACE_MODULO,
    I.lshift        : B.BINARY_LSHIFT,
    I.rshift        : B.BINARY_RSHIFT,
    I.binand        : B.BINARY_AND,
    I.binor         : B.BINARY_OR,
    I.binxor        : B.BINARY_XOR,
    I.ilshift       : B.INPLACE_LSHIFT,
    I.irshift       : B.INPLACE_RSHIFT,
    I.ibinand       : B.INPLACE_AND,
    I.ibinor        : B.INPLACE_OR,
    I.ibinxor       : B.INPLACE_XOR}

cmp_op_map = {
    I.gt              : '>',
    I.ge              : '>=',
    I.eq              : '==',
    I.ne              : '!=',
    I.le              : '<=',
    I.lt              : '<',
    I.in_             : 'in',
    I.notin           : 'not in',
    I.is_             : 'is',
    I.isnot           : 'is not',
    I.exception_match : 'exception match'}

@defmethod(generate_operations, [I.binary_base])
def meth(bb):
    if bb.result_ignored:
        yield generate_eval_and_drop_unless_pure(bb.lop)
        yield generate_eval_and_drop_unless_pure(bb.rop)
    else:
        yield genops(bb.lop)
        yield genops(bb.rop)
        try:
            binop = binary_op_map[type(bb)]
            value = None
        except KeyError:
            binop = B.COMPARE_OP
            value = cmp_op_map[type(bb)]
        yield binop, value

# # # # # # # #
# Attributes  #
# # # # # # # #

@defmethod(generate_operations, [I.attrget])
def meth(ag):
    if ag.result_ignored:
        yield generate_eval_and_drop_unless_pure(ag.obj)
    else:
        yield genops(ag.obj)
        yield B.LOAD_ATTR, ag.name

@defmethod(generate_operations, [I.attrset])
def meth(ats):
    yield genops(ats.value)
    if not ats.result_ignored:
        yield B.DUP_TOP, None
    yield genops(ats.obj)
    yield B.STORE_ATTR, ats.name

@defmethod(generate_operations, [I.attrdel])
def meth(ad):
    yield genops(ats.obj)
    yield B.DELETE_ATTR, ad.name
    if not ad.result_ignored:
        yield B.LOAD_CONST, None

# # # # #
# Item  #
# # # # #

@defmethod(generate_operations, [I.getitem])
def meth(gi):
    if gi.result_ignored:
        yield generate_eval_and_drop_unless_pure(gi.op)
        yield generate_eval_and_drop_unless_pure(gi.item)
    else:
        yield genops(gi.op)
        yield genops(gi.item)
        yield B.BINARY_SUBSCR, None

@defmethod(generate_operations, [I.setitem])
def meth(si):
    yield genops(si.value)
    if not si.result_ignored:
        yield B.DUP_TOP, None
    yield genops(si.op)
    yield genops(si.item)
    yield B.STORE_SUBSCR, None

@defmethod(generate_operations, [I.delitem])
def meth(di):
    yield genops(di.op)
    yield genops(di.item)
    yield B.DELETE_SUBSCR, None
    if not di.result_ignored:
        yield B.LOAD_CONST, None

# # # # #
# Slice #
# # # # #

@defmethod(generate_operations, [I.buildslice])
def meth(bs):
    if bs.result_ignored:
        for child in iter_children(bs):
            yield generate_eval_and_drop_unless_pure(child)
    else:
        yield genops(bs.start)
        yield genops(bs.stop)
        yield genops(bs.step)
        yield B.BUILD_SLICE, 3

@defmethod(generate_operations, [I.unpack_seq])
def meth(us):
    yield genops(us.seq)
    if not us.result_ignored:
        yield B.DUP_TOP, None
    yield B.UNPACK_SEQUENCE, len(us.places)
    for binding in us.places:
        yield generate_write_binding(binding)


# # # # #
# Progn #
# # # # #

@defmethod(generate_operations, [I.progn])
def meth(p):
    exprs = list(p.exprs)
    if not exprs:
        if not p.result_ignored:
            yield B.LOAD_CONST, None
    else:
        return_index = len(exprs) - 1
        if p.result_ignored:
            return_index += 1
        for index,expr in enumerate(exprs):
            assert expr.result_ignored == (index < return_index)
            yield genops(expr)

# # # # #
# Call  #
# # # # #

@defmethod(generate_operations, [I.call])
def meth(c):
    if c.result_ignored and purep(c):
        return
    yield genops(c.callee)
    for arg in c.args:
        yield genops(arg)
    for name,kwd in zip(c.kwd_names, c.kwd_values):
        yield B.LOAD_CONST, name
        yield genops(kwd)
    if c.star_args:
        yield genops(c.star_args)
    if c.star_kwds:
        yield genops(c.star_kwds)
    arg_op = len(c.args) + (len(c.kwd_values)<<8)
    if c.star_args and c.star_kwds:
        yield B.CALL_FUNCTION_VAR_KW, arg_op
    elif c.star_kwds:
        yield B.CALL_FUNCTION_KW, arg_op
    elif c.star_args:
        yield B.CALL_FUNCTION_VAR, arg_op
    else:
        yield B.CALL_FUNCTION, arg_op
    if c.result_ignored:
        yield B.POP_TOP, None


# # # # # # # #
# Conditional #
# # # # # # # #

@defmethod(generate_operations, [I.if_])
def meth(c):
    assert c.then.result_ignored == c.result_ignored
    assert c.else_.result_ignored == c.result_ignored
    lfalse = B.Label()
    ljoin = B.Label()
    yield genops(c.condition)
    yield B.JUMP_IF_FALSE, lfalse
    yield B.POP_TOP, None
    yield genops(c.then)
    yield B.JUMP_FORWARD, ljoin
    yield lfalse, None
    yield B.POP_TOP, None
    yield genops(c.else_)
    yield ljoin, None


# # # # # #
# Return  #
# # # # # #

@defmethod(generate_operations, [I.return_])
def meth(r):
    yield genops(r.value)
    #really only need this for consistent stack depth
    if not r.result_ignored:
        B.DUP_TOP, None
    yield B.RETURN_VALUE, None


# # # # #
# Yield #
# # # # #

@defmethod(generate_operations, [I.yield_])
def meth(y):
    yield genops(y.value)
    yield B.YIELD_VALUE, None
    if y.result_ignored:
        yield B.POP_TOP, None


# # # # # # # # # # #
# Exception Raising #
# # # # # # # # # # #

@defmethod(generate_operations, [I.raise0])
def meth(r):
    yield B.RAISE_VARARGS, 0
    if not r.result_ignored:
        yield B.LOAD_CONST, None

@defmethod(generate_operations, [I.raise1])
def meth(r):
    yield genops(r.value)
    if not r.result_ignored:
        yield B.DUP_TOP, None
    yield B.RAISE_VARARGS, 1

@defmethod(generate_operations, [I.raise3])
def meth(r):
    yield genops(r.type)
    if not r.result_ignored:
        yield B.DUP_TOP, None
    yield genops(r.value)
    yield genops(r.traceback)
    yield B.RAISE_VARARGS, 3


# # # # # # # # # # # #
# Exception Catching  #
# # # # # # # # # # # #

@defmethod(generate_operations, [I.trycatch])
def meth(tc):
    lhandler = B.Label()
    ljoin = B.Label()
    yield B.SETUP_EXCEPT, lhandler
    yield genops(tc.body)
    yield B.POP_BLOCK, None
    yield B.JUMP_FORWARD, ljoin
    yield lhandler, None
    for b in [tc.exc_type_binding, tc.exc_value_binding, tc.exc_tb_binding]:
        if b is None:
            yield B.POP_TOP, None
        else:
            yield generate_write_binding(b)
    yield genops(tc.catch)
    yield ljoin, None
    if not tc.result_ignored:
        yield B.LOAD_CONST, None


# # # # # # # #
# Try Finally #
# # # # # # # #

@defmethod(generate_operations, [I.tryfinally])
def meth(tf):
    handler = B.Label()
    yield B.SETUP_FINALLY, handler
    yield genops(tf.body)
    yield B.POP_BLOCK, None
    yield B.LOAD_CONST, None
    yield handler, None
    yield genops(tf.finally_)
    yield B.END_FINALLY, None
    if not tf.result_ignored:
        yield B.LOAD_CONST, None

# # # # # # #
# Tag Body  #
# # # # # # #

def get_tag_label(tag):
    try:
        return state.tag_labels[tag]
    except KeyError:
        assert tag.symbol is not None
        lbl = state.tag_labels[tag] = B.Label()
        return lbl

@defmethod(generate_operations, [I.tagbody])
def meth(tb):
    for tag in tb.tags:
        if tag.symbol is not None:
            yield get_tag_label(tag), None
        yield genops(tag.body)
    if not tb.result_ignored:
        yield B.LOAD_CONST, None

@defmethod(generate_operations, [I.go])
def meth(go):
    yield B.JUMP_ABSOLUTE, get_tag_label(go.tag)
    if not go.result_ignored:
        yield B.LOAD_CONST, None

@defmethod(generate_operations, [I.foriter])
def meth(fi):
    yield genops(fi.iter)
    yield B.FOR_ITER, get_tag_label(fi.tag)
    if not fi.result_ignored:
        yield B.DUP_TOP, None
        yield B.ROT_TWO, None
    yield generate_write_binding(fi.binding)
    yield B.POP_TOP, None #pop the iter

@defmethod(generate_operations, [I.toplevel])
def meth(top):
    yield genops(top.expression)

# # # # # # #
# Function  #
# # # # # # #

load_function_code = MultiMethod()

get_function_free_bindings = MultiMethod()

seen = set()
@defmethod(get_function_free_bindings, [I.function])
def meth(f):
    free_bindings, cell_bindings = find_non_local_bindings(f.body)
    for bu in I.iter_bindings(f):
        if bind.get_binding_use_type(bu) == bind.BND_CELL:
            cell_bindings.add(bu.binding)
    free_bindings -= cell_bindings
    return free_bindings

# @defmethod(get_function_free_bindings, [I.non_const_function])
# def meth(f):
#     return f.free_bindings

def get_canonical_free_bindings(f):
    return sorted(get_function_free_bindings(f),
                  key=get_name_translation)

@defmethod(load_function_code, [I.function])
def meth(f):
    free_bindings = get_canonical_free_bindings(f)
    ops = compile_operations(f.body)
    args = map(get_use_translation, f.args)
    args += map(get_use_translation, f.kwds)
    if f.star_args:
        args.append(get_use_translation(f.star_args))
    if f.star_kwds:
        args.append(get_use_translation(f.star_kwds))
    code = compile_code(ops, map(get_name_translation, free_bindings),
                        args,
                        not not f.star_args,
                        not not f.star_kwds,
                        f.name, f.filename,
                        min(f.lineno, first_lineno(ops)),
                        f.doc)
    yield B.LOAD_CONST, code

# @defmethod(load_function_code, [I.non_const_function])
# def meth(f):
#     yield generate_read_binding(rb.binding)

@defmethod(generate_operations, [I.basefunction])
def meth(f):
    if f.result_ignored:
        #just evaluate defaults with side effects
        for d in f.defaults:
            yield generate_eval_and_drop_unless_pure(d)
        return
    for d in f.defaults:
        yield genops(d)
    free_bindings = get_canonical_free_bindings(f)
    if free_bindings:
        for fr in free_bindings:
            yield B.LOAD_CLOSURE, state.name_translations[fr]
        yield B.BUILD_TUPLE, len(free_bindings)
    yield load_function_code(f)
    yield (B.MAKE_CLOSURE if free_bindings else
           B.MAKE_FUNCTION), len(f.defaults)

# # # # # # # # # #
# Pre-Evaluation  #
# # # # # # # # # #

@defmethod(generate_operations, [I.preeval])
def meth(pe):
    compilation_error(pe, '%s form not transformed', pe.__class__.__name__)

# # # # # #
# Import  #
# # # # # #

@defmethod(generate_operations, [I.import_name])
def meth(im):
    yield B.LOAD_CONST, -1
    yield B.LOAD_CONST, None
    yield B.IMPORT_NAME, im.name
    if im.result_ignored:
        yield B.POP_TOP, None


# # # # # # # # # # # # # # # # # # # #
# Tree-wise Lexical Binding Utilities #
# # # # # # # # # # # # # # # # # # # #

class NonLocalNameFinder(IRWalker):

    descend_into_functions = True

    def __init__(self):
        IRWalker.__init__(self)
        self.cell_bindings = set()
        self.free_bindings = set()

    def visit_node(self, node):
        for bu in I.iter_bindings(node):
            bt = bind.get_binding_use_type(bu)
            if bt == bind.BND_CELL:
                self.cell_bindings.add(bu.binding)
            elif bt == bind.BND_FREE:
                self.free_bindings.add(bu.binding)
        self.visit_children(node)


def find_non_local_bindings(node):
    nlbf = NonLocalNameFinder()
    nlbf.visit(node)
    return nlbf.free_bindings, nlbf.cell_bindings


class LocalNameTranslator(IRWalker):

    descend_into_functions = True

    def __init__(self):
        IRWalker.__init__(self)
        self.local_names = set()

    def visit_node(self, node):
        for bu in I.iter_bindings(node):
            if bu.binding not in state.name_translations:
                if bind.get_binding_use_type(bu) is not bind.BND_GLOBAL:
                    name = self.new_local_name(bu.binding.symbol.print_form)
                    state.name_translations[bu.binding] = name
        self.visit_children(node)

    def new_local_name(self, basename):
        for trans in self.iter_translations(basename):
            if trans not in self.local_names:
                self.local_names.add(trans)
                return trans

    @staticmethod
    def iter_translations(basename):
        yield basename #first try non-translated
        for i in itertools.count(1):
            #use ( and ) in compiler generated names as
            #such symbols cannot (easily) be read in
            yield '%s(%d)' % (basename, i)


def translate_bindings(ir):
    LocalNameTranslator().visit(ir)
    return ir


# # # # # # # # # # # # # # # # # # #
# Remove locations from other files #
# # # # # # # # # # # # # # # # # # #

class LocationStripper(IRWalker):

    descend_into_functions = True

    def __init__(self, filename):
        IRWalker.__init__(self)
        self.filename = filename

    def visit_node(self, node):
        if node.filename is not self.filename or self.filename is None:
            node.filename = None
            node.lineno = None
            node.colno = None
        self.visit_children(node)

def strip_locations_from_other_files(node, filename):
    LocationStripper(filename).visit(node)

def strip_all_locatons(node):
    LocationStripper(None).visit(node)


# # # # # # #
# Utilities #
# # # # # # #

class CompilationError(Exception):

    def __init__(self, ir, msg):
        self.ir = ir
        self.msg = msg

    def __str__(self):
        if not self.ir:
            return self.msg
        return '%s: %s' % (I.ir_location_str(self.ir), self.msg)

def compilation_error(ir=None, msg='error', *args):
    raise CompilationError(ir, msg%args if args else msg)

def generate_eval_and_drop(node):
    node.result_ignored = True
    yield genops(node)

def generate_eval_and_drop_unless_pure(node):
    if not purep(node):
        yield generate_eval_and_drop(node)

def compile_code(ops, freevars, args, varargs, varkwargs,
                 name, filename, firstlineno, docstring):
    ops = list(ops)
    c = B.Code(ops, freevars, args, varargs, varkwargs, True,
               name or '<jamenson_expression>',
               filename or '<string>',
               firstlineno or 0,
               docstring or '')
    try:
        return c.to_code()
    except Exception:
        B.printcodelist(ops)
        raise
