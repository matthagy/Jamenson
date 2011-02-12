
__all__ = '''OrderedDict DefaultOrderDict OrderedSet
'''.split()

class OrderedDict(dict):

    def __init__(self, seq=()):
        self.order = []
        self.update(seq)

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def __setitem__(self, key, value):
        try:
            self.order.remove(key)
        except ValueError:
            pass
        self.order.append(key)
        dict.__setitem__(self, key, value)

    def pop(self, key):
        val = dict.pop(self, key)
        self.order.remove(key)
        return val

    def __delitem__(self, key):
        self.pop(key)

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
            return value
        return self[key]

    def update(self, seq):
        if isinstance(seq, dict):
            seq = seq.iteritems()
        for k,v in seq:
            self[k] = v

    def __iter__(self):
        return iter(self.order)

    def iterkeys(self):
        return iter(self)

    def itervalues(self):
        for k in self:
            yield self[k]

    def iteritems(self):
        for k in self:
            yield k, self[k]

    def keys(self):
        return list(self)

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def clear(self):
        del self.order[::]
        dict.clear(self)

    def copy(self):
        return self.__class__(self.iteritems())

    def __reduce__(self):
        return OrderedDict, (self.items(),)

    def __eq__(self, other):
        deq = dict.__eq__(self, other)
        if not isinstance(other, OrderedDict):
            return deq
        return deq and self.order == other.order

    def __req__(self, other):
        return self==other


class OrderedDefaultDict(OrderedDict):

    def __init__(self, default_factory, seq=()):
        self.default_factory = default_factory
        super(OrderedDefaultDict,self).__init__(seq)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            value = self[key] = self.default_factory()
            return value


class OrderedSet(set):

    def __init__(self, seq=()):
        self.order = []
        self.update(seq)

    def add(self, op):
        if op not in self:
            set.add(self, op)
            self.order.append(op)

    def insert(self, index, op):
        if op in self:
            self.order.remove(op)
        else:
            set.add(self, op)
        self.order.insert(index, op)

    def remove(self, op):
        set.remove(self, op)
        self.order.remove(op)

    def __iter__(self):
        return iter(self.order)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def update(self, seq):
        for op in seq:
            self.add(op)
        return self

    def copy(self):
        cp = self.__class__.__new__(self.__class__)
        set.update(cp, self)
        cp.order = self.order[::]
        return cp

    def discard(self, el):
        try:
            self.remove(el)
        except KeyError:
            pass

    def pop(self, el):
        self.remove(el)
        return el

    # perform all set operations, s.t. order of elemnts preserves order as if
    # order lists where added.  none of this is designed for efficency, at all!

    def difference(self, other):
        if not isinstance(other, OrderedSet):
            return set.difference(self, other)
        return self.copy().difference_update(other)

    def difference_update(self, other):
        if not isinstance(other, OrderedSet):
            return set.difference_update(self, other)
        for el in other:
            self.discard(el)
        return self

    def intersection(self, other):
        if not isinstance(other, OrderedSet):
            return set.intersection(self, other)
        return self.copy().intersection_update(other)

    def intersection_update(self, other):
        if not isinstance(other, OrderedSet):
            return set.intersection_update(self, other)
        for op in list(self):
            if op not in other:
                self.discard(op)
        return self

    def symmetric_difference(self, other):
        if not isinstance(other, OrderedSet):
            return set.symmetric_difference(self, other)
        return self.copy().symmetric_difference_update(other)

    def symmetric_difference_update(self, other):
        if not isinstance(other, OrderedSet):
            return set.symmetric_difference_update(self, other)
        for el in other:
            if el in self:
                self.remove(el)
            else:
                self.add(el)
        return self

    def union(self, other):
        if not isinstance(other, OrderedSet):
            return set.union(self, other)
        return self.copy().update(other)

    __or__ = __ror__ = union
    __ior__ = update

    __and__ = __rand__ = intersection
    __iand__ = intersection_update

    __sub__ = difference
    __isub__ = difference_update

    __xor__ = __rxor__ = symmetric_difference
    __ixor__ = symmetric_difference_update

    def __eq__(self, other):
        if not isinstance(other, OrderedSet):
            return set.__eq__(self, other)
        return set.__eq__(self, other) and self.order == other.order

