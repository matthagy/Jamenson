'''Utilities for handeling non-execution time evaluation.
'''

from __future__ import absolute_import

from ..compiler import ir as I
from ..compiler.walk import IRWalker, propigate_location
from ..runtime.symbol import gensym


class PreEvalReplacer(IRWalker):

    descend_into_functions = True
    def __init__(self, preeval_class):
        IRWalker.__init__(self)
        setattr(self, 'visit_' + preeval_class.__name__,
                self.replace_preeval)

class PreEvalShortCircuiter(PreEvalReplacer):

    def replace_preeval(self, node):
        expr = node.expression
        I.replace_child(node, expr)
        return self.visit(expr)

def short_circuit_preeval(node, preeval_class=None):
    '''replace preeval forms with direct execution
    '''
    return PreEvalReplacer(preeval_class or I.preeval).visit(node)


class LoadTimeTransformer(PreEvalReplacer):

    def __init__(self, scope):
        super(LoadTimeTransformer, self).__init__(I.load_time_value)
        self.scope = scope
        self.loads = []

    def replace_preeval(self, node):
        self.visit(node.expression)
        g = gensym('load-time')
        self.scope.register_local(g)
        self.loads.append([g, node.expression])
        I.replace_child(node, I.make_read_binding(I.get_node_local_scope(node).use_symbol(g)))


def replace_loadtimes(top):
    """Insert the code for load time evaluation of expressions.
       Accomplished by evaluating these forms at highest level progn and
       then storing their values in gensym's.
    """
    assert isinstance(top, I.toplevel)
    trans = LoadTimeTransformer(top.scope)
    trans.visit(top)
    if trans.loads:
        top_expr = top.expression
        del top.expression
        expr = I.make_progn(list(I.make_write_binding(top.scope.use_symbol(g), expr)
                                 for g,expr in trans.loads) +
                            [top_expr])
        propigate_location(top, expr, skips=list(expr for g,expr in trans.loads))
        top.expression = expr
    return top

