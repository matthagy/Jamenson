'''ports for bilatterally connecting cells
   for creating arbitary bidirectional graphs
'''

from jamenson.runtime.multimethod import MultiMethod, defmethod

__all__ = '''PortError DanglingPort AmbiguousConnection BreakNonExisting
             Port PortList
             get_cells get_cell count_connections
             connect disconnect disconnect_all replace_connection
             '''.split()


class PortError(Exception):
    pass

class DanglingPort(PortError):
    def __str__(self):
        return 'Port is not connected'

class AmbiguousConnection(PortError):
    def __str__(self):
        return 'Port is overly connected for use'

class BreakNonExisting(PortError):
    def __str__(self):
        return 'Attempting to break non-existing connection'


class PortBase(object):

    __ports__ = []

class Port(PortBase):
    '''relate a single cell to a single connection
    '''

    __ports__ = ['port','cell']

    def __init__(self, cell):
        self.cell = cell
        self.port = None

class PortList(PortBase):
    '''relate a single cell to zero or more connections
    '''

    __ports__ = ['ports','cell']

    def __init__(self, cell):
        self.cell = cell
        self.ports = []


get_cells = MultiMethod('get_cells',
                        doc='get cells connected to this port')
get_cell = MultiMethod('get_cell',
                       doc='get single cell connected to this port')
count_connections = MultiMethod('count_connections',
                                doc='number of connection for this port')
connect = MultiMethod('connect',
                      doc='connect two ports')
disconnect = MultiMethod('disconnect',
                            doc='disconnect two ports')
disconnect_all = MultiMethod('disconnect_all',
                             doc='disconnect all connections for this port')
replace_connection = MultiMethod('replace_connection',
                                 signature='one_end,old_other,new_other')
disconnect_other = MultiMethod('disconnect_other',
                               doc='disconnect other end of port; only used internally')


@defmethod(get_cells, [Port])
def meth(p):
    return [p.port.cell] if p.port is not None else []

@defmethod(get_cells, [PortList])
def meth(pl):
    return [p.cell for p in pl.ports]

@defmethod(get_cell, [Port])
def meth(p):
    if p.port is None:
        raise DanglingPort
    return p.port.cell

@defmethod(get_cell, [PortList])
def meth(pl):
    if not pl.ports:
        raise DanglingPort
    elif len(pl.ports)!=1:
        raise AmbiguousConnection
    return pl.ports[0]

@defmethod(count_connections, [Port])
def meth(p):
    return 1 if p.port is not None else 0

@defmethod(count_connections, [PortList])
def meth(pl):
    return len(pl.ports)

@defmethod(connect, [Port, Port])
def meth(a,b):
    if a is b:
        raise PortError('cannot self connect ports')
    if a.port is not None:
        disconnect(a, a.port)
    if b.port is not None:
        disconnect(b, b.port)
    a.port = b
    b.port = a

@defmethod(connect, [Port, PortList])
def meth(p,pl):
    if p.port is not None:
        disconnect(p, p.port)
    p.port = pl
    assert p not in pl.ports
    pl.ports.append(p)

@defmethod(connect, [PortList, Port])
def meth(pl,p):
    connect(p,pl)

@defmethod(connect, [PortList, PortList])
def meth(a,b):
    if a is b:
        raise PortError('cannot self connect ports')
    if a in b.ports:
        #don't form multiple connections
        assert b in a.ports
        return
    a.ports.append(b)
    b.ports.append(a)

@defmethod(disconnect, [Port,Port])
def meth(a,b):
    if a.port is not b:
        raise BreakNonExisting
    assert b.port is a
    disconnect_all(a)
    assert a.port is None
    assert b.port is None

@defmethod(disconnect, [Port,PortList])
def meth(p,pl):
    if p not in pl.ports:
        raise BreakNonExisting
    disconnect_all(p)
    assert p.port is None
    assert p not in pl.ports

@defmethod(disconnect, [PortList,Port])
def meth(pl,p):
    disconnect(p,pl)

@defmethod(disconnect, [PortList,PortList])
def meth(a,b):
    if b not in a.ports:
        raise BreakNonExisting
    a.ports.remove(b)
    b.ports.remove(a)

