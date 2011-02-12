'''arbitrary recursions data structure tear down
'''

from __future__ import with_statement
from __future__ import absolute_import

from collections import defaultdict

from .func import identity, noop, compose
from .ctxsingleton import CtxSingleton
from .multimethod import MultiMethod, defmethod
from .atypes import anytype, typep
from .atypes.etypes import recursions_type
from .atypes.ptypes import atomic_type
from .collections import OrderedDict, OrderedDefaultDict, OrderedSet


__all__ = ['do_deletion','delete','state','delete_obj','recursions_type']


class DeleteState(CtxSingleton):

    def _cxs_setup_top(self):
        self.memo = set()
        self.recursions = None
        self.delete_immutable = True

state = DeleteState()

def do_deletion(op, recursions=None, delete_immutable=True):
    assert typep(recursions, recursions_type)
    with state(recursions=recursions, delete_immutable=delete_immutable):
        delete(op)

def delete(op):
    recursions = state.recursions
    if recursions is not None and recursions==0:
        return
    memo = state.memo
    i = id(op)
    if i in memo:
        return
    memo.add(i)
    if recursions is None:
        delete_obj(op)
    else:
        with state.top(recursions=recursions-1):
            delete_obj(op)

delete_obj = MultiMethod('delete_obj',
                         doc='objection destruction registry')

#by default no deletion
defmethod(delete_obj, 'anytype')(identity)

#atomic types
defmethod(delete_obj, 'atomic_type')(identity)

#sequence types
@defmethod(delete_obj, '(tuple,frozenset)')
def meth(op, delete=delete):
    if not state.delete_immutable:
        raise TypeError("can't delete immutable objects %r" % (op,))
    for el in op:
        delete(el)

@defmethod(delete_obj, 'list')
def meth(op, delete=delete):
    for el in op:
        delete(el)
    del op[::]

@defmethod(delete_obj, '(set,OrderedSet)')
def meth(op, delete=delete):
    for el in op:
        delete(el)
    op.clear()

#mappings
@defmethod(delete_obj, '(dict, defaultdict, OrderedDefaultDict, OrderedDict)')
def meth(op, delete=delete):
    for k,v in op.iteritems():
        delete(k)
        delete(v)
    op.clear()
