
from __future__ import absolute_import

from . import ir as I
from .walk import IRWalker, propigate_location

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


