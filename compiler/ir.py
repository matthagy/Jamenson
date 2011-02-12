'''Intermediate Representation of code for compilation
'''

from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.compiler.ir
    exit()

import sys
import new
import operator
import itertools
from functools import partial

from ..runtime.func import identity
from ..runtime.collections import OrderedSet
from ..runtime.multimethod import MultiMethod, defmethod, around
from ..runtime.ports import (Port, PortList, connect, disconnect, disconnect_all, replace_connection,
                             get_cell, get_cells, DanglingPort, AttrPortList)
from ..runtime.as_string import StringingMixin, as_string
from ..runtime.copy import copy, copy_obj, set_copy
from ..runtime.delete import delete, delete_obj
from ..runtime.symbol import Symbol
from ..runtime.atypes import (as_optimized_type, union, typep, anytype, notanytype,
                              Seq, IsType, MemberType)
from ..runtime.atypes.ptypes import typep, function_type

from . import bind


None_t = IsType(None)
bool_t = as_optimized_type(bool)

class ChildrenList(AttrPortList):
    """sequence of children nodes each of whom's continuation is recieved
       in parent node
    """

    def __init__(self, parent):
        super(ChildrenList, self).__init__('continuation_port', parent)


class BindingList(AttrPortList):
    '''sequence of bindings who are used in contained node
    '''

    def __init__(self, parent):
        super(BindingList, self).__init__('user_port', parent)


class node(StringingMixin):
    '''base class for all ir nodes
    '''

    _children = []
    _childlists = []
    _bindings = []
    _bindinglists = []

    _attrs = ['lineno', 'colno', 'filename',
              'optimized',
              'result_ignored', 'result_type']

    lineno = None
    colno = None
    filename = None

    #transformation information
    optimized = False

    #annotations
    result_ignored = False
    result_type = anytype

    def continuation():
        def get(self):
            try:
                return get_cell(self.continuation_port)
            except DanglingPort:
                return None
        def set(self, value):
            if value is not None:
                raise RuntimeError("setting continuation in child is ambiguous")
            del_(self)
        def del_(self):
            disconnect_all(self.continuation_port)
        return property(get, set, del_)
    continuation = continuation()



# # # # # # # # # # # # # # # #
# Accessor to Port Attributes #
# # # # # # # # # # # # # # # #

def base_init_func(cls, arg_mapping, *args, **kwds):
    assert len(args) <= len(arg_mapping)
    node = cls()
    init_ports(node)
    for k,v in zip(arg_mapping, args):
        setattr(node, k, v)
    for k,v in kwds.iteritems():
        setattr(node, k, v)
    return node

def base_get_child(name, node):
    port = getattr(node, name)
    try:
        return get_cell(port)
    except DanglingPort:
        return None

def base_set_child(name, node, child):
    try:
        base_del_child(name, node)
    except AttributeError:
        pass
    if child is not None:
        connect(getattr(node,name), as_node(child).continuation_port)

def base_del_child(name, node):
    port = getattr(node, name)
    try:
        child = get_cell(port)
    except DanglingPort:
        raise AttributeError
    else:
        disconnect(port, child.continuation_port)


def base_get_childlist(name, node):
    return getattr(node, name)

def base_set_childlist(name, node, seq):
    base_del_childlist(name, node)
    getattr(node, name).extend(seq)

def base_del_childlist(name, node):
    del getattr(node, name)[::]


def base_get_binding(name, node):
    port = getattr(node, name)
    try:
        return get_cell(port)
    except DanglingPort:
        return None

def base_set_binding(name, node, binding):
    try:
        base_del_binding(name, node)
    except AttributeError:
        pass
    if binding is not None:
        if binding.user:
            raise RuntimeError('attempting to reuse binding %s' % (binding,))
        connect(getattr(node, name), binding.user_port)

def base_del_binding(name, node):
    port = getattr(node, name)
    try:
        binding = get_cell(port)
    except DanglingPort:
        raise AttributeError
    else:
        disconnect(port, binding.user_port)

def base_get_bindinglist(name, node):
    return getattr(node, name)

def base_set_bindinglist(name, node, seq):
    base_del_bindinglist(name, node)
    getattr(node, name).extend(seq)

def base_del_bindinglist(name, node):
    del getattr(node, name)[::]


def base_check_type_set_attr(tp, n, node, value):
    if not typep(value, tp):
        raise TypeError("cannot assign %r to %s.%s; not of type %s" %
                        (value, node.__class__.__name__, n[1:], as_string(tp)))
    setattr(node, n, value)

def build_accessors(dct, names, base_get, base_set, base_del):
    for n in names:
        inner_name = '_' + n
        dct[n] = property(partial(base_get, inner_name),
                          partial(base_set, inner_name),
                          partial(base_del, inner_name))

# # # # # # # # # # #
# Node Construction #
# # # # # # # # # # #

def bases_collect_list(bases, attr):
    bases_set = OrderedSet()
    for base in bases:
        bases_set.update(base.mro())
    acc = []
    for base in bases_set:
        acc.extend(getattr(base, attr, ()))
    return acc

