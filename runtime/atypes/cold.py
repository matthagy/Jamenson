'''Atypes is built on top of multimethods, which is in turn built on top of atypes.
   To resolve this cyclic dependencies, we use Pythons type system to create
   a low-functionality (cold) atypes-like systems.
   The cold atypes can then be used to construct a cold multimethods as used in
   the boostraping process.
'''

from __future__ import absolute_import

from functools import partial

from ..func import identity, noop, compose
from ..atypes.common import worst_score, best_score, no_score, atypes_multimethods_interface

__all__ = atypes_multimethods_interface

def typep(op, tp):
    return isinstance(op, tp)

class Type(object):
    def __init__(self, tps):
        self.tps = tps

def as_optimized_type(tp):
    return Type(set(tp)) if isinstance(tp, tuple) else Type(set([tp]))

def type_name(tp):
    if len(tp.tps)==1:
        return iter(tp.tps).next().__name__
    return '(%s)' % ','.join(x.__name__ for x in tp.tps)

def compose_types_scorer(tps):
    return type, [partial(score_type,tp) for tp in tps]

def score_type(tp, key):
    acc = no_score
    for x in tp.tps:
        try:
            score = key.mro().index(x)
        except ValueError:
            continue
        except TypeError:
            score = best_score if issubclass(x, key) else no_score
        if acc is no_score:
            acc = score
        else:
            acc = min(acc, score)
    return acc

