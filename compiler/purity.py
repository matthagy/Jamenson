'''determine purity (side-effect free) of a ir expressions
'''

from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.compiler.purity
    exit()


from ..runtime.multimethod import MultiMethod, defmethod, around
from ..runtime.purity import purep as callable_purep
from . import ir as I
from .resolution import compile_time_resolve, UnresolvableError


purep = MultiMethod('purep',
                  signature='node',
                  doc='''Determine whether an ir node can be proven to
                  be pure (side-effect free).  True if pure otherwise False.
                  ''')

# default to not pure
@defmethod(purep, [I.node])
def meth(node):
    return False

# operations that are always pure
@defmethod(purep, [(I.nop, I.constant, I.read_binding)])
def meth(node):
    return True

# operations that are never pure
@defmethod(purep, [(I.write_binding, I.delete_binding,
                    I.attrset, I.attrdel,
                    I.setitem, I.delitem,
                    I.return_, I.yield_,
                    I.raise0, I.raise1, I.raise3,
                    I.trycatch, I.tryfinally, I.tagbody, I.jump)])
def meth(node):
    return False

# operations that are pure when their children are pure
@defmethod(purep, [(I.unary_base, I.binary_base, I.attrget, I.getitem, I.progn, I.if_, I.function)])
def children_pure(node):
    return all(purep(child) for child in I.iter_children(node))

@defmethod(purep, [I.call])
def meth(node):
    try:
        callee = compile_time_resolve(node.callee)
    except UnresolvableError:
        return False
    else:
        if not callable_purep(callee):
            return False
    return children_pure(node)

