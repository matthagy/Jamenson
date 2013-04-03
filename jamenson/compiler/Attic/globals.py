'''code transformations to access global symbol bindings
'''

from __future__ import absolute_import

import .ir as I
from .scope import NameTranslation, Binding
from .walk import IRWalker
from ..runtime.symbol import get_symbol_cells_map


I.load_time_value(I.call(
    callee=I.constant(get_symbol_cells_map),
    kwd_names=[]))

class GlobalTransformer(IRWalker):

    def __init__(self, cells_map_binding):
        IRWalker.__init__(self)
        self.cells_map_binding = cells_map_binding

    def update(self, node, rebuilder):
        if node.binding.is_global():
            expr = rebuilder(node)
            if I.get_continuation(node):
                I.replace_child(node, expr)
        else:
            expr = node
        return self.visit(expr)

    def make_read_cells_map_binding(self):
        return I.read_binding(self.cells_map_binding)

    def visit_read_binding(self, node):
        return self.update(node, self.make_read_binding)

    def make_read_binding(self, node):
        return I.getitem(self.make_read_cells_map_binding(),
                         I.constant(node.binding.symbol))

    def visit_write_binding(self, node):
        return self.update(node, self.make_write_binding)

    def make_write_binding(self, node):
        return I.setitem(self.make_read_cells_map_binding(),
                         I.constant(node.binding.symbol),
                         node.value)

    def visit_delete_binding(self, node):
        return self.update(node, self.make_delete_binding)

    def make_delete_binding(self, node):
        return I.delitem(self.make_read_cells_map_binding(),
                         I.constant(node.binding.symbol))

def transform_globals(node):
    
