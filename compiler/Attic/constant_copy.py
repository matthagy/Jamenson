'''Ensure non-immutable constants are copied to prevent
   mutation affecting constant in future uses
'''

from ..runtime.builtins import get_builtin_symbol
from ..runtime.immutable import immutablep
from .walk import IRWalker, propigate_location
from . import ir as I
from .bind import Binding, BindingUse

copy_binding = Binding(get_builtin_symbol('make-copy'))

def make_copy_form(value, loc_form=None):
    copy_form = I.make_call(callee=I.make_read_binding(BindingUse(copy_binding)),
                            args=[I.make_constant(value)],
                            kwd_names=[], kwd_values=[],
                            star_args=None, star_kwds=None)
    if loc_form is not None:
        propigate_location(loc_form, copy_form)
    return copy_form


class ConstantCopyInserter(IRWalker):

    descend_into_functions = True

    def visit_constant(self, cnst):
        if not immutablep(cnst.value):
            I.replace_child(cnst, make_copy_form(cnst.value, cnst))


def insert_copy_constants(node):
    assert not isinstance(node, I.constant)
    ConstantCopyInserter().visit(node)
    return node

