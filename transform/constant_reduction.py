'''Evaluate constant expressions in ir.
'''

from __future__ import absolute_import
from __future__ import with_statement

import operator as O
import types

from ..runtime.multimethod import MultiMethod, defmethod, around
from ..runtime.picklep import picklep
from ..runtime.copy import make_copy
from ..runtime.purity import purep
from ..compiler.resolution import compile_time_resolve, UnresolvableError
from ..compiler.walk import propigate_location, IRWalker
from ..compiler import ir as I
from ..compiler import codegen
from ..compiler import bind


constant_reduce = MultiMethod('constant_reduce',
                              signature='node',
                              doc='''
                              If possible, reduce expression to simpler expression.
                              Called after children nodes have been reduced to simpler nodes
                              ''')

def handle_constants(node):
    node = reduce_constants(node)
    node = fix_possible_constants(node)
    return node

def reduce_constants(node):
    #reduce children first
    for child in list(I.iter_children(node)):
        r_child = reduce_constants(child)
        if r_child is not child:
            #print 'node', child, r_child
            I.replace_child(child, r_child)
    return constant_reduce(node)


class PossibleConstantFixer(IRWalker):
    """We don't want to include any non-pickleable objects as constants.
       On the other hand, we do want all constant values availabe for
       constant reduction as non-pickleable constants can be used to
       reduce expression to pickleable ones.
       This is accomplished by marking all reduction produced constants as
       `possible_constants` where we still keep the generating ir node around.
       After all reduction, non-pickleable possible_constants are replaced by
       the ir repressentation where as pickleable constants are converted to
       regular constants.
    """

    descend_into_functions = True

    def visit_possible_constant(self, pc):
        if picklep(pc.value):
            I.replace_child(pc, I.make_constant(pc.value))
        else:
            I.replace_child(pc, pc.node)
            self.visit(pc.node)


def fix_possible_constants(node):
    if isinstance(node, I.possible_constant):
        return fix_possible_constants(I.make_toplevel(node, bind.Scope())).expression
    PossibleConstantFixer().visit(node)
    return node


class NotConstant(Exception):
    pass

no_default = object()
def as_value(op, default=no_default):
    if op is None and default is not no_default:
        return default
    if not isinstance(op, I.constant):
        raise NotConstant
    return op.value

def catch_notconstant(func):
    def inner(node, *args, **kwds):
        try:
            return func(node, *args, **kwds)
        except NotConstant:
            return node
    return inner

def mkcnst(node, value):
    return propigate_location(node, I.make_possible_constant(value, node))

@catch_notconstant
def reduce_through_function(node, func):
    return mkcnst(node, evaluate_catch(node, func, *map(as_value, I.iter_children(node))))

def evaluate_catch(node, func, *args):
    try:
        return func(*args)
    except Exception:
        # Could insert code to handle errors here as they aren't neccessarily fatal.
        # We can always revert back to the original node if the function is incapable of
        # reduction.
        # Need a way to distinguish such expected errors from programming errors.
        raise


#by default do nothing
@defmethod(constant_reduce, [I.node])
def meth(node):
    return node

unary_functions = {
    I.neg      : O.neg,
    I.pos      : O.pos,
    I.not_     : O.not_,
    I.convert  : repr,
    I.invert   : O.invert,
    I.get_iter : iter,
}

@defmethod(constant_reduce, [I.unary_base])
def meth(node):
    return reduce_through_function(node, unary_functions[type(node)])

binary_functions = {
    I.add             : O.add,
    I.subtract        : O.sub,
    I.multiply        : O.mul,
    I.divide          : O.div,
    I.floor_divide    : O.floordiv,
    I.true_divide     : O.truediv,
    I.modulo          : O.mod,
    I.iadd            : O.iadd,
    I.isubtract       : O.isub,
    I.imultiply       : O.imul,
    I.idivide         : O.idiv,
    I.ifloor_divide   : O.ifloordiv,
    I.itrue_divide    : O.itruediv,
    I.imodulo         : O.imod,
    I.lshift          : O.lshift,
    I.rshift          : O.rshift,
    I.binand          : O.and_,
    I.binor           : O.or_,
    I.binxor          : O.xor,
    I.ibinand         : O.iand,
    I.ibinor          : O.ior,
    I.ibinxor         : O.ixor,
    I.eq              : O.eq,
    I.ne              : O.ne,
    I.gt              : O.gt,
    I.ge              : O.ge,
    I.eq              : O.eq,
    I.le              : O.le,
    I.lt              : O.lt,
    I.in_             : O.contains,
    I.notin           : lambda x,seq: x not in seq,
    I.is_             : O.is_,
    I.isnot           : O.is_not,
    I.exception_match : isinstance,
}

@defmethod(constant_reduce, [I.binary_base])
def meth(node):
    return reduce_through_function(node, binary_functions[type(node)])

@defmethod(constant_reduce, [I.attrget])
@catch_notconstant
def meth(node):
    return mkcnst(node, evaluate_catch(node, getattr, as_value(node.obj), node.name))

@defmethod(constant_reduce, [I.getitem])
@catch_notconstant
def meth(node):
    return mkcnst(node, evaluate_catch(node, lambda op, item: op[item], as_value(node.op), as_value(node.item)))

@defmethod(constant_reduce, [I.progn])
@catch_notconstant
def meth(node):
    if not node.exprs:
        return I.copy_loc(I.make_nop(), node)
    for expr in node.exprs:
        value = as_value(expr)
    return mkcnst(node, value)


@defmethod(constant_reduce, [I.call])
@catch_notconstant
def meth(node):
    callee = as_value(node.callee)
    if not purep(callee):
        raise NotConstant
    star_args = as_value(node.star_args, [])
    star_kwds = as_value(node.star_kwds, {})
    args = map(as_value, node.args)
    kwds = dict(zip(node.kwd_names, map(as_value, node.kwd_values)))
    def perform_call():
        if set(kwds) & set(star_kwds):
            #could insert code to raise this error at runtime (possibly expected?)
            raise ValueError("multiple values for same keyword")
        kwds.update(star_kwds)
        return callee(*(args + star_args), **kwds)
    return mkcnst(node, evaluate_catch(node, perform_call))

@defmethod(constant_reduce, [I.if_])
@catch_notconstant
def meth(node):
    return node.then if as_value(node.condition) else node.else_

@defmethod(constant_reduce, [I.function])
@catch_notconstant
def meth(func):
    if codegen.get_function_free_bindings(func):
        return func
    map(as_value, func.defaults)
    #must import here to prevent cyclic imports
    from ..compiler.function import make_function
    return mkcnst(func, make_function(make_copy(func)))

