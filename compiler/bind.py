
from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.compiler.bind
    jamenson.compiler.bind.test()
    exit()


from ..runtime.ports import (Port, PortList, connect, disconnect, disconnect_all, replace_connection,
                             count_connections, get_cell, get_cells, DanglingPort,
                             AttrPortList, AttrPortMapping)
from ..runtime.ctxsingleton import CtxSingleton
from ..runtime.multimethod import defmethod
from ..runtime.copy import copy_obj, copy, get_copy, set_copy
from ..runtime.as_string import as_string, StringingMixin


#Binding Use Scoping
BND_GLOBAL, BND_LOCAL, BND_CELL, BND_FREE = BND_USE_SCOPINGS = range(4)
BND_CONCRETE = BND_LOCAL, BND_CELL, BND_FREE


class ScopableBase(StringingMixin):

    def __init__(self):
        self.scope_port = Port(self)

    @property
    def scope(self):
        try:
            return get_cell(self.scope_port)
        except DanglingPort:
            return None

class BindingUseMixin(object):

    def __init__(self):
        self.user_port = Port(self)

class BindingUse(ScopableBase, BindingUseMixin):

    def __init__(self, binding):
        ScopableBase.__init__(self)
        BindingUseMixin.__init__(self)
        self.binding_port = Port(self)
        self.binding = binding

    def binding():
        def get(self):
            try:
                return get_cell(self.binding_port)
            except DanglingPort:
                return None
        def set(self, binding):
            del_(self)
            if binding is not None:
                if not isinstance(binding, Binding):
                    raise TypeError("can't assign type %s to binding"
                                    % (type(binding).__name__,))
                binding.uses.append(self)
        def del_(self):
            if self.binding is not None:
                self.binding.uses.remove(self)
        return property(get, set, del_)
    binding = binding()

    @property
    def user(self):
        try:
            return get_cell(self.user_port)
        except DanglingPort:
            return None

    @property
    def symbol(self):
        if not self.binding:
            return None
        return self.binding.symbol

@defmethod(as_string, [BindingUse])
def meth(bu):
    return '<%s %s %s>' % (bu.__class__.__name__,
                           bu.binding,
                           {BND_GLOBAL : 'global',
                            BND_LOCAL  : 'local',
                            BND_CELL   : 'cell',
                            BND_FREE   : 'free'}[get_binding_use_type(bu)])

@defmethod(copy_obj, [BindingUse])
def meth(bu):
    return BindingUse(copy(bu.binding))


class ConcreteBindingUse(BindingUseMixin):

    def __init__(self, name, use_type):
        assert isinstance(name, str)
        assert use_type in BND_CONCRETE
        BindingUseMixin.__init__(self)
        self.name = name
        self.use_type = use_type

class BindableBase(ScopableBase):

    def __init__(self, symbol):
        ScopableBase.__init__(self)
        self.symbol = symbol


class Binding(BindableBase):

    def __init__(self, symbol):
        BindableBase.__init__(self, symbol)
        self.uses_port = AttrPortList('binding_port', self)

    def uses():
        def get(self):
            return self.uses_port
        def set(self, seq):
            del_(self)
            self.uses_port.extend(seq)
        def del_(self):
            del self.uses_port[::]
        return property(get, set, del_)
    uses = uses()

@defmethod(as_string, [Binding])
def meth(bn):
    return '<%s %s 0x%X>' % (bn.__class__.__name__, bn.symbol, id(bn))

@defmethod(copy_obj, [Binding])
def meth(b):
    return Binding(b.symbol)



class Macrolet(BindableBase):

    def __init__(self, symbol, macro):
        BindableBase.__init__(self, symbol)
        self.macro = macro


class SymbolMacrolet(BindableBase):

    def __init__(self, symbol, form):
        BindableBase.__init__(self, symbol)
        self.form = form


macro_types = Macrolet, SymbolMacrolet


