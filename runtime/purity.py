
from __future__ import absolute_import

from weakref import WeakKeyDictionary


pure_functions_weak = WeakKeyDictionary()
pure_functions = {}


def register_pure(op):
    try:
        pure_functions_weak[op] = 1
    except TypeError:
        pure_functions[op] = 1
    return op

def purep(op):
    return op in pure_functions_weak or op in pure_functions

# Only a weak defition of purity is used here!
# Later, will need a more rigorous way of testing purity with
# respect to the arguments to function.

map(register_pure, [
    abs, all, any, bool, buffer, callable, chr,
    classmethod, cmp, coerce, complex, dict,
    dir, divmod, enumerate, float, frozenset,
    getattr, hasattr, hash, hex, int,
    isinstance, issubclass, iter, len, list, long,
    max, min, object, oct, ord, pow, property, range,
    repr, reversed, round, set, slice, sorted, staticmethod,
    str, sum, tuple, type, unichr, unicode, vars, xrange, zip,
    ])
