
from __future__ import absolute_import
from __future__ import with_statement

if __name__ == '__main__':
    import jamenson.transform.state
    exit()

from ..runtime.ctxsingleton import CtxSingleton
from ..runtime.struct import defstruct
from ..runtime.atypes import anytype, Seq, MemberType, Predicate
from ..runtime.symbol import Symbol
from ..runtime.multimethod import MultiMethod, defmethod
from ..runtime.iterutils import permutations

class TransformationState(CtxSingleton):

    def _cxs_setup_top(self):
        self.transformations = None
        self.default_transformation = None
        self._cxs_setup_aux()

    def _cxs_copy(self, **kwds):
        cp = self._cxs_super._cxs_copy(**kwds)
        cp._cxs_setup_aux()
        return cp

    def _cxs_setup_aux(self):
        self.transformations = (self.transformations.copy()
                                if self.transformations
                                else {})
        self.default_transformation = (self.default_transformation or
                                       'default')

        if 'default' not in self.transformations:
            self.transformations['default'] = get_default_transformation()


RULE_BEFORE, RULE_AFTER = range(2)
defstruct('Rule',
          ['type', None, MemberType([RULE_BEFORE, RULE_AFTER])],
          ['name', None, str])

base_trans_props = [
    ['name', None, str],
    ['rules', [], Seq(Rule)]]

defstruct('Transformation',
          ['func', None, Predicate(callable)],
          *base_trans_props)

defstruct('TransformationSet',
          ['names', [], Seq(str)],
          *base_trans_props)

def cannonicalize_name(name):
    if isinstance(name, Symbol):
        name = name.print_form
    assert isinstance(name, str)
    return name.lower()

def parse_rule(rule):
    tp, name = rule
    return Rule(type=dict(before=RULE_BEFORE,
                          after=RULE_AFTER)[tp.lower()],
                name=cannonicalize_name(name))

def register_transformation(name, func, *rules):
    name = cannonicalize_name(name)
    _register(name, Transformation(name=name,
                                   func=func,
                                   rules=map(parse_rule, rules)))

def register_transformation_set(name, inner_names, *rules):
    name = cannonicalize_name(name)
    _register(name, TransformationSet(name=name,
                                      names=map(cannonicalize_name, inner_names),
                                      rules=map(parse_rule, rules)))

def _register(name, trans):
    state.transformations[name] = trans

default_names = []

def get_default_transformation():
    return TransformationSet(name='default',
                             names=default_names,
                             rules=[])

def add_default_transformation(name):
    default_names.append(name)

def run_transformation(ir, name='default'):
    the_trans = get_transformation(name)
    all_transes = expand_transformations(the_trans)
    ordered_transes = order_transformations(all_transes, name)
    for trans in ordered_transes:
        ir = trans.func(ir)
    return ir

def get_transformation(name):
    try:
        return state.transformations[name]
    except KeyError:
        raise ValueError("no such transformation %r" % (name,))

def expand_transformations(trans):
    memo = {}
    x_expand_transformations(trans, memo)
    return filter(lambda x: x is not None, memo.values())

x_expand_transformations = MultiMethod('x_expand_transformations',
                                       doc='''
                                       ''')

@defmethod(x_expand_transformations, [Transformation, dict])
def meth(trans, memo):
    memo[trans.name] = trans

@defmethod(x_expand_transformations, [TransformationSet, dict])
def meth(trans, memo):
    memo[trans.name] = None
    for name in trans.names:
        if name not in memo:
            x_expand_transformations(get_transformation(name), memo)

def order_transformations(ts, name):
    invariants = collect_invariants(ts)
    for names in permutations(list(t.name for t in ts)):
        if order_obeys_invariantes(names, invariants):
            mapping = dict((t.name, t) for t in ts)
            return list(mapping[name] for name in names)
    raise RuntimeError("no valid transformation order for transformation %r" % (name,))

def collect_invariants(ts):
    acc = set()
    for t in ts:
        for rule in t.rules:
            if rule.type is RULE_AFTER:
                acc.add((rule.name, t.name))
            elif rule.type is RULE_BEFORE:
                acc.add((t.name, rule.name))
            else:
                raise RuntimeError('bad rule %r' % (rule.type,))
    return list(acc)

def order_obeys_invariantes(order, invariants):
    order = list(order)
    for first, second in invariants:
        if order.index(first) > order.index(second):
            return False
    return True

state = TransformationState()
from . import declare #import for side effects