class Scope(StringingMixin):

    def __init__(self, parent=None, manage_locals=None):
        self.child_scopes_port = AttrPortList('parent_port', self)
        self.parent_port = Port(self)
        if manage_locals is None:
            manage_locals = parent is None
        assert parent or manage_locals, 'no local managment for scope'
        self.parent = parent
        self.manage_locals = manage_locals
        self.bindings_port = AttrPortMapping('scope_port', self)
        self.binding_uses_port = AttrPortList('scope_port', self)

    def parent():
        def get(self):
            try:
                return get_cell(self.parent_port)
            except DanglingPort:
                return None
        def set(self, parent):
            del_(self)
            if parent is not None:
                parent.child_scopes_port.append(self)
        def del_(self):
            disconnect_all(self.parent_port)
        return property(get, set, del_)
    parent = parent()

    @property
    def top(self):
        if not self.parent:
            return self
        return self.parent.top

    @property
    def depth(self):
        depth = 0
        scope = self
        while scope.parent:
            depth += 1
            scope = scope.parent
        return depth

    def child_scopes():
        def get(self):
            return self.child_scopes_port
        def set(self, seq):
            _del(self)
            self.child_scopes_port.extend(seq)
        def del_(self):
            del self.child_scopes_port[::]
        return property(get, set, del_)
    child_scopes = child_scopes()

    def bindings():
        def get(self):
            return self.bindings_port
        def set(self, mapping):
            del_(self)
            self.bindings_port.update(mapping)
        def del_(self):
            self.bindings_port.clear()
        return property(get, set, del_)
    bindings = bindings()

    def binding_uses():
        def get(self):
            return self.binding_uses_port
        def set(self, seq):
            del_(self)
            self.binding_uses_port.extend(seq)
        def del_(self):
            del self.binding_uses_port[::]
        return property(get, set, del_)
    binding_uses = binding_uses()

    #api
    def create_child(self, new_locals=False):
        return self.__class__(parent=self, manage_locals=new_locals)

    def register_local(self, sym):
        return self.register(sym, Binding(sym))

    def register_macrolet(self, sym, macro):
        return self.register(sym, Macrolet(sym, macro))

    def register_symbolmcrolet(self, sym, form):
        return self.register(sym, SymbolMacrolet(sym, form))

    def use_symbol(self, sym):
        scope, binding_or_macro = self.find_binding_or_macro(sym)
        if binding_or_macro is None:
            #global, non-scoped
            return BindingUse(Binding(sym))
        if isinstance(binding_or_macro, macro_types):
            return binding_or_macro
        return self.use_binding(binding_or_macro)

    def register_and_use_local(self, sym):
        return self.use_binding(self.register_local(sym))

    def unregister_binding(self, binding):
        assert len(binding.uses)==0
        assert binding is self.bindings[binding.symbol]
        del self.bindings[binding.symbol]

    #internals
    def register(self, sym, binding_or_macro):
        assert sym not in self.bindings
        self.bindings[sym] = binding_or_macro
        return binding_or_macro

    def find_binding_or_macro(self, sym):
        try:
            return self, self.bindings[sym]
        except KeyError:
            if self.parent:
                return self.parent.find_binding_or_macro(sym)
            return None, None

    def use_binding(self, binding):
        bu = BindingUse(binding)
        self.binding_uses_port.append(bu)
        return bu

    def get_locals_scope(self):
        if self.manage_locals:
            return self
        return self.parent.get_locals_scope()



@defmethod(as_string, [Scope])
def meth(sc):
    return '<Scope with %d bindings>' % (len(sc.bindings),)

@defmethod(copy_obj, [Scope])
def meth(s):
    cp = set_copy(s, Scope())
    if s.parent:
        cp.parent = copy(s.parent)
    cp.manage_locals = s.manage_locals
    for k,binding in s.bindings.iteritems():
        cp.bindings[k] = copy(binding)
    for binding_use in s.binding_uses:
        cp.binding_uses.append(copy(binding_use))
    for child in s.child_scopes:
        cp.child_scopes.append(copy(child))
    return cp

def get_binding_use_type(bu):
    if not bu.scope:
        return BND_GLOBAL
    if bu.scope.get_locals_scope() is not bu.binding.scope.get_locals_scope():
        return BND_FREE
    used_scopes = set(use.scope.get_locals_scope() for use in bu.binding.uses)
    if (len(used_scopes) > 1 or
        list(used_scopes)[0] is not bu.binding.scope.get_locals_scope()):
        return BND_CELL
    return BND_LOCAL

def test():
    from ..runtime.symbol import make_symbol
    x,y,z = map(make_symbol, 'x y z'.split())

    s0 = Scope()
    s1 = s0.create_child()
    s2 = s1.create_child(new_locals=True)
    s3 = s2.create_child()

    assert s0.parent is None
    assert s1.parent is s0
    assert s2.parent is s1
    assert s3.parent is s2

    assert s1 in s0.child_scopes
    assert s2 in s1.child_scopes
    assert s3 in s2.child_scopes

    bx0 = s0.register_local(x)
    bx1 = s1.register_local(x)
    bx3 = s3.register_local(x)

    bu0 = s0.use_symbol(x)
    bu1 = s1.use_symbol(x)
    bu2 = s2.use_symbol(x)
    bu3 = s3.use_symbol(x)

    print s2.use_symbol(y)
    print bu0
    print bu1
    print bu2
    print bu3

    print len(bx0.uses)
    print len(bx1.uses)
    print len(bx3.uses)



__name__ == '__main__' and test()
