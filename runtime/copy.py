'''arbitrary recursions copy registry
'''

from __future__ import with_statement
from __future__ import absolute_import

from collections import defaultdict

from .func import identity, noop, compose
from .ctxsingleton import CtxSingleton
from .multimethod import MultiMethod, defmethod
from .atypes import as_optimized_type, anytype, union, intersection, typep
from .atypes.etypes import recursions_type
from .atypes.ptypes import atomic_type
from .collections import OrderedDict, OrderedDefaultDict, OrderedSet


__all__ = ['make_copy','copy','state','copy_obj','recursions_type','get_copy', 'set_copy']

class CopyState(CtxSingleton):

    def _cxs_setup_top(self):
        self.memo = None
        self.recursions = None

state = CopyState()


def make_copy(op, recursions=None):
    assert typep(recursions, recursions_type)
    with state(recursions=recursions, memo={}):
        return copy(op)

_holder = object()
def copy(op):
    recursions = state.recursions
    if recursions is not None and recursions==0:
        return op
    memo = state.memo
    i = id(op)
    try:
        cp = memo[i]
    except KeyError:
        memo[i] = _holder
        if recursions is None:
            cp = copy_obj(op)
        else:
            with state(recursions=recursions-1, memo=memo):
                cp = copy_obj(op)
        memo[i] = cp
    if cp is _holder:
        cyclic_error(op)
    return cp

def get_copy(op):
    try:
        op = state.memo[id(op)]
    except KeyError:
        raise ValueError("copy not yet in progress for %r" % (op,))
    else:
        if op is _holder:
            cyclic_error(op)
        return op

def set_copy(op, cp):
    memo = state.memo
    try:
        existing = memo[id(op)]
    except KeyError:
        pass
    else:
        if existing is not _holder and existing is not cp:
            raise RuntimeError("replacing copy")
    memo[id(op)] = cp
    return cp

def cyclic_error(op):
    raise RuntimeError("cyclic copy for %r id=%d" % (op, id(op)))


copy_obj = MultiMethod('copy_obj',
                   doc='arbitrary recursions copying registry')

#by default no copy_objing
defmethod(copy_obj, [anytype])(identity)

#atomic types
defmethod(copy_obj, [atomic_type])(identity)

@defmethod(copy_obj, [list])
def meth(l):
    return map(copy, l)

@defmethod(copy_obj, [tuple])
def meth(t):
    return tuple(map(copy, t))

@defmethod(copy_obj, [(dict, OrderedDict)])
def meth(d):
    return type(d)([[copy(k),copy(v)] for k,v in d.iteritems()])

@defmethod(copy_obj, [(set, frozenset, OrderedSet)])
def meth(s):
    return type(s)([copy(x) for x in s])

@defmethod(copy_obj, [(defaultdict, OrderedDefaultDict)])
def meth(d):
    return type(d)(d.default_factory, [[copy(k),copy(v)] for k,v in d.iteritems()])
