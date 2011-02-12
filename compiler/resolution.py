'''compile time resolution of simple ir expressions
'''

from ..runtime.symbol import get_symbol_cell, UnboundSymbolError
from . import ir as I
from . import bind


class UnresolvableError(Exception):
    pass

def compile_time_resolve(ir):
    if isinstance(ir, I.read_binding):
        if bind.get_binding_use_type(ir.binding) is bind.BND_GLOBAL:
            try:
                return get_symbol_cell(ir.binding.binding.symbol)
            except UnboundSymbolError:
                pass
    elif isinstance(ir, I.attrget):
        obj = compile_time_resolve(ir.obj)
        try:
            return getattr(obj, ir.name)
        except AttributeError:
            pass
    elif isinstance(ir, I.constant):
        return ir.value
    raise UnresolvableError


