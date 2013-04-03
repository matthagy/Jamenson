'''Types not need for boot strapping and can be loaded afterwards
'''

from __future__ import absolute_import

from functools import partial

from ..func import identity, noop, compose
from ..collections import OrderedDict, OrderedSet
from ..multimethod import MultiMethod, defmethod, defboth_wrapper, around
from .common import worst_score, best_score, no_score
from ..atypes import (as_type, as_string, eq_types,
                      IsInstanceType, union, optimize_type, typep,
                      TypeBase, JoinBase, OneOf, KeyerBase, hash_type,
                      defeq, defunion2, union_two, union_pair_reduce,
                      combine_join_reduce, combinate_reduce_join,
                      defunionreduce, TypeKeyerType,
                      get_type_keyer, get_key_scorer, keyer_getfunc,
                      flatten_keyer, flatten_type_key,
                      score_worst, score_none)

__all__ = '''
          anytype notanytype
          IsType EqType MemberType
          Predicate complement intersection
          _AnyType _NotAnyType Invert AllOf
'''.split()


# # # # # # # # #
# Type Classes  #
# # # # # # # # #

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

class EqlTypeBase(TypeBase):
    '''matches single instance of an object
    '''
    __slots__ = ['op']
    def __init__(self, op):
        self.op = op

class IsType(EqlTypeBase):
    name = 'is'
    eqp = staticmethod(lambda a,b: a is b)

class EqType(EqlTypeBase):
    name = 'eq'
    eqp = staticmethod(lambda a,b: a == b)

class MemberType(TypeBase):
    name = 'member'
    def __init__(self, op):
        self.elements = frozenset(op)

class Predicate(TypeBase):
    """predicate handled by some external function
       use sparingly as these can't be optimized
    """
    __slots__ = ['func']

    def __init__(self, func):
        self.func = func

class Invert(TypeBase):
    '''reverse logic of innert type
    '''
    __slots__ = ['inner']
    def __init__(self, inner):
        self.inner = as_type(inner)

class Seq(TypeBase):
    '''checks inner on all elements of a sequence
    '''
    __slots__ = ['inner']
    def __init__(self, inner):
        self.inner = as_type(inner)

OneOf.empty_type = notanytype

class AllOf(JoinBase):
    '''intersection of inner types
    '''
    empty_type = anytype
    name = 'allof'


# # # # # # # # #
# Type Methods  #
# # # # # # # # #

@defmethod(as_string, [_AnyType])
def meth(op):
    return 'anytype'

@defmethod(as_string, [_NotAnyType])
def meth(op):
    return 'notanytype'

@defmethod(as_string, [EqlTypeBase])
def meth(op):
    return '(%s %r)' % (op.name, op.op,)

@defmethod(eq_types, [EqlTypeBase,EqlTypeBase])
def meth(a,b):
    if a.__class__ is not b.__class__:
        return NotImplemented
    return a.eqp(a.op, b.op)

@defmethod(hash_type, [IsType])
def meth(op):
    return hash(id(op.op)) ^ 0x5f5b9f1

@defmethod(hash_type, [EqType])
def meth(op):
    try:
        return hash(op.op)
    except (ValueError,AttributeError):
        return 0x2aaaaaab #big prime


@defmethod(as_string, [MemberType])
def meth(op):
    return 'member(%s)' % (list(op.elements),)

@defmethod(hash_type, [MemberType])
def meth(op):
    return hash(op.elements)

@defeq('MemberType,MemberType')
def meth(a,b):
    return a.elements == b.elements


@defmethod(as_string, [Predicate])
def meth(op):
    return 'predicate(%r)' % (op.func,)

@defmethod(eq_types, [Predicate,Predicate])
def meth(a,b):
    return a.func is b.func

@defmethod(hash_type, [Predicate])
def meth(op):
    return hash(op.func) ^ 0x6146561


@defmethod(as_string, [Invert])
def meth(op):
    return 'not(%s)' % (op.inner,)

@defmethod(eq_types, [Invert,Invert])
def meth(a,b):
    return a.inner == b.inner

@defmethod(hash_type, [Invert])
def meth(op):
    return hash_type(op.inner) ^ 0x638f203

@defmethod(as_string, [Seq])
def meth(op):
    return 'seq(%s)' % (op.inner)

@defmethod(eq_types, [Seq,Seq])
def meth(a,b):
    return a.inner == b.inner

