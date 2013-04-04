'''Annotation of ir.
   Handles simple annotations, particularly marking results that are ignored.
'''

from __future__ import absolute_import


from ..runtime.multimethod import MultiMethod, defmethod

from . import ir as I


def annotate(ir):
    annotate_node(ir)
    annotate_children(ir)

annotate_node = MultiMethod('annotate_node')

@defmethod(annotate_node, [I.node])
def meth(node):
    pass

annotate_children = MultiMethod('annotate_children')

@defmethod(annotate_children, [I.node])
def meth(node):
    for child in I.iter_children(node):
        annotate(child)

@defmethod(annotate_node, [I.unary_base])
def meth(ub):
    ub.op.result_ignored = ub.result_ignored

@defmethod(annotate_node, [I.binary_base])
def meth(bb):
    bb.lop.result_ignored = bb.rop.result_ignored = bb.result_ignored

@defmethod(annotate_node, [I.buildslice])
def meth(bs):
    bs.start.result_ignored = bs.stop.result_ignored = bs.step.result_ignored = bs.result_ignored

@defmethod(annotate_node, [I.progn])
def meth(p):
    exprs = list(p.exprs)
    return_index = len(exprs) - 1
    if p.result_ignored:
        return_index += 1
    for index,expr in enumerate(exprs):
        expr.result_ignored = index < return_index

@defmethod(annotate_node, [I.if_])
def meth(c):
    c.then.result_ignored = c.else_.result_ignored = c.result_ignored

@defmethod(annotate_node, [I.trycatch])
def meth(tc):
    tc.body.result_ignored = True
    tc.catch.result_ignored = True

@defmethod(annotate_node, [I.tryfinally])
def meth(tf):
    tf.body.result_ignored =True
    tf.finally_.result_ignored = True

@defmethod(annotate_node, [I.tag])
def meth(tg):
    tg.result_ignored = True
    tg.body.result_ignored = True

@defmethod(annotate_node, [I.preeval])
def meth(pre):
    pre.expression.result_ignored = pre.result_ignored

@defmethod(annotate_node, [I.toplevel])
def meth(tp):
    tp.expression.result_ignored = tp.result_ignored
