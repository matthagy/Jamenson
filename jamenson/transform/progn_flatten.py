'''Flatten nested progns, open progns with single expressions, and
   replace empty progns with nops
'''

from __future__ import absolute_import
from __future__ import with_statement

from ..compiler import ir as I
from ..compiler import bind
from ..compiler.walk import IRWalker
from ..compiler.purity import purep


def flatten_a_progn(p):
    assert isinstance(p, I.progn)
    new_exprs = []
    continued_index = len(p.exprs) - 1
    for i,expr in enumerate(p.exprs):
        if isinstance(expr, I.progn):
            exprs = list(expr.exprs)
            del expr.exprs[::] #delete expressions continuations
            new_exprs.extend(exprs)
        elif i!=continued_index and purep(expr):
            #drop pure expressions if their results aren't returned
            del expr.continuation
        else:
            del expr.continuation
            new_exprs.append(expr)
    if len(new_exprs) > 1:
        p.exprs = new_exprs #sets up expressions continuations
    elif len(new_exprs) == 1:
        I.replace_child(p, new_exprs[0])
    else:
        I.replace_with_nop(p)


class PrognFlattener(IRWalker):

    descend_into_functions = True

    def visit_progn(self, p):
        self.visit_children(p)
        flatten_a_progn(p)


def flatten_progns(ir):
    if isinstance(ir, I.progn):
        ir = I.copy_loc(I.make_toplevel(ir, bind.Scope()), ir)
        flatten_progns(ir)
        assert len(ir.bindings) == 0
        ex = ir.expression
        del ex.continuation
        return ex
    else:
        PrognFlattener().visit(ir)
        return ir