@defmethod(hash_type, [Seq])
def meth(op):
    return hash_type(op.inner) ^ 0x53fd05f

# # # # # #
# as type #
# # # # # #

defmethod(as_type, [type(None)])(lambda x: notanytype)
defmethod(as_type, [object])(IsType)
defmethod(as_type, [(int,long,float,str,complex)])(EqType)
defmethod(as_type, [(list,set,frozenset,OrderedSet)])(MemberType)
defmethod(as_type, [type(lambda : 1)])(Predicate)

# # # # # # # # # # # #
# Algebric Operations #
# # # # # # # # # # # #

complement = MultiMethod(name='complement',
                         signature='TypeBase',
                         doc='''calculates the complment (inverse) of a type
                         ''')

@defmethod(complement, [anytype])
def meth(op):
    return complement(as_type(op))

@defmethod(complement, [TypeBase])
def meth(op):
    return Invert(op)

@defmethod(complement, [Invert])
def meth(op):
    return op.inner

@defmethod(complement, [_AnyType])
def meth(op):
    return notanytype

@defmethod(complement, [_NotAnyType])
def meth(op):
    return anytype


@defunion2([_AnyType,TypeBase])
def meth(a,b):
    return a

@defunion2([_NotAnyType,TypeBase])
def meth(a,b):
    return b

@defunion2([OneOf, OneOf])
def meth(a,b):
    return OneOf(a.inners | b.inners)


intersection_two = MultiMethod(name='intersection_two',
                               signature='TypeBase,TypeBase',
                               doc='''calculates the intersection of two types
                               ''')

def intersection(*inners):
    '''intersection of all types, this is optimized by by optimize_type
    '''
    return reduce(intersection_two, map(as_type,inners))

defintersection2 = partial(defboth_wrapper, intersection_two)


@defintersection2('_NotAnyType,TypeBase')
def meth(a,b):
    return a

@defintersection2('_AnyType,TypeBase')
def meth(a,b):
    return b

@defintersection2('TypeBase,TypeBase')
def meth(a,b):
    return AllOf(OrderedSet([a,b]))

@defmethod(intersection_two, [AllOf,TypeBase])
def meth(a,t):
    return AllOf(a.inners | OrderedSet([t]))

@defmethod(intersection_two, [TypeBase, AllOf])
def meth(t,a):
    return AllOf(OrderedSet([t]) | a.inners)

@defintersection2('AllOf,AllOf')
def meth(a,b):
    return AllOf(a.inners | b.inners)


# # # # # # # # #
# Optimizations #
# # # # # # # # #

@defmethod(optimize_type, [MemberType])
def meth(op):
    if not op.elements:
        return notanytype
    elif len(op.elements)==1:
        for el in op.elements:
            return EqType(el)
    return op

@defmethod(optimize_type, [Invert])
def meth(op):
    return complement(optimize_type(op.inner))

@defmethod(optimize_type, [Seq])
def meth(op):
    return Seq(optimize_type(op.inner))

@defmethod(optimize_type, [JoinBase], combination=around)
def meth(callnext, op):
    '''hanle trival joins, more complexes cases handled below
    '''
    if len(op.inners) == 1:
        for tp in op.inners:
            return optimize_type(tp)
    elif len(op.inners) == 0:
        return op.empty_type
    else:
        return callnext(op)

# # # # # # # # # #
# Join Reduction  #
# # # # # # # # # #

intersection_pair_reduce = MultiMethod('intersection_pair_reduce',
                                doc='''
                                reduce sets of elements in intersections by
                                pairwise reduction
                                ''', default_combination=combine_join_reduce)

defintersectionreduce = partial(defboth_wrapper, intersection_pair_reduce)


@defmethod(optimize_type, [AllOf], combination=around)
def meth(callnext, op):
    return callnext(combinate_reduce_join(intersection_pair_reduce, op))

@defmethod(optimize_type, [OneOf], combination=around)
def meth(callnext, op):
    return callnext(combinate_reduce_join(union_pair_reduce, op))

@defmethod(optimize_type, [(AllOf,OneOf)], combination=around)
def expand_join(callnext, op):
    '''Convert nested Joins into flat Joins.
       This needs to be done before the pairwise reduction is done.
       No recursion needed as at this point all inner elements have already
       been optimized s.t. they are flat.
    '''
    new_inner = []
    cls = op.__class__
    for inner in op.inners:
        if isinstance(inner, cls):
            new_inner.extend(inner.inners)
        else:
            new_inner.append(inner)
    return callnext(op if len(new_inner) == len(op.inners) else cls(new_inner))

