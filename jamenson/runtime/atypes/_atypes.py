'''Algebric Type System

   Supports arbriarty types rules as well as algebric combinations through
   set joins and complements.  Designed to extend the Python type system to
   incorporate a more robust definition of types.  This is espically useful
   for multimethods.

   Examples:

     In[0]: from jamenson.runtime.atypes import *
     In[2]: py_numbers = as_type((int, long, float, complex))
     In[2]: py_numbers
     Out[2]: oneof((int), (long), (float), (complex))

   Defines a composite type that matches any of the
   basic python number types.  The semantics of this type is

             OneOf([IsInstanceType(set([int])),
                    IsInstanceType(set([long])),
                    IsInstanceType(set([float])),
                    IsInstanceType(set([complex]))])

   This can be simplified with the function `optimize_type

     In[3]: opt_py_numbers = optimize_type(py_numbers)
     Out[3]: (int,long,complex,float)

          i.e. IsInstanceType(set([int,long,float,complex]))

   One can also use type definitions beyond Python types

   In[4]: odd_int_t = as_optimized_type(intersection(union(int,long), lambda x: x%2==1))
   In[5]: typep(7, odd_int_t)
   Out[6]: True
   In[7]: typep(6L, odd_int_t)
   Out[7]: False
   In[8]: typep([1,2], odd_int_t)
   Out[8]: False

   The last example is important, in that type searches are performed left-to-right
   and depth first. In this example, this allows us to assume that the union(int,long)
   type has been satisfied and we can saftely perform arithmetic without worry of a TypeError.
'''

from __future__ import absolute_import

from functools import partial

from ..func import identity, noop, compose
from ..collections import OrderedDict, OrderedSet
from .bsclasses import (TypeKeyerType, OneOf, TypeBase, KeyerBase, absolute_import,
                        type_keyer, IsInstanceType, JoinBase, bsclasses_names_spaces)
from .common import worst_score, best_score, no_score
from .common import atypes_multimethods_interface
from ..multimethod import MultiMethod, defmethod, defboth_wrapper, around
from .. import multimethod as MM

__all__ = atypes_multimethods_interface + '''
          as_type as_string eq_types
          IsInstanceType union
          optimize_type
          typep
'''.split()


# # # # # # #
# Base Type #
# # # # # # #
#import jamenson.runtime.atypes.bsclasses
#bsclasses = jamenson.runtime.atypes.bsclasses
#from jamenson.runtime.atypes.bsclasses import *

#this multimethod extends beyond the scope of atypes
#and is used for generic string representation of all objects
#in the jamenson runtime
as_string = MultiMethod(name='as_string',
                        #signature='object',
                        doc='''string representation of arbitrary systems
                        ''')
type_name = MultiMethod(name='type_name',
                        #signature='object',
                        doc='''returns a string the meaningfully names
                        what this type coresponds to
                        ''')
eq_types = MultiMethod(name='eq_types',
                       #signature='object,object',
                       doc='''whether two types instances have the same
                       semantical meaning
                       ''')
hash_type = MultiMethod(name='hash_type',
                        #signature='object',
                        doc='''calculate a hash s.t. two types that are equal through eq_types
                        will have the same hash key
                        ''')

@defmethod(as_string, [TypeBase])
def meth(op):
    return op.__class__.__name__

@defmethod(type_name, [TypeBase])
def meth(op):
    return as_string(op)

@defmethod(hash_type, [TypeBase])
def meth(op):
    return hash(id(op))

defeq = partial(defboth_wrapper, eq_types)

@defeq([TypeBase,TypeBase])
def meth(a,b):
    #return False #`is situation already handled in __eq__
    #rehandle it anyways, when eq_types called directly
    return a is b


# # # # # # # # #
# Type Methods  #
# # # # # # # # #

@defmethod(as_string, [IsInstanceType])
def meth(op):
    return '(%s)' % ','.join(tp.__name__ for tp in op.types)

@defeq([IsInstanceType,IsInstanceType])
def meth(a,b):
    return a.types == b.types

@defmethod(hash_type, [IsInstanceType])
def meth(op):
    return hash(frozenset(op.types))


@defmethod(as_string, [JoinBase])
def meth(op):
    return '%s(%s)' % (op.name, ', '.join(map(as_string, op.inners)))

@defmethod(eq_types, [JoinBase,JoinBase])
def meth(a,b):
    if a.__class__ is not b.__class__:
        return NotImplemented
    return a.inners == b.inners

@defmethod(hash_type, [JoinBase])
def meth(op):
    return hash(tuple(op.inners))


# # # # # #
# as type #
# # # # # #

as_type = MultiMethod(name='as_type',
                      #signature='object',
                      doc='''convert arbitrary objects to types
                      ''')

