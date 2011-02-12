
from __future__ import absolute_import


from functools import partial

from ..func import identity, noop, compose
from ..collections import OrderedDict
from ..multimethod import MultiMethod, defmethod, defboth_wrapper, around
from .common import worst_score, best_score, no_score
from ..atypes import (as_type, as_string, eq_types, hash_type, as_type,
                      TypeBase, anytype, notanytype,
                      complement, union, intersection, optimize_type, typep,
                      defunionreduce, defintersectionreduce,
                      get_type_keyer, get_key_scorer, keyer_getfunc,
                      instance_keyer, flatten_type_key,
                      KeyerBase)

__all__ = '''HasAttr Attr Item
'''.split()

attrname_type = as_type(str)

as_attrname = MultiMethod('as_attrname')

defmethod(as_attrname, 'attrname_type')(identity)


# # # # # # # # #
# Type Classes  #
# # # # # # # # #

class AttrBase(TypeBase):

    def __init__(self, attrname):
        self.attrname = as_attrname(attrname)

class HasAttr(AttrBase):

    pass

class Attr(AttrBase):

    def __init__(self, attrname, inner):
        AttrBase.__init__(self, attrname)
        self.inner = as_type(inner)


class Item(AttrBase):

    def __init__(self, item, inner):
        self.item = item
        self.inner = as_type(inner)


# # # # # # # # #
# Type Methods  #
# # # # # # # # #

@defmethod(as_string, [HasAttr])
def meth(op):
    return 'hasattr(%r)' % (op.attrname,)

@defmethod(eq_types, [HasAttr,HasAttr])
def meth(a,b):
    return a.attrname == b.attrname

@defmethod(hash_type, [HasAttr])
def meth(op):
    return hash(op.attrname) ^ 0x1d60b03f


@defmethod(as_string, [Attr])
def meth(op):
    return 'attr(%s, %s)' % (op.attrname, as_string(op.inner))

@defmethod(eq_types, [Attr,Attr])
def meth(a,b):
    return (a.attrname == b.attrname and
            eq_types(a.inner, b.inner))

@defmethod(hash_type, [Attr])
def meth(op):
    return hash(op.attrname) ^ hash_type(op.inner) ^ 0x1cca50bb

@defmethod(as_string, [Item])
def meth(op):
    return 'item(%s, %s)' % (op.item, as_string(op.inner))

@defmethod(eq_types, [Item,Item])
def meth(a,b):
    return a.item == b.item and eq_types(a.inner, b.inner)

@defmethod(hash_type, [Item])
def meth(op):
    base = 0x1c316873
    try:
        base ^= hash(op.item)
    except (TypeError, AttributeError):
        pass
    return base ^ hash_type(op.inner)


# # # # # # # # #
# Optimizations #
# # # # # # # # #

@defmethod(optimize_type, [Attr])
def meth(a):
    #these are not true identical patterns,
    #in that TypeError is not raised if object
    #doesn't have the attribute.  In practice
    #such case are handled by explicit HasAttr before Attr
    inner = optimize_type(a.inner)
    if inner is anytype:
        return anytype
    if inner is notanytype:
        return notanytype
    return Attr(a.attrname, inner)

@defmethod(optimize_type, [Item])
def meth(a):
    inner = optimize_type(a.inner)
    if inner is anytype:
        return anytype
    if inner is notanytype:
        return notanytype
    return Item(a.item, inner)


# # # # # # # # # # # #
# Algebric Operations #
# # # # # # # # # # # #

#no point defining algebric operations for HasAttr
#as eq and hashing handles this already

@defunionreduce([Attr,Attr])
def meth(a,b):
    if a.attrname == b.attrname:
        return Attr(a.attrname, optimize_type(union(a.inner, b.inner)))
    return None

@defintersectionreduce([Attr,Attr])
def meth(a,b):
    if a.attrname == b.attrname:
        return Attr(a.attrname, optimize_type(intersection(a.inner, b.inner)))
    return None

@defmethod(complement, [Attr])
def meth(op):
    return Attr(op.attrname, optimize_type(complement(op.inner)))


@defunionreduce([Item,Item])
def meth(a,b):
    if a.item == b.item:
        return Item(a.item, optimize_type(union(a.inner, b.inner)))
    return None

@defintersectionreduce([Item,Item])
def meth(a,b):
    if a.item == b.item:
        return Item(a.item, optimize_type(intersection(a.inner, b.inner)))
    return None

@defmethod(complement, [Item])
def meth(op):
    return Item(op.item, optimize_type(complement(op.inner)))



# # # # #
# typep #
# # # # #

@defmethod(typep, [anytype, HasAttr])
def meth(op, ha):
    return hasattr(op, ha.attrname)

@defmethod(typep, [anytype, Attr])
def meth(op, a):
    return typep(getattr(op, a.attrname), a.inner)

@defmethod(typep, [anytype, Item])
def meth(op, i):
    return typep(op[i.item], i.inner)


# # # # # # # #
# Keyer Types #
# # # # # # # #

@defmethod(get_type_keyer, [HasAttr])
def meth(op):
    return instance_keyer

def hasattr_inner(attrname, op):
    return best_score if hasattr(op, attrname) else no_score

@defmethod(get_key_scorer, [HasAttr])
def meth(op):
    return partial(hasattr_inner, op.attrname)



missing_item_or_attr = object()

class WrappingKeyer(KeyerBase):

    def __init__(self, thing, inner_keyer):
        self.thing = thing
        self.inner_keyer = inner_keyer

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self.thing == other.thing and
                self.inner_keyer == other.inner_keyer)

    def __hash__(self):
        base = 0x1c4ff6f9
        try:
            base ^= hash(self.thing)
        except (ValueError, TypeError):
            pass
        return base ^ hash(self.inner_keyer)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '%s(%r, %s)' % (self.__class__.__name__,
                               self.thing, self.inner_keyer)

@defmethod(keyer_getfunc, [WrappingKeyer])
def meth(w):
    return partial(w.base_keyer, w.thing, keyer_getfunc(w.inner_keyer))


class AttrKeyer(WrappingKeyer):

    @staticmethod
    def base_keyer(attrname, inner_keyer, op):
        try:
            attr = getattr(op, attrname)
        except AttributeError:
            return missing_item_or_attr
        else:
            return inner_keyer(attr)


class ItemKeyer(WrappingKeyer):

    @staticmethod
    def base_keyer(item, inner_keyer, op):
        try:
            item = op[item]
        except LookupError:
            return missing_item_or_attr
        else:
            x = inner_keyer(item)
            return x

@defmethod(get_type_keyer, [Attr])
def meth(op):
    return AttrKeyer(a.attrname, get_type_keyer(a.inner))

@defmethod(get_type_keyer, [Item])
def meth(i):
    return ItemKeyer(i.item, get_type_keyer(i.inner))

def keyer_wrapper(inner_keyer, inner_key):
    if inner_key is missing_item_or_attr:
        return no_score
    return inner_keyer(inner_key)

@defmethod(get_key_scorer, [Attr])
@defmethod(get_key_scorer, [Item])
def meth(op):
    return partial(keyer_wrapper, get_key_scorer(op.inner))