@defmethod(optimize_type, [(AllOf,OneOf)], combination=around)
def meth(callnext, op):
    '''Optimize inners before reductions.
       Helps to simplify inner composite forms to simpler representation before
       handled at this level.
    '''
    return callnext(op.__class__(map(optimize_type, op.inners)))


# # # # # # # # # # # # # # # # # # #
# pairwise reduction of join pairs  #
# # # # # # # # # # # # # # # # # # #

@defintersectionreduce([TypeBase, TypeBase])
def meth(a,b):
    if eq_types(a,b):
        return a
    return None

@defunionreduce([_AnyType, TypeBase])
def meth(a,t):
    return a

@defintersectionreduce([_AnyType, TypeBase])
def meth(a,t):
    return t

@defunionreduce([_NotAnyType, TypeBase])
def meth(a,t):
    return t

@defintersectionreduce([_NotAnyType, TypeBase])
def meth(a,t):
    return a

@defintersectionreduce([IsInstanceType, IsInstanceType])
def meth(a,b):
    t = a.types & b.types
    if not t:
        return notanytype
    return IsInstanceType(*t)

@defunionreduce([IsType, IsType])
def meth(a,b):
    if a.op is b.op:
        return a
    return None

@defunionreduce([EqType, EqType])
def meth(a,b):
    if a.op == b.op:
        return a
    return MemberType([a.op, b.op])

@defintersectionreduce([EqlTypeBase,EqlTypeBase])
def meth(a,b):
    if a.__class__ is not b.__class__:
        return None
    if a.eqp(a.op, b.op):
        return a
    return notanytype

@defunionreduce([IsType, EqType])
def meth(i,e):
    if i.op is e.op:
        return i
    return None

@defintersectionreduce([IsType, EqType])
def meth(i,e):
    if i.op is e.op:
        return i
    if i.op != e.op:
        return notanytype
    return i

@defunionreduce([MemberType, EqType])
def meth(m,e):
    return MemberType(m.elements | frozenset([e.op]))

@defintersectionreduce([MemberType, EqType])
def meth(m,e):
    if e.op not in m:
        return notanytype
    return e

@defunionreduce([MemberType, MemberType])
def meth(a,b):
    return optimize_type(MemberType(a.elements | b.elements))

@defintersectionreduce([MemberType, MemberType])
def meth(a,b):
    return optimize_type(MemberType(a.elements & b.elements))

@defunionreduce([Invert, Invert])
def meth(a,b):
    return optimize_type(Invert(a.inner & b.inner))

@defintersectionreduce([Invert, Invert])
def meth(a,b):
    return optimize_type(Invert(a.inner | b.inner))

@defunionreduce([Seq, Seq])
def meth(a,b):
    return optimize_type(Seq(a.inner | b.inner))

@defintersectionreduce([Seq, Seq])
def meth(a,b):
    return optimize_type(Seq(a.inner & b.inner))


# # # # #
# typep #
# # # # #

@defmethod(typep, [object, _AnyType])
def meth(op, tp):
    return True

@defmethod(typep, [object, _NotAnyType])
def meth(op, tp):
    return False

@defmethod(typep, [object, IsType])
def meth(op, tp):
    return op is tp.op

@defmethod(typep, [object, EqType])
def meth(op, tp):
    return op == tp.op

@defmethod(typep, [object, MemberType])
def meth(op, tp):
    return op in tp.elements

@defmethod(typep, [object, Predicate])
def meth(op, p):
    return bool(p.func(op))

@defmethod(typep, [object, Invert])
def meth(op, tp):
    return not typep(op, tp)

@defmethod(typep, [object, Seq])
def meth(op, tp):
    try:
        i = iter(op)
    except (TypeError,ValueError,AttributeError):
        return False
    for el in i:
        if not typep(el, tp.inner):
            return False
    return True

@defmethod(typep, [object, AllOf])
def meth(op, tp):
    for etp in tp.inners:
        if not typep(op, etp):
            return False
    return True

@defmethod(typep, [object, OneOf])
def meth(op, tp):
    for etp in tp.inners:
        if typep(op, etp):
            return True
    return False