@defmethod(disconnect_all, [Port])
def meth(p):
    if p.port is not None:
        disconnect_other(p.port, p)
        p.port = None

@defmethod(disconnect_all, [PortList])
def meth(pl):
    for x in pl.ports:
        disconnect_other(x, pl)
    del pl.ports[::]

@defmethod(disconnect_other, [Port,PortBase])
def meth(p, x):
    assert p.port is x
    p.port = None

@defmethod(disconnect_other, [PortList,PortBase])
def meth(pl, x):
    pl.ports.remove(x)


@defmethod(replace_connection, [Port, PortBase, PortBase])
def meth(p, old, new):
    assert p.port is old
    disconnect(p, old)
    connect(p, new)

connect_other = MultiMethod('connect_other')

@defmethod(connect_other, [PortList, PortBase])
def meth(pl, other):
    pl.ports.append(other)

@defmethod(connect_other, [Port, PortBase])
def meth(p, other):
    if p.port is not None:
        disconnect_all(p)
    assert p.port is None
    p.port = other

@defmethod(replace_connection, [PortList, PortBase, PortBase])
def meth(pl, old, new):
    inx = pl.ports.index(old)
    pl.ports[inx] = new
    disconnect_other(old, pl)
    connect_other(new, pl)

class PortCollection(object):

    def __init__(self, item_attr_name, cell):
        self.item_attr_name = item_attr_name
        self.port = PortList(cell)

    def get_item_port(self, item):
        return getattr(item, self.item_attr_name)


class AttrPortList(PortCollection):

    def append(self, other):
        connect(self.port, self.get_item_port(other))

    def remove(self, other):
        disconnect(self.port, self.get_item_port(other))

    def __iter__(self):
        return iter(get_cells(self.port))

    def __len__(self):
        return count_connections(self.port)

    def __contains__(self, el):
        return el in get_cells(self.port)

    def extend(self, seq):
        for el in seq:
            self.append(el)

    def index(self, el):
        for i,i_el in enumerate(self):
            if el == i_el:
                return i
        raise ValueError

    def __getitem__(self, index):
        return get_cells(self.port)[index]

    def __setitem__(self, index, el):
        replace_connection(self.port,
                           self.get_item_port(self[index]),
                           self.get_item_port(el))

    def __delitem__(self, index):
        if not isinstance(index, slice):
            index = slice(index, index+1, 1)
        else:
            l = len(self)
            start,stop,step = index.indices(l)
            if start==0 and step==1 and stop==l:
                disconnect_all(self.port)
                return
        for el in self[index]:
            disconnect(self.port,self.get_item_port(el))




class AttrPortMapping(PortCollection):

    def __init__(self, item_attr_name, cell):
        super(AttrPortMapping, self).__init__(item_attr_name, cell)
        self.key_list = []

    no_default = object()
    def _index_key(self, key, default=no_default):
        try:
            return self.key_list.index(key)
        except ValueError:
            if default is self.no_default:
                raise KeyError
            return default

    def __getitem__(self, key):
        return self.port.ports[self._index_key(key)].cell

    def __setitem__(self, key, value):
        index = self._index_key(key, None)
        if index is None:
            self.key_list.append(key)
            connect(self.port, self.get_item_port(value))
        else:
            replace_connection(self.port,
                               self.port.ports[index],
                               self.get_item_port(value))

    def __delitem__(self, key):
        index = self._index_key(key)
        del self.key_list[index]
        disconnect(self.port, self.port.ports[index])

    def __iter__(self):
        return iter(self.key_list)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return self.key_list[::]

    def values(self):
        return get_cells(self.port)

    def items(self):
        return zip(self.key_list, get_cells(self.port))

    def iterkeys(self):
        return iter(self.key_list)

    def itervalues(self):
        return iter(get_cells(self.port))

    def iteritems(self):
        return iter(self.items())

    def update(self, seq):
        if hasattr(seq, 'iteritems'):
            seq = seq.iteritems()
        for k,v in seq:
            self[k] = v

    def clear(self):
        del self.key_list[::]
        disconnect_all(self.port)

    def __len__(self):
        return len(self.key_list)

    def __contains__(self, key):
        return key in self.key_list

