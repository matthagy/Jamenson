'''symbol table
'''

from __future__ import absolute_import

import itertools

from ..runtime.ctxsingleton import CtxSingleton
from ..runtime.multimethod import defmethod
from ..runtime.copy import copy_obj
from ..runtime.as_string import as_string, StringingMixin


class NameTranslation(StringingMixin):
    '''jamenson allows for lexically scoped bindings with identical symbols
       that correspond to different local bindings.
       python requires all local bindings to a have a unique name.
       we therefore have to perform a translation of seperate bindings with
       the same name in the same lexical enviroment.
       this is a place holder to defer that translation until assembling
    '''

    #uniq ids used in debugging scope
    next_uid = iter(itertools.count()).next

    __slots__ = ['uid','basename', 'translation']

    def __init__(self, basename, translation=None):
        self.uid = self.next_uid()
        self.basename = basename
        self.translation = translation

@defmethod(as_string, [NameTranslation])
def meth(op):
    return '%s(0x%x, %r, %r)' % (op.__class__.__name__,
                                 op.uid, op.basename,
                                 op.translation)

@defmethod(copy_obj, [NameTranslation])
def meth(op):
    return op.__class__(op.basename, op.translation)


[BND_GLOBAL,BND_LOC,BND_CELL,BND_FREE,
 BND_MACRO,BND_SYMBOLMACRO] = BND_TYPES = range(6)

class Binding(StringingMixin):
    '''represent scemantics of a symbol
    '''

    __slots__ = ['symbol', 'type', 'value']

    def __init__(self, symbol, type, value):
        assert type in BND_TYPES
        self.symbol = symbol
        self.type = type
        self.value = value

    def is_global(self):
        return self.type == BND_GLOBAL

    def is_local(self):
        return self.type == BND_LOC

    def is_cell(self):
        return self.type == BND_CELL

    def is_free(self):
        return self.type == BND_FREE

    def is_macrolet(self):
        return self.type == BND_MACRO

    def is_symbolmacrolet(self):
        return self.type == BND_SYMBOLMACRO

    def is_var_binding(self):
        return self.type in [BND_GLOBAL, BND_LOC,
                             BND_CELL, BND_FREE]

    def is_macro_binding(self):
        return self.type in [BND_MACRO, BND_SYMBOLMACRO]

    def get_name(self):
        if not self.is_var_binding():
            raise RuntimeError("attempt to access name of non variable binding %s" % (self,))
        elif not self.value.translation:
            raise RuntimeError("%s name not yet translated" % (self,))
        return self.value.translation


@defmethod(as_string, [Binding])
def meth(op):
    return 'Binding(%s, %s)' % (
        {BND_GLOBAL:      'BND_GLOBAL',
         BND_LOC:         'BND_LOC',
         BND_CELL:        'BND_CELL',
         BND_FREE:        'BND_FREE',
         BND_MACRO:       'BND_MACRO',
         BND_SYMBOLMACRO: 'BND_SYMBOLMACRO'}[op.type],
        as_string(op.value))

@defmethod(copy_obj, [Binding])
def meth(op):
    return op.__class__(op.type, copy(op.value))


class Scope(object):
    '''builds nested scoping

       member manage_locals is set to True when this is the top
       scope of a function (or top scope of a module) and there
       can create closures
    '''

    def __init__(self, parent=None, manage_locals=None):
        if manage_locals is None:
            manage_locals = parent is None
        assert parent or manage_locals, 'no local managment for scope'
        self.parent = parent
        self.manage_locals = manage_locals
        self.bindings = {}
        if self.manage_locals:
            self.name_translations = {}

    #api
    def create_child(self, new_locals=False):
        return Scope(parent=self, manage_locals=new_locals)

    def register_local(self, sym):
        return self.register(sym, Binding(sym, BND_LOC,
                                          self.get_locals_scope().
                                          get_name_translation(self, sym.print_form)))

    def register_macrolet(self, sym, macro):
        return self.register(sym, Binding(sym, BND_MACRO, macro))

    def register_symbolmacrolet(self, sym, form):
        return self.register(sym, Binding(sym, BND_SYMBOLMACRO, form))

    def use_symbol(self, sym):
        scope,binding = self.find_binding(sym)
        #no translation for globals
        if binding is None:
            return Binding(sym, BND_GLOBAL, None)
        assert isinstance(binding, Binding)
        #no scoping for macro (translation) bindings
        if binding.is_macro_binding():
            return binding
        #check for lexical closures
        if scope.get_locals_scope() is not self.get_locals_scope():
            #convert local bindings to cell bindings
            if binding.is_local():
                binding.type = BND_CELL
            #free variable in parent scope
            elif binding.is_free():
                pass
            #cell variable in parent scope
            else:
                assert binding.is_cell()
            binding = self.get_locals_scope().register_free(sym)
            assert binding
        return binding

    #internals
    def register(self, sym, binding):
        assert sym not in self.bindings
        self.bindings[sym] = binding
        return binding

    def find_binding(self, sym):
        try:
            return self, self.bindings[sym]
        except KeyError:
            if self.parent:
                return self.parent.find_binding(sym)
            else:
                return None, None

    def get_locals_scope(self):
        if self.manage_locals:
            return self
        return self.parent.get_locals_scope()

    def get_name_translation(self, scope, name):
        try:
            return self.name_translations[scope,name]
        except KeyError:
            nt = self.name_translations[scope,name] = NameTranslation(name)
            return nt

    def register_free(self, sym):
        #need to all register as free var in all function scopes upto
        #scope in which cell is declared
        try:
            binding = self.bindings[sym]
        except KeyError:
            assert self.parent
            parent = self.parent.register_free(sym)
            if self.manage_locals:
                return self.register(sym, Binding(sym, BND_FREE, parent.value))
            return parent
        else:
            if binding.is_free():
                #already declared free in parent scopes, done
                pass
            elif not binding.is_cell():
                raise RuntimeError("inconsistent cell/free bindings")
            return binding


