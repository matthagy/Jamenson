
from __future__ import absolute_import

from .walk import IRWalker

class ConstantsCollection(object):
    '''Special collection that compares objects not just by
       equality but also by type.  Hashing not used so that
       we can store unhashable objects.
    '''

    def __init__(self, seq=None):
        self.ops = []
        if seq is not None:
            self.extend(seq)

    def add(self, op):
        key = self.key_op(op)
        if key not in self.ops:
            self.ops.append(key)

    def remove(self, op):
        self.ops.remove(self.key_op(op))

    def extend(self, seq):
        for el in seq:
            self.add(el)

    def key_op(self, op):
        return type(op), op

    def __len__(self):
        return len(self.ops)

    def __contains__(self, op):
        return self.key_op(op) in self.ops

    def __iter__(self):
        for tp,val in self.ops:
            yield val

    def index(self, op):
        return self.ops.index(self.key_op(op))


class ConstantCollector(IRWalker):

    def __init__(self, descend_into_functions=True, skip_unused_constants=True):
        super(ConstantCollector, self).__init__()
        self.descend_into_functions = descend_into_functions
        self.constants = ConstantsCollection()
        self.skip_unused_constants = skip_unused_constants

    def visit_constant(self, node):
        if not (self.skip_unused_constants and node.result_ignored):
            self.constants.add(node.value)


def collect_constants(node, descend_into_functions=True, skip_unused_constants=True):
    col = ConstantCollector(descend_into_functions, skip_unused_constants)
    col.visit(node)
    return col.constants