# # # # # # # #
# Keyer Types #
# # # # # # # #

class AgnosticKeyerType(KeyerBase):
    pass

agnostic_keyer = AgnosticKeyerType()

class InstanceKeyerType(KeyerBase):
    pass

instance_keyer = InstanceKeyerType()

defmethod(keyer_getfunc, 'AgnosticKeyerType')(lambda x : noop)
defmethod(keyer_getfunc, 'InstanceKeyerType')(lambda x: identity)

@defmethod(as_string, [(AgnosticKeyerType, TypeKeyerType, InstanceKeyerType)])
def meth(op):
    base = op.__class__.__name__.split('Keyer',1)[0].lower()
    return '%s-keyer' % (base,)

class CompoundKeyer(KeyerBase):

    def __init__(self, seqkeyer):
        self.seqkeyer = seqkeyer

@defmethod(get_type_keyer, [JoinBase])
def meth(join):
    return CompoundKeyer(map(get_type_keyer, join.inners))

def base_compound_keyer_func(keyer_funcs, op):
    return tuple([keyer(op) for keyer in keyer_funcs])

@defmethod(keyer_getfunc, [CompoundKeyer])
def meth(ck):
    return partial(base_compound_keyer_func, map(keyer_getfunc, ck.seqkeyer))

class SeqKeyer(KeyerBase):

    def __init__(self, inner):
        self.inner = inner

def base_seq_keyer_func(keyer_func, op):
    try:
        i = iter(op)
    except (TypeError,ValueError,AttributeError):
        return None
    return tuple([keyer_func(el) for el in i])

@defmethod(keyer_getfunc, [SeqKeyer])
def meth(sk):
    return partial(base_seq_keyer_func, keyer_getfunc(sk.inner))


# agnostic scorers
@defmethod(get_type_keyer, [(_AnyType,_NotAnyType)])
def meth(op):
    return agnostic_keyer

@defmethod(get_key_scorer, [_AnyType])
def meth(op):
    return score_worst

@defmethod(get_key_scorer, [_NotAnyType])
def meth(op):
    return score_none


# eql scorers
score_type = union(int, no_score)

def eql2score_wrapper(eql, xop, op): return best_score if eql(xop, op) else no_score

@defmethod(get_type_keyer, [Seq])
def meth(seq):
    return SeqKeyer(get_type_keyer(seq.inner))

def seq_scorer(inner, seq):
    if seq is None:
        return no_score
    acc = best_score
    for keyel in seq:
        score = inner(keyel)
        if score is no_score:
            return score
        if score > acc:
            acc = score
    return acc

@defmethod(get_key_scorer, [Seq])
def meth(s):
    return partial(seq_scorer, get_key_scorer(s.inner))



@defmethod(get_type_keyer, [(EqlTypeBase,MemberType,Predicate)])
def meth(op):
    return instance_keyer

@defmethod(get_key_scorer, [EqlTypeBase])
def meth(tp):
    return partial(eql2score_wrapper, tp.eqp, tp.op)

def memberof(seq, el): return best_score if el in seq else no_score

@defmethod(get_key_scorer, [MemberType])
def meth(tp):
    return partial(memberof, tp.elements)

def bool2score_wrapper(func, op): return best_score if func(op) else no_score

@defmethod(get_key_scorer, [Predicate])
def meth(p):
    return partial(bool2score_wrapper, p.func)


# algebric relationships
@defmethod(get_type_keyer, [Invert])
def meth(op):
    return get_type_keyer(op.inner)

def invert_score(func, op): return best_score if func(op) is no_score else no_score

@defmethod(get_key_scorer, [Invert])
def meth(p):
    return partial(invert_score, get_type_keyer(p.inner))

def score_all_of(inners, keys):
    acc = best_score
    for inner,op in zip(inners, keys):
        score = inner(op)
        if score is no_score:
            return score
        if score > acc:
            acc = score
    return acc

@defmethod(get_key_scorer, [AllOf])
def meth(op):
    return partial(score_all_of, map(get_key_scorer, op.inners))


# composition of types
@defmethod(flatten_keyer, [OrderedDict, AgnosticKeyerType])
def meth(mapping, keyer):
    return 0 #dosn't matter

@defmethod(flatten_type_key, [OrderedDict, Invert])
def meth(mapping, tp):
    return flatten_type_key(mapping, tp.innner)



