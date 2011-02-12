
from __future__ import absolute_import
from __future__ import with_statement

import new

from . import ir as I
from . import codegen
from .block import compile_time_eval, common_transform
from .preeval import evaluate_compile_time_values
from .purity import purep
from ..runtime.purity import register_pure


def make_function(func, **kwds):
    assert isinstance(func, I.function)
    func = evaluate_compile_time_values(func, compile_time_eval)
    body = func.body
    old_parent_scope = func.scope.parent
    func.scope.parent = None
    top = I.copy_loc(I.make_toplevel(body, func.scope), body)
    top = common_transform(top)
    func.body = top.expression
    free_bindings = codegen.get_canonical_free_bindings(func)
    if free_bindings:
        raise ValueError("can't create a function with free bindings")
    with codegen.state.top(tag_labels=None, **kwds):
        ir = codegen.construct_compilation_ir(func)
        function_pure = purep(ir)
        [[_, code]] = codegen.load_function_code(ir)
    default_values = tuple(map(codegen.evaluate_ir, func.defaults))
    func.scope.parent = old_parent_scope
    function =  new.function(code, {}, func.name, default_values)
    if function_pure:
        register_pure(function)
    return function

