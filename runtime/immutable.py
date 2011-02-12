
from __future__ import absolute_import
from __future__ import with_statement

from .multimethod import MultiMethod, defmethod
from .atypes import anytype
from .cons import Cons, nil
from .symbol import Symbol


immutablep = MultiMethod('immutablep')

@defmethod(immutablep, [anytype])
def meth(op):
    return False

@defmethod(immutablep, [(int,long,float,str,unicode,type(None),Symbol)])
def meth(op):
    return True

@defmethod(immutablep, [tuple])
def meth(t):
    return all(immutablep(op) for op in t)

@defmethod(immutablep, [Cons])
def meth(s):
    return s is nil

