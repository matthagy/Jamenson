'''Determine if an object can be marshalled
'''

from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.runtime.marshalp
    exit()

from types import CodeType

from .multimethod import MultiMethod, defmethod
from .atypes import anytype


marshalp = MultiMethod('marshalp',
                       doc='''
                       predicate to determine if an object
                       is marshalable
                       ''')

#by default, not marshalable
@defmethod(marshalp, [anytype])
def meth(op):
    return False

#atomic types
@defmethod(marshalp, [(int,long,float,bool,complex,str,unicode,type(None),Ellipsis)])
def meth(op):
    return True

#collections that maybe marshalable if composed of other marshallable objects
#and not cyclic
composite_types = tuple,list,dict,set,frozenset
@defmethod(marshalp, [composite_types])
def meth(op):
    return marshallable_collection(op, set(), 250)

def marshallable_collection(col, memo, depth):
    if id(col) in memo:
        return False
    if not depth:
        return False
    depth -= 1
    memo.add(id(col))
    for el in iter_col_elements(col):
        if isinstance(el, composite_types):
            if not marshallable_collection(el, memo, depth):
                return False
        elif not marshalp(el):
            return False
    memo.remove(id(col))
    return True

iter_col_elements = MultiMethod()

@defmethod(iter_col_elements, [(tuple,list,set,frozenset)])
def meth(seq):
    return iter(seq)

@defmethod(iter_col_elements, [dict])
def meth(dct):
    for itr in [dct.iterkeys, dct.itervalues]:
        for el in itr():
            yield el

@defmethod(marshalp, [CodeType])
def meth(co):
    return all(marshalp(cnst) for cnst in co.co_consts)
