'''utilities for handeling non-execute time evaluation
'''

from __future__ import absolute_import

from . import ir as I
from .walk import IRWalker, propigate_location
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


def transform_load_times(top):
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


class EvaluateCompileTime(IRWalker):

    descend_into_functions = True

    def __init__(self, eval_ir):
        super(EvaluateCompileTime, self).__init__()
        self.eval_ir = eval_ir

    def visit_compile_time_value(self, node):
        I.replace_child(node, propigate_location(node, I.make_constant(self.eval_ir(node.expression))))

def evaluate_compile_time_values(node, eval_ir):
    EvaluateCompileTime(eval_ir).visit(node)
    return node


