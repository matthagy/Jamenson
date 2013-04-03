
from __future__ import with_statement

import new


class CtxSingletonState(object):

    def __init__(self, ctx):
        self._cxs_ctx = ctx
        self._cxs_super = super(self.__class__.mro()[0], self)

    @property
    def parent(self):
        return self._cxs_ctx._cxs_get_parent(self)

    @classmethod
    def _cxs_create_top(cls, ctx):
        self = cls(ctx)
        self._cxs_setup_top()
        return self

    def _cxs_setup_top(self):
        pass

    def __enter__(self):
        return self._cxs_ctx._cxs_enter_instance(self)

    def __exit__(self, *exc_info):
        return self._cxs_ctx._cxs_exit_instance(self, exc_info)

    def __call__(self, *args, **kwds):
        return self._cxs_copy(*args, **kwds)

    def _cxs_copy(self, **kwds):
        cp = self.__class__(self._cxs_ctx)
        for n,v in vars(self).iteritems():
            if not (n.startswith('_cxs_') or (hasattr(self.__class__, n) and
                                              getattr(self.__class__,n) == v)):
                setattr(cp, n, v)
        for n,v in kwds.iteritems():
            setattr(cp, n, v)
        return cp

    def _cxs_delete(self):
        vars(self).clear()


class CtxSingletonBase(object):

    def __init__(self, singleton_state_cls):
        self._cxs_singleton_cls = singleton_state_cls
        self._cxs_stack = []
        #have to create _cxs_stack before calling _cxs_create_top
        self._cxs_stack.append(self._cxs_singleton_cls._cxs_create_top(self))

    @property
    def top(self):
        return self._cxs_stack[-1]

    @property
    def bottom(self):
        return self._cxs_stack[0]

    @property
    def depth(self):
        return len(self._cxs_stack)

    def _cxs_get_parent(self, state):
        try:
            i = self._cxs_stack.index(state)
        except ValueError:
            return None
        return None if i==0 else self._cxs_stack[i-1]

    def _cxs_get_child(self, state):
        i = self._cxs_stack.index(state) + 1
        None if i==len(self._cxs_stack) else self._cxs_stack[i]

    def __getitem__(self, i):
        return self._cxs_stack[i]

    #map attributes to top state
    def __getattr__(self, name):
        assert not name.startswith('_cxs_')
        assert not name.startswith('__')
        return getattr(self.top, name)

    def __setattr__(self, name, value):
        if name.startswith('_cxs_'):
            vars(self)[name] = value
        else:
            setattr(self.top, name, value)

    #map context managment to default state when called on singleton
    #use top attribute to map to top state
    def __enter__(self):
        return self._cxs_enter_cls()

    def __exit__(self, *exc_info):
        return self._cxs_exit_cls()

    #map copying to default state when called on singleton
    #use top attribute to copy default
    def __call__(self, *args, **kwds):
        return self._cxs_singleton_cls._cxs_create_top(self)(*args, **kwds)

    #context managment
    def _cxs_enter_instance(self, instance):
        assert instance._cxs_ctx is self
        top = instance._cxs_copy()
        assert top._cxs_ctx is self
        self._cxs_stack.append(top)
        return top

    def _cxs_enter_cls(self):
        self._cxs_stack.append(self._cxs_singleton_cls._cxs_create_top(self))

    def _cxs_exit_instance(self, instance, exc_info):
        return self._cxs_exit_cls(exc_info)

    def _cxs_exit_cls(self, exc_info):
        self._cxs_stack.pop()._cxs_delete()
        return list(exc_info).count(None)==3




class CtxSingletonMetaClass(type):

    def __new__(cls, name, bases, dct):
        singleton_dict = {}
        state_dict = {}
        if dct['__module__'] == __name__ and name == 'CtxSingleton':
            singleton_dict.update(dct)
        else:
            state_dict.update(dct)
        state_cls = new.classobj(name + '-cxs-state', (CtxSingletonState,), state_dict)
        singleton_dict['_cxs_singleton_cls'] = state_cls
        return type.__new__(cls, name + '-singleton', bases, singleton_dict)


class CtxSingleton(CtxSingletonBase):
    '''use metaclass to use class syntax as a declarative dsl
       to define SingletonState
    '''

    __metaclass__ = CtxSingletonMetaClass

    def __init__(self):
        super(CtxSingleton, self).__init__(self._cxs_singleton_cls)


# class ReaderState(CtxSingleton):

#     def __init__(self):
#         self.table = {}
#         self.package = None

#     def _cxs_copy(self, inherit_package=False, extensions=None):
#         cp = self._cxs_super._cxs_copy()
#         cp.table = self.table.copy()
#         return cp

# state = ReaderState()

# #access read table
# state.table

# #current package
# state.package

# #push new default state with extensions=stuff
# with state(extensions=stuff):
#     pass

# #push state inherted from top state with extensions=stuff
# with state.top(extensions=stuff):
#     pass

# #inhert from second
# with state[-1](extensions=stuff):
#     pass

