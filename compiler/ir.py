'''Intermediate Representation of code for compilation.

   Uses the port systems and magic attributes to access and manipulate
   control flow.
'''

from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.compiler.ir
    exit()

import itertools

from ..runtime.multimethod import defmethod, around
from ..runtime.ports import (Port, PortList, connect, disconnect,
                             get_cell, get_cells, DanglingPort)
from ..runtime.copy import copy, copy_obj
from ..runtime.symbol import Symbol
from ..runtime.atypes import (as_optimized_type, anytype, notanytype,
                              Seq, IsType, MemberType)
from . import bind
from .irbase import (node, defnode,
                     # node multimethods
                     init_ports, as_node,
                     iter_children, iter_bindings,
                     # utilities
                     replace_child, ir_location_str, copy_loc)


None_t = IsType(None)
bool_t = as_optimized_type(bool)


# # # # # # # # #
# No Operation  #
# # # # # # # # #

defnode('nop', optimized=True, result_type=None_t,
        doc='''
        no operation
        ''')

def replace_with_nop(op):
    replace_child(op, copy_loc(make_nop(), op))


# # # # # # #
# Constant  #
# # # # # # #

defnode('constant',
        attrs=['value'],
        make_name='inner_make_constant',
        optimized=True,
        doc='''
        load a constant value
        ''')

def make_constant(op):
    node = inner_make_constant(op)
    node.result_type = IsType(op)
    return node

defmethod(as_node, [anytype])(make_constant)

defnode('possible_constant',
        attrs=[('node', node)],
        bases=[constant],
        make_name='inner_make_possible_constant',
        args=['value', 'node'],
        doc='''
        Represent a node that is known at compile time to evaluates to a constant.
        Used commonly for functions, so functions can be evaled at compile time while
        including their code in final executable.
        See notes in constant_reduction.py.
        ''')

def make_possible_constant(value, node):
    node = inner_make_possible_constant(value, node)
    node.result_type = IsType(value)
    return node


# # # # # # # # # # # # #
# Symbol Cell Bindings  #
# # # # # # # # # # # # #

defnode('read_binding',
        bindings=['binding'],
        optimized=True)

defnode('write_binding',
        bindings=['binding'],
        children=['value'],
        args=['binding','value'])

defnode('delete_binding',
        bindings=['binding'],
        result_type=None_t,
        optimized=True)


# # # # # # # # # # #
# Unary Operations  #
# # # # # # # # # # #

defnode('unary_base', abstract=True,
        children=['op'])

unary_op_names = '''
  neg pos not_ convert invert get_iter
  '''.split()

defnode(unary_op_names, bases=[unary_base])

not_.result_type = bool_t
convert.result_type = as_optimized_type(str)


# # # # # # # # # # #
# Binary Operations #
# # # # # # # # # # #

defnode('binary_base', abstract=True,
        children=['lop','rop'])

binary_op_names = '''
  add subtract multiply divide floor_divide true_divide modulo
  iadd isubtract imultiply idivide ifloor_divide itrue_divide imodulo
  lshift rshift binand binor binxor
  ilshift irshift ibinand ibinor ibinxor
  '''.split()

defnode(binary_op_names, bases=[binary_base])

defnode('comparision_base', abstract=True,
        bases=[binary_base],
        result_type=bool_t)

cmp_op_names = '''
  gt ge eq ne le lt in_ notin is_ isnot exception_match
'''.split()

defnode(cmp_op_names, bases=[comparision_base])


# # # # # # # #
# Attributes  #
# # # # # # # #

defnode('attrbase', abstract=True,
        children=['obj'],
        attrs=[('name', str)])

defnode('attrget', bases=[attrbase],
        args=['name','obj'])

defnode('attrset', bases=[attrbase],
        children=['value'],
        args=['name','obj','value'])

defnode('attrdel', bases=[attrbase],
        args=['name','obj'],
        result_type=None_t)


# # # # #
# Item  #
# # # # #

defnode('itembase', abstract=True,
        children=['op','item'])

defnode('getitem', bases=[itembase],
        args=['op','item'])

defnode('setitem', bases=[itembase],
        children=['value'],
        args=['op','item','value'])

defnode('delitem', bases=[itembase],
        result_type=None_t,
        args=['op','item'])


# # # # #
# Slice #
# # # # #

defnode('buildslice',
        children=['start','stop','step'],
        result_type=slice)

defnode('unpack_seq',
        children=['seq'],
        bindinglists=['places'],
        args=['seq','places'])


# # # # #
# Progn #
# # # # #

defnode('progn',
        childlists=['exprs'])


# # # # #
# Call  #
# # # # #

defnode('call',
        attrs=[('kwd_names', Seq(str))],
        children=['callee', 'star_args', 'star_kwds'],
        childlists=['args','kwd_values'],
        args=['callee', 'args', 'kwd_names', 'kwd_values', 'star_args', 'star_kwds'])


# # # # # # # #
# Conditional #
# # # # # # # #

defnode('if_',
        children=['condition','then','else_'])


# # # # # #
# Return  #
# # # # # #

defnode('return_',
        children=['value'],
        result_type=notanytype)


# # # # #
# Yield #
# # # # #

