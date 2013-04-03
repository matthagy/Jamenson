
from __future__ import absolute_import
from __future__ import with_statement

from . import ir as I

def evalwhen_fixup(ir):
    if isinstance(ir, I.toplevel):
        evalwhen_fixup(ir.expression)
        return ir
    if not isinstance(ir, I.evalwhen):
        return ir
    if isinstance(ir.expression, I.evalwhen):
        ir.expression = evalwhen_fixup(ir.expression)
        assert isinstance(ir.expression, I.evalwhen)
        assert not isinstance(ir.expression.expression, I.evalwhen)
