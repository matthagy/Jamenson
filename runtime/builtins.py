
from __future__ import absolute_import
from __future__ import with_statement

import __builtin__ as bltns

from .symbol import (resolve_and_export_print_form, get_package,
                     get_symbol_package,
                     get_sys_symbol, set_symbol_cell,
                     set_symbol_cell, get_symbol_cell,
                     packages,
                     symbolp, attributep,
                     register_reset_notifier)
from .cons import register_special_form_emiter, format_cons_raw
from .as_string import as_string, StringingMixin
from .multimethod import defmethod
from . import require
from . import symbol
from . import macro
from . import cons
from . import copy



bltn_pkg = get_package('builtins')
packages['b'] = bltn_pkg


# # # # # # # # # # # # #
# These are temporaries #
# # # # # # # # # # # # #
# Will later be handled by translator and code generator

def make_attr_getter(*args):
    names = [arg.print_form for arg in args]
    def inner(op):
        for name in names:
            op = getattr(op, name)
        return op
    return inner

def make_call_method(*args):
    names = [arg.print_form for arg in args]
    def inner(op, *args, **kwds):
        for name in names:
            op = getattr(op, name)
        return op(*args, **kwds)
    return inner

def attr(op, *attrs):
    for attr in attrs:
        op = getattr(op, attr.print_form)
    return op

class obj(StringingMixin):

    def __init__(self, **kwds):
        vars(self).update(kwds)

    def __eq__(self, other):
        if not isinstance(other, obj):
            return NotImplemented
        return vars(self) == vars(other)

@defmethod(as_string, [StringingMixin])
def meth(op):
    return '%s(%s)' % (op.__class__.__name__,
                       ' '.join(':%s %s' % (n,v)
                                for n,v in sorted(vars(op).iteritems())))

builtin_extras = {
    'Symbol'           : symbol.Symbol,
    'symbolp'          : symbol.symbolp,
    'gensym'           : symbol.gensym,
    'keywordp'         : symbol.keywordp,
    'use-package'      : symbol.use_package,
    'make-attribute'   : symbol.make_attribute,
    'make-keyword'     : symbol.make_keyword,
    'MacroFunction'    : macro.MacroFunction,
    'Cons'             : cons.Cons,
    'cons'             : cons.Cons,
    'clist'            : cons.clist,
    'listlen'          : cons.listlen,
    'make-attr-getter' : make_attr_getter,
    'make-call-method' : make_call_method,
    'attr'             : attr,
    'require'          : require.require,
    'obj'              : obj,
    'make-copy'        : copy.make_copy,
}

def get_builtin_symbol(name):
    return resolve_and_export_print_form(name, bltn_pkg)

def setup():
    for name in dir(bltns):
        sym = get_builtin_symbol(name)
        set_symbol_cell(sym, getattr(bltns, name))
    for name,value in builtin_extras.iteritems():
        sym = get_builtin_symbol(name)
        set_symbol_cell(sym, value)
setup()

def reset():
    yield None
    setup()
    return

register_reset_notifier(reset)


def builtinp(sym):
    return get_symbol_package(sym) is bltn_pkg

def get_builtin(sym):
    return get_symbol_cell(sym)


@register_special_form_emiter(get_builtin_symbol('attr'))
def emit_attr(c, emit, memo):
    acc = []
    attr_sym = iter(c).next()
    def rec(op):
        if symbolp(op):
            acc.append(as_string(op))
            return True
        l = list(op)
        try:
            head,iop,attr = l
        except ValueError:
            return False
        else:
            if not (head==attr_sym and attributep(attr)):
                return False
            acc.append(attr.print_form)
            return rec(iop)
    if not rec(c):
        return format_cons_raw(c, emit, memo)
    emit('.'.join(acc[::-1]))

@register_special_form_emiter(get_builtin_symbol('make-call-method'))
def emit_call_method(c, emit, memo):
    attrs = list(c)[1:]
    if not all(map(attributep, attrs)):
        return format_cons_raw(c, emit, memo)
    emit('.' + '.'.join(attr.print_form for attr in attrs))

@register_special_form_emiter(get_builtin_symbol('make-attr-getter'))
def emit_attr_getter(c, emit, memo):
    attrs = list(c)[1:]
    if not all(map(attributep, attrs)):
        return format_cons_raw(c, emit, memo)
    emit('..' + '.'.join(attr.print_form for attr in attrs))