defmethod(as_type, [TypeBase])(identity)
defmethod(as_type, [type(type)])(IsInstanceType)
defmethod(as_type, [tuple])(OneOf)


# # # # # # # # # # # #
# Algebric Operations #
# # # # # # # # # # # #
# these operations are designed to be as simple as possible
# optimizations and higher level interfaces, built
# upon these simple operations, are provied below
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

union_two = MultiMethod(name='union_two',
                        #signature='TypeBase,TypeBase',
                        doc='''calculates the union of two types
                        ''')

def union(*inners):
    '''union of all types, this is optimized by by optimize_type
    '''
    return reduce(union_two, map(as_type, inners))

defunion2 = partial(defboth_wrapper, union_two)

@defunion2([TypeBase,TypeBase])
def meth(a,b):
    return OneOf(OrderedSet([a,b]))

@defunion2([IsInstanceType,IsInstanceType])
def meth(a,b):
   return IsInstanceType(*(a.types | b.types))


# order of these operations matters, so as to preserve or
# order in join

defmethod(union_two, [TypeBase, OneOf])
def meth(a,o):
    return OneOf(OrderedSet([a]) | o.inners)

defmethod(union_two, [OneOf, TypeBase])
def meth(o,a):
    return OneOf(o.inner | OrderedSet([a]))


# # # # # # # # #
# Optimizations #
# # # # # # # # #

optimize_type = MultiMethod('optimize_type',
                            #signature='TypeBase',
                            doc='''optimize type
                            may return an entirely different type, or a variant of the existing type,
                            or the existing type when no optimization is possible
                            ''')

def as_optimized_type(op):
    return optimize_type(as_type(op))

defmethod(optimize_type, [TypeBase])(identity)


# # # # # # # # # #
# Join Reduction  #
# # # # # # # # # #
# simplify joins by pairwise reduction of elemnts in set.
# each reduction converts a pair of types into a single type.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# define a new method combination for reduction of join elements.
# each method attempt to reduce the two elements to a single type.
# when this is not possible the method should return None.
# we then attempt the next method in this combination until one
# returns a value that is not None or we reach the end of the method
# sequence.

combine_join_reduce = MM.CombinationType('join_reduce')

def compile_join_reduce(mm, method, last_func):
    func = method.func
    if last_func is None:
        return func
    @MM.wrapper_fixup(mm)
    def wrap(a,b):
        red = func(a,b)
        if red is not None:
            return red
        return last_func(a,b)
    return wrap

MM.combination_compilers[combine_join_reduce] = compile_join_reduce

union_pair_reduce = MultiMethod('union_pair_reduce',
                                doc='''
                                reduce sets of elements in unions by
                                pairwise reduction
                                ''', default_combination=combine_join_reduce)

defunionreduce = partial(defboth_wrapper, union_pair_reduce)

def combinate_reduce_join(reducer, op):
    '''Reduce combinations through pairwsie reduction.
       T all combinations; including reducer(a,b) for all a and b s.t. a is not b
    '''
    inners = list(op.inners)
    for i,a in enumerate(inners):
        for b in inners[i+1:]:
            r = reducer(a,b)
            if r is not None:
                new_inners = op.inners.copy()
                #remove before add, incase r is eqal to orignal
                new_inners.remove(a)
                new_inners.remove(b)
                #insert at position of first one
                new_inners.insert(i, r)
                return combinate_reduce_join(reducer, op.__class__(new_inners))
    return op

@defmethod(optimize_type, [OneOf], combination=around)
def meth(callnext, op):
    return callnext(combinate_reduce_join(union_pair_reduce, op))


# # # # # # # # # # # # # # # # # # #
# pairwise reduction of join pairs  #
# # # # # # # # # # # # # # # # # # #

@defunionreduce([TypeBase, TypeBase])
def meth(a,b):
    if eq_types(a,b):
        return a
    return None

@defunionreduce([IsInstanceType, IsInstanceType])
def meth(a,b):
    return IsInstanceType(*(a.types | b.types))

# # # # #
# typep #
# # # # #

typep = MultiMethod(name='typep',
                    #signature='object, TypeBase',
                    doc='''test whether an instance corresponds to a type specifiier''')

@defmethod(typep, [object, IsInstanceType])
def meth(op, tp):
    return isinstance(op, tuple(tp.types))

@defmethod(typep, [object, OneOf])
def meth(op, tp):
    for etp in tp.inners:
        if typep(op, etp):
            return True
    return False



# # # # # # # # # # # #
# Keyers and Scoring  #
# # # # # # # # # # # #
# A keyer converts an object to cannonical type key
# that can be used to know whether or not an object
# matches a type specification
# # # # # # # # # # # # # # # # # # # # # # # # # # #