defnode('yield_',
        children=['value'])


# # # # # # # # # # #
# Exception Raising #
# # # # # # # # # # #

defnode('raise_', result_type=notanytype)

defnode('raise0', bases=[raise_], optimized=True)

defnode('raise1',
        bases=[raise_],
        children=['value'])

defnode('raise3',
        bases=[raise_],
        children=['type', 'value', 'traceback'])


# # # # # # # # # # # #
# Exception Catching  #
# # # # # # # # # # # #

defnode('trycatch',
        result_type=None_t,
        children=['body', 'catch'],
        bindings=['exc_type_binding',
                  'exc_value_binding',
                  'exc_tb_binding'])


# # # # # # # #
# Try Finally #
# # # # # # # #

defnode('tryfinally',
        result_type=None_t,
        children=['body', 'finally_'])


# # # # # # #
# Tag Body  #
# # # # # # #

defnode('tag',
        children=['body'],
        make_name='inner_make_tag',
        result_type=notanytype,
        attrs=[('tagid', int),
               ('symbol', (Symbol, type(None)))])

next_tag_id = iter(itertools.count()).next

def make_tag(symbol, body):
    return inner_make_tag(body=body, tagid=next_tag_id(), symbol=symbol)

@defmethod(init_ports, [tag], combination=around)
def meth(callnext, tg):
    callnext(tg)
    tg._uses = PortList(tg)

@defmethod(copy_obj, [tag], combination=around)
def meth(callnext, tg):
    cp = callnext(tg)
    cp._uses = PortList(cp) #copies handled in children
    return cp

def get_uses(tg):
    return get_cells(tg._uses)

tag.uses = property(get_uses)


defnode('jump')

@defmethod(init_ports, [jump], combination=around)
def meth(callnext, jp):
    callnext(jp)
    jp._tag = Port(jp)

def get_jump_tag(jp):
    try:
        return get_cell(jp._tag)
    except DanglingPort:
        return None

def set_jump_tag(jp, tg):
    del_jump_tag(jp)
    if tg is not None:
        if not isinstance(tg, tag):
            raise TypeError("tag attribute of %s must be a tag instance; given %s" %
                            (type(jp).__name__, tg))
        connect(jp._tag, tg._uses)

def del_jump_tag(jp):
    tg = get_jump_tag(jp)
    if tg:
        disconnect(jp._tag, tg._uses)

jump.tag = property(get_jump_tag,
                    set_jump_tag,
                    del_jump_tag)


@defmethod(copy_obj, [jump], combination=around)
def meth(callnext, jp):
    cp = callnext(jp)
    cp.tagid = next_tag_id()
    cp._tag = Port(cp)
    connect(cp._tag, copy(jp.tag)._uses)
    return cp


defnode('go',
        bases=[jump],
        optimized=True,
        result_type=notanytype,
        args=['tag'])

defnode('foriter',
        bases=[jump],
        children=['iter'],
        bindings=['binding'],)

defnode('tagbody',
        result_type=None_t,
        childlists=['tags'])


# # # # # # #
# Function  #
# # # # # # #

defnode('basefunction',
        result_type=type(lambda x: None),
        childlists=['defaults'],
        bindinglists=['args', 'kwds'],
        bindings=['star_args', 'star_kwds'],
        attrs=[('name', str),
               ('doc', (type(None), str)),
               ('scope', bind.Scope)])


defnode('function',
        bases=[basefunction],
        children=['body'])

# defnode('non_const_function',
#         bases=[basefunction],
#         attrs=[('inner_function', basefunction)],
#         bindings=['code_binding'])

# # # # # # #
# Eval When #
# # # # # # #

W_COMPILE_TOPLEVEL, W_LOAD_TOPLEVEL, W_EXECUTE = WHENS = range(3)
when_t = MemberType(WHENS)

defnode('evalwhen',
        result_type=notanytype,
        children=['expression'],
        attrs=[('when', Seq(when_t))],
        args=['when','expression'])


# # # # # # # # # #
# Pre-Evaluation  #
# # # # # # # # # #

defnode('preeval',
        children=['expression'])

defnode('load_time_value',
        bases=[preeval])

defnode('compile_time_value',
        bases=[preeval])

# # # # # # # # # #
# Top Level Form  #
# # # # # # # # # #

defnode('toplevel',
        children=['expression'],
        attrs=[('scope', bind.Scope)],
        args=['expression','scope']
        )

def get_node_local_scope(ir):
    if ir is None:
        raise RuntimeError("node not inside a function or a toplevel form")
    if isinstance(ir, (toplevel, basefunction)):
        return ir.scope
    #defaults belong to scope above function
    if isinstance(ir.continuation, function) and ir in ir.continuation.defaults:
        return get_node_local_scope(ir.continuation.continuation)
    return get_node_local_scope(ir.continuation)


# # # # # #
# Import  #
# # # # # #

defnode('import_name',
        attrs=[('name', str)])



# # # # # # #
# Utilities #
# # # # # # #

def syntax_error(node, msg, *args):
    raise SyntaxError(msg%args if args else msg,
                      (node.filename, node.lineno, node.colno,
                       as_string(node)))
