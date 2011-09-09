'''Base class and framework for intermediate representation
'''

import sys
import new
import operator
from functools import partial

from ..runtime.func import identity
from ..runtime.collections import OrderedSet
from ..runtime.multimethod import MultiMethod, defmethod
from ..runtime.ports import (Port, connect, disconnect, disconnect_all, replace_connection,
                             get_cell, DanglingPort, AttrPortList)
from ..runtime.as_string import StringingMixin, as_string
from ..runtime.copy import copy, copy_obj, set_copy
from ..runtime.atypes import as_optimized_type, typep, anytype
from ..runtime.atypes.ptypes import function_type


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

def _defnode(name, gbls, *args, **kwds):
    '''declarative dsl to define nodes
    '''
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
    try:
        gbls = kwds.pop('globals')
    except KeyError:
        gbls = sys._getframe(kwds.pop('depth',1)).f_globals

    if isinstance(name_or_list, list):
        return [defnode(name, globals=gbls, **kwds) for name in name_or_list]
    return _defnode(name_or_list, gbls, **kwds)


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