get_type_keyer = MultiMethod(name='get_type_keyer',
                             #signature='TypeBase',
                             doc='''returns the object that describes the rule by which instances
                             can be typed in a canonical way to determine if they follow this type
                             rule and the strength (score) of which they follow it
                             ''')

get_key_scorer = MultiMethod(name='get_key_scorer',
                                  #signature='TypeBase',
                                  doc='''given a type, returns a function that can score a specific key
                                  generated from its keyer
                                  ''')

# # # # # #
# Keyers  #
# # # # # #

keyer_getfunc = MultiMethod(name='keyer_getfunc',
                            #signature='KeyerBase',
                            doc='''returns a function that can generate a key that is unique
                            with regard to every variant of this type
                            ''')


defmethod(keyer_getfunc, [TypeKeyerType])(lambda x: type)

# isinstace scorer
def score_worst(key): return worst_score
def score_none(key): return no_score

@defmethod(get_type_keyer, [IsInstanceType])
def meth(op):
    return type_keyer

def isinstance_scorer(types, key_type):
    acc = no_score
    for x in types:
        try:
            score = key_type.mro().index(x)
        except ValueError:
            continue
        except TypeError:
            if x is type and issubclass(key_type, x):
                score = best_score
            else:
                score = best_score if issubclass(x, key_type) else no_score
        if acc is no_score:
            acc = score
        else:
            acc = min(acc, score)
    return acc

@defmethod(get_key_scorer, [IsInstanceType])
def meth(tp):
    return partial(isinstance_scorer, tp.types)

# algebric relationships
def score_one_of(inners, keys):
    acc = no_score
    for inner,op in zip(inners, keys):
        score = inner(op)
        if score is no_score:
            continue
        if acc is no_score or score < acc:
            acc = score
    return acc

@defmethod(get_key_scorer, [OneOf])
def meth(op):
    return partial(score_one_of, map(get_key_scorer, op.inners))


# composition of types
flatten_keyer = MultiMethod('flatten_keyer')
flatten_type_key = MultiMethod('flatten_type_key')

@defmethod(flatten_keyer, [OrderedDict, KeyerBase])
def meth(mapping, keyer):
    try:
        return mapping[keyer]
    except KeyError:
        index = mapping[keyer] = len(mapping)
        return index

@defmethod(flatten_type_key, [OrderedDict, TypeBase])
def meth(mapping, tp):
    return flatten_keyer(mapping, get_type_keyer(tp))

@defmethod(flatten_type_key, [OrderedDict, JoinBase])
def meth(mapping, join):
    return map(partial(flatten_type_key, mapping), join.inners)

def compose_types_scorer(tps):
    '''generates a composite type to both uniquely key and determine the score
       for set of types
    '''
    #break cyclic dependency of `compose_types_scorer and `calculate_method
    diff_types = set(map(type, tps))
    if len(diff_types) == 1:
        for tp in diff_types:
            pass
        try:
            keyer,make_scorer = hard_coded_composers[tp]
        except KeyError:
            pass
        else:
            return keyer, map(make_scorer, tps)
    key_mapping = OrderedDict()
    indices = [flatten_type_key(key_mapping, tp) for tp in tps]
    keyers = list(key_mapping)
    if not keyers:
        #happens when everyone is agnostic
        return noop, [score_worst]*len(tps)
    keyer_funcs = map(keyer_getfunc, keyers)
    scorers = map(get_key_scorer, tps)
    assert len(indices) == len(scorers)
    if len(keyers) == 1 and all([isinstance(x,int) for x in indices]):
        return list(keyer_funcs)[0], scorers
    return (lambda x : tuple([keyer_func(x) for keyer_func in keyer_funcs]),
            [make_indexer(xindices,scorer)
             for xindices,scorer in zip(indices, scorers)])

hard_coded_composers = {
    IsInstanceType : [type, lambda tp: partial(isinstance_scorer, tp.types)],
}

def getanitem(i, scorer, key): return scorer(key[i])

def rec_make_tree(indices,key):
    if isinstance(indices, int):
        return key[indices]
    return [rec_make_tree(index,key) for index in indices]

def getatree(indices, scorer, key): return scorer(rec_make_tree(indices, key))

def make_indexer(indices, scorer):
    if isinstance(indices, int):
        return partial(getanitem, indices, scorer)
    return partial(getatree, indices, scorer)

#apply new methods to classes
#from jamenson.runtime.atypes import bsclasses
def wire():
    for name in 'as_string eq_types hash_type as_type'.split():
        bsclasses_names_spaces[name] = globals()[name]
wire()
del wire


def hack_to_reoptimize_all_method_types():
    from jamenson.runtime.atypes.cold import Type
    def opt(x): return x if isinstance(x, Type) else optimize_type(x)
    for k,v in globals().iteritems():
        if isinstance(v, MultiMethod):
            for m in v.methods:
                m.type_sig.types = map(opt, m.type_sig.types)