def createnode(name, children=[], childlists=[],
               bindings=[], bindinglists=[], attrs=[],
               args=None, bases=[], doc='', cls_attrs=None,
               optimized=None, result_type=None):
    d = dict(__doc__=doc)
    if cls_attrs:
        d.update(cls_attrs)
    if optimized is not None:
        d['optimized'] = optimized
    if result_type is not None:
        d['result_type'] = as_optimized_type(result_type)
    build_accessors(d, children, base_get_child, base_set_child, base_del_child)
    build_accessors(d, childlists, base_get_childlist, base_set_childlist, base_del_childlist)
    build_accessors(d, bindings, base_get_binding, base_set_binding, base_del_binding)
    build_accessors(d, bindinglists, base_get_bindinglist, base_set_bindinglist, base_del_bindinglist)
    xattrs = []
    for n in attrs:
        if isinstance(n,str):
            xattrs.append(n)
        else:
            n,tp = n
            xattrs.append(n)
            d[n] = property(operator.attrgetter('_'+n),
                            partial(base_check_type_set_attr,
                                    as_optimized_type(tp), '_'+n))
    bases = list(bases)
    if node not in bases:
        bases = bases + [node]
    children = bases_collect_list(bases, '_children') + children
    childlists = bases_collect_list(bases, '_childlists') + childlists
    bindings = bases_collect_list(bases, '_bindings') + bindings
    bindinglists = bases_collect_list(bases, '_bindinglists') + bindinglists
    attrs = bases_collect_list(bases, '_attrs') +  attrs
    d['_children'] = children
    d['_childlists'] = childlists
    d['_bindings'] = bindings
    d['_bindinglists'] = bindinglists
    d['_attrs'] = attrs
    if args is None:
        args = xattrs + bindings + bindinglists + children + childlists
    cls = new.classobj(name, tuple(bases), d)
    maker = partial(base_init_func, cls, args)
    return cls, maker

def _defnode(name, *args, **kwds):
    '''declarative dsl to define nodes
    '''
    gbls = sys._getframe(kwds.pop('depth',1)).f_globals
    make_name = kwds.pop('make_name', None)
    abstract = kwds.pop('abstract', False)
    cls,maker = createnode(name, *args, **kwds)
    gbls[name] = cls
    if not abstract:
        if make_name is None:
            make_name = 'make_%s' % name
        elif typep(make_name, function_type):
            make_name = make_name(name) # used with sequences
        gbls[make_name] = maker
    return cls

def defnode(name_or_list, **kwds):
    if isinstance(name_or_list, list):
        return [defnode(name,**kwds) for name in name_or_list]
    return _defnode(name_or_list, **kwds)


# # # # # # # # # # # # # # # #
# Node Behavior Multimethods  #
# # # # # # # # # # # # # # # #

init_ports = MultiMethod('init_ports')

@defmethod(init_ports, [node])
def meth(node):
    node.continuation_port = Port(node)
    init_child_ports(node)
    init_binding_ports(node)

def init_binding_ports(node):
    for n in node.__class__._bindings:
        setattr(node, '_'+n, Port(n))
    for n in node.__class__._bindinglists:
        setattr(node, '_'+n, BindingList(node))

def init_child_ports(node):
    for n in node.__class__._children:
        setattr(node, '_'+n, Port(node))
    for n in node.__class__._childlists:
        setattr(node, '_'+n, ChildrenList(node))


as_node = MultiMethod(name='as_node',
                      signature='op',
                      doc='''
                      ''')

defmethod(as_node, [node])(identity)


iter_children = MultiMethod(name='iter_children',
                           signature='node',
                           doc="""
                           iterate the children nodes whose continuations
                           are used in this node
                           """)

@defmethod(iter_children, [node])
def meth(node):
    for attr in node._children:
        child = getattr(node, attr)
        if child is not None:
            yield child
    for attr in node._childlists:
        for child in getattr(node, attr):
            yield child


iter_bindings = MultiMethod(name='iter_bindings',
                            signature='node',
                            doc="""
                            iterate the bindings used in this node,
                            but not the nodes's children
                            """)

@defmethod(iter_bindings, [node])
def meth(node):
    for name in node._bindings:
        binding = getattr(node, name)
        if binding is not None:
            yield binding
    for name in node._bindinglists:
        for binding in getattr(node, name):
            yield binding

@defmethod(copy_obj, [node])
def meth(node):
    cp = node.__class__.__new__(node.__class__)
    set_copy(node, cp)
    init_ports(cp)
    for attr in node._attrs:
        if isinstance(attr, tuple):
            attr,_ = attr
        setattr(cp, attr, copy(getattr(node, attr)))
    for attr in node._children:
        setattr(cp, attr, copy(getattr(node, attr)))
    for attr in node._childlists:
        setattr(cp, attr, map(copy, getattr(node, attr)))
    for attr in node._bindings:
        setattr(cp, attr, copy(getattr(node, attr)))
    for attr in node._bindinglists:
        setattr(cp, attr, map(copy, getattr(node, attr)))
    return cp


# # # # # # #
# Utilities #
# # # # # # #

def syntax_error(node, msg, *args):
    raise SyntaxError(msg%args if args else msg,
                      (node.filename, node.lineno, node.colno,
                       as_string(node)))

def replace_child(old, new):
    replace_connection(old.continuation_port.port,
                       old.continuation_port,
                       new.continuation_port)

def ir_location_str(ir):
    return '%s:%s.%s' % ('?' if ir.filename is None else ir.filename,
                         '?' if ir.lineno is None else ir.lineno,
                         '?' if ir.colno is None else ir.colno)

def copy_loc(dst, src):
    dst.filename = src.filename
    dst.lineno = src.lineno
    dst.colno = src.colno
    return dst


# # # #
# Nop #
# # # #

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


