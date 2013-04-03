
'''make sure class and special instance are only loaded once,
   even when atypes is reloaded
'''

from jamenson.runtime.collections import OrderedDict, OrderedSet

class TypeBase(object):

    def __invert__(self):
        return complement(self)

    def __or__(self, other):
        return union(self, other)

    def __and__(self, other):
        return intersection(self, other)

    def __repr__(self):
        return as_string(self)

    def __repr__(self):
        return as_string(self)

    def __eq__(self, other):
        if self is other:
            return True
        try:
            return eq_types(self, other)
        except NoSuchMethod:
            return NotImplemented

    def __hash__(self):
        return hash_type(self)

class _AnyType(TypeBase):
    '''matches anything
    '''
    __slots__ = []

anytype = _any = _AnyType()

class _NotAnyType(TypeBase):
    """doesn't match anything
    """
    __slots__ = []

notanytype = _NotAnyType()

class IsInstanceType(TypeBase):
    '''wraps a Python type
    '''
    __slots__ = ['types']
    def __init__(self, *types):
        assert all(isinstance(tp, type) for tp in types)
        assert len(types) > 0
        self.types = set(types)


class JoinBase(TypeBase):
    '''join of inner types
    '''
    __slots__ = ['inners']
    def __init__(self, inners):
        self.inners = OrderedSet(map(as_type, inners))

class OneOf(JoinBase):
    '''union of inner types
    '''
    empty_type = notanytype
    name = 'oneof'

class KeyerBase(object):
    def __str__(self): return as_string(self)
    def __repr__(self): return as_string(self)


class TypeKeyerType(KeyerBase):
    pass

type_keyer = TypeKeyerType()


__all__ = [k for k in list(globals()) if not k.startswith('__') and not '[' in k]
