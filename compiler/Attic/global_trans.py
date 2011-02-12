'''Translate operation on globally scoped symbols to
   operations on symbol_cell mapping
'''

from __future__ import absolute_import
from __future__ import with_statement

from ..runtime.symbol import get_symbol_cells_map, gensym
from . import ir as I
from . import bind
from .walk import IRWalker, propigate_location
from .translate import state as translation_state


class GlobalSymbolTransformer(IRWalker):

    def __init__(self, symbol_map_sym, top_scope):
        IRWalker.__init__(self)
        self.symbol_map_sym = symbol_map_sym
        self.current_scope = top_scope

    @staticmethod
    def is_global(binding):
        return bind.get_binding_use_type(binding) == bind.BND_GLOBAL

    @staticmethod
    def replace(old, new, skips=[]):
        propigate_location(old, new, skips)
        I.replace_child(old, new)

    def visit_function(self, func):
        for child in func.defaults:
            self.visit(child)
        old_scope = self.current_scope
        self.current_scope = func.scope
        self.visit(func.body)
        self.current_scope = old_scope

    def make_read_map(self):
        return I.make_read_binding(self.current_scope.use_symbol(self.symbol_map_sym))

    def visit_read_binding(self, rb):
        if not self.is_global(rb.binding):
            return
        self.replace(rb, I.make_getitem(self.make_read_map(),
                                        I.make_constant(rb.binding.symbol)))

    def make_set(self, binding, value_ir):
        return I.make_setitem(self.make_read_map(),
                              I.make_constant(binding.symbol),
                              value_ir)

    def visit_write_binding(self, wb):
        value = wb.value
        if self.is_global(wb.binding):
            del value.continuation
            self.replace(wb, self.make_set(wb.binding, value),
                         skips=[value])
        self.visit(value)

    def visit_delete_binding(self, db):
        if not self.is_global(db.binding):
            return
        self.replace(db, I.make_delitem(self.make_read_map(),
                                        I.make_constant(db.binding.symbol)))

    def visit_foriter(self, fi):
        itr = fi.iter
        if self.is_global(fi.binding):
            old_binding = fi.binding
            del fi.binding
            sym = gensym('foriter-tmp')
            self.current_scope.register_local(sym)
            del itr.continuation
            self.replace(fi, I.make_progn([
                I.make_foriter(tag=fi.tag,
                               binding=self.current_scope.use_symbol(sym),
                               iter=itr),
                self.make_set(old_binding, I.make_read_binding(self.current_scope.use_symbol(sym)))
                ]),
                skips=[itr])
            del fi.tag
        self.visit(itr)

    def visit_unpack_seq(self, us):
        new_bindings = []
        copies = []
        for binding in us.places:
            if not self.is_global(binding):
                new_bindings.append(binding)
            else:
                gs = gensym('unpack-tmp')
                new_bindings.append(self.current_scope.register_and_use_local(gs))
                copies.append([gs, binding])
        seq = us.seq
        if copies:
            del seq.continuation
            del us.places
            self.replace(us, I.make_progn([
                I.make_unpack_seq(seq, new_bindings)
                ] + [self.make_set(binding, I.make_read_binding(self.current_scope.use_symbol(gs)))
                     for gs,binding in copies]),
                skips=[seq])
        self.visit(seq)

def transform_global_symbol_use(top):
    assert isinstance(top, I.toplevel)
    top_scope = top.scope
    assert not top_scope.parent
    symbol_map_sym = gensym('symbol-cells-map')
    symbol_map_binding = top_scope.register_local(symbol_map_sym)
    GlobalSymbolTransformer(symbol_map_sym, top_scope).visit(top.expression)
    if not len(symbol_map_binding.uses):
        top_scope.unregister_binding(symbol_map_binding)
        return top
    expression = top.expression
    del expression.continuation
    when = None
    if isinstance(expression, I.evalwhen):
        when = expression.when
        expression = expression.expression
        del expression.continuation
    new_ir = I.make_progn([I.make_write_binding(
                               top_scope.use_symbol(symbol_map_sym),
                               I.make_call(callee=I.make_constant(get_symbol_cells_map),
                                           args=[], kwd_names=[], kwd_values=[],
                                           star_args=None, star_kwds=None)),
                           expression])
    if when is not None:
        new_ir = I.make_evalwhen(when=when, expression=new_ir)
    new_top = I.make_toplevel(new_ir, top_scope)
    propigate_location(top, new_top, [expression])
    return new_top
