
from __future__ import absolute_import

from . import ir as I
from .walk import IRWalker, propigate_location
from . import bind


class ScopeInserter(IRWalker):

    def __init__(self, scope):
        super(ScopeInserter, self).__init__()
        self.scope = scope

    def visit_function(self, func):
        #don't visit body
        func.scope.parent = self.scope

    def visit_toplevel(self, top):
        raise RuntimeError("toplevel not top")


def as_top_expression(ir):
    if isinstance(ir, I.toplevel):
        return ir
    scope = bind.Scope()
    ScopeInserter(scope).visit(ir)
    return I.copy_loc(I.make_toplevel(ir, scope), ir)

