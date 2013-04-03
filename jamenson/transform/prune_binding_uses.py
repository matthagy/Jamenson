
from __future__ import absolute_import
from __future__ import with_statement

from ..compiler import bind
from ..compiler import ir as I
from ..compiler.walk import propigate_location, IRWalker


class WriteOnlyBindingsRemover(IRWalker):

    descend_into_functions = True

    def visit_toplevel(self, top):
        self.handle_scope(top.scope)

    def visit_function(self, func):
        self.handle_scope(func.scope)

    def handle_scope(self, scope):
        for binding in scope.bindings:
            users = filter(None, (binding_use.user for binding_use in bindings.uses))
            n_reads, n_writes, n_deletes = (sum(1 for user in users if isinstance(user, counting_user_types))
                                            for counting_user_types in (I.read_binding, I.write_binding, I.delete_binding))
            n_others = len(users) - (n_reads + n_writes + n_deletes)
            if not n_reads + n_others:
                #XXX can hide errors in code by removing binding deletion, although commonly not important
                if not n_deletes:
                    for user in users:
                        shortcircuit_write_binding(user)

def remove_write_only_bindings(node):
    if isinstance(node, I.write_binding):
        return remove_write_only_bindings(I.make_toplevel(node, bind.Scope())).expression
    WriteOnlyBindingsRemover().visit(node)
    return node

def shortcircuit_write_binding(wb):
    assert isinstance(wb, I.write_binding)
    assert wb.continuation is not None
    value = wb.value
    I.replace_child(wb, value)
    return value


