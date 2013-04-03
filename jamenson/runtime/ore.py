'''Object Regular Expressions
   Simple regular expression matching of Python objects using
   an NFA engine
'''

from __future__ import absolute_import
from __future__ import with_statement
from __future__ import division

if __name__ == '__main__':
    import jamenson.runtime.ore
    exit()

import new
from collections import deque
from .multimethod import MultiMethod, defmethod
from .atypes import anytype, typep, as_optimized_type
from .func import identity
from .as_string import StringingMixin, as_string
from .symbol import (resolve_and_export_print_form, get_package, use_package,
                     unuse_package, sys_package, all_used_packages)
from .cons import Cons, clist

ore_package = get_package('ore')


class AbortTransaction(Exception):
    pass


class MatchState(object):

    def __init__(self):
        self.states = []
        self.values = {}

    def save(self, name, value):
        self.values[name] = value

    nodefault = object()
    def load(self, name, default=nodefault):
        try:
            return self.values[name]
        except KeyError:
            if default is not self.nodefault:
                return default
            raise ValueError("no such value %r" % (name,))

    def loads(self, *names, **kwds):
        default = kwds.pop('default', self.nodefault)
        assert not kwds
        return [self.load(name, default) for name in names]

    def begin(self):
        state = vars(self).copy()
        state['values'] = state['values'].copy()
        self.states.append(state)

    def rollback(self):
        state = self.states.pop()
        vars(self).clear()
        vars(self).update(state)

    def commit(self):
        self.states.pop()

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_tp, exc_value, exc_tb):
        exc_tb = None
        if exc_tp is None:
            self.commit()
            return None
        else:
            self.rollback()
            return isinstance(exc_value, AbortTransaction)

class SexpBase(StringingMixin):

    def as_sexp(self):
        return resolve_and_export_print_form(self.__class__.__name__.lower(),
                                             ore_package)

@defmethod(as_string, [SexpBase])
def meth(mb):
    used = ore_package in all_used_packages(sys_package)
    use_package(ore_package, sys_package)
    try:
        return str(mb.as_sexp())
    finally:
        if not used:
            unuse_package(ore_package, sys_package)

class MatchBase(SexpBase):

    def match(self, op):
        state = MatchState()
        if self.xmatch(state, op):
            return state
        return None

    def xmatch(self, state, op):
        raise RuntimeError("match not implemented for %s" % (self.__class__.__name__,))

as_ore = MultiMethod('as_ore',
                     doc='''
                     ''')

@defmethod(as_ore, [MatchBase])
def meth(op):
    return op

class Succeed(MatchBase):

    @staticmethod
    def xmatch(state, op):
        return True

succeed = Succeed()

class Fail(MatchBase):

    @staticmethod
    def xmatch(state, op):
        return False

fail = Fail()

class CompoundBase(MatchBase):

    def __init__(self, *children):
        self.children = map(as_ore, children)

    def as_sexp(self):
        return clist(super(CompoundBase, self).as_sexp(),
                     *[child.as_sexp() for child in self.children])


class Or(CompoundBase):

    def xmatch(self, state, op):
        for choice in self.children:
            with state:
                if not choice.xmatch(state, op):
                    raise AbortTransaction
                return True
        return False

class And(CompoundBase):

    def xmatch(self, state, op):
        with state:
            for child in self.children:
                if not child.xmatch(state, op):
                    raise AbortTransaction
            return True
        return not self.children

class Seq(CompoundBase):

    def xmatch(self, state, op):
        try:
            itr = iter(op)
        except TypeError:
            return False
        with state:
            for i,(child,iop) in enumerate(zip(self.children, itr)):
                if not child.xmatch(state, iop):
                    raise AbortTransaction
            if self.children and i+1 != len(self.children):
                raise AbortTransaction
            return True
        return False

class Save(MatchBase):

    def __init__(self, name, inner=succeed, key=identity):
        self.name = name
        self.inner = as_ore(inner)
        self.key = key

    def xmatch(self, state, op):
        if not self.inner.xmatch(state, op):
            return False
        state.save(self.name, self.key(op))
        return True

    def as_sexp(self):
        acc = [super(Save, self).as_sexp(),
               self.name]
        if not isinstance(self.inner, Succeed):
            acc.append(self.inner.as_sexp())
        return clist(*acc)


class ProviderBase(SexpBase):

    def provide(self, state):
        raise RuntimeError("provide not implemented for %s" % (self.__class__.__name__,))

as_provider = MultiMethod('as_provider',
                          doc='''
                          ''')

@defmethod(as_provider, [ProviderBase])
def meth(op):
    return op

class Constant(ProviderBase):

    def __init__(self, value):
        self.value = value

    def provide(self, state):
        return self.value

    def as_sexp(self):
        return clist(super(Constant, self).as_sexp(),
                     repr(self.value))

@defmethod(as_provider, [anytype])
def meth(op):
    return Constant(op)

class Load(ProviderBase):

    def __init__(self, name, default=MatchState.nodefault):
        self.name = name
        self.default = default

    def provide(self, state):
        return state.load(self.name, self.default)

    def as_sexp(self):
        return clist(super(Load, self).as_sexp(),
                     self.name)

class UnaryOp(MatchBase):

    def xmatch(self, state, op):
        return self.check(op)

class LogicTrue(UnaryOp):

    @staticmethod
    def check(op):
        return op

class LogicFalse(UnaryOp):

    @staticmethod
    def check(op):
        return not op

class Predicate(UnaryOp):

    def __init__(self, func):
        self.check = func

class Type(UnaryOp):

    def __init__(self, tp):
        self.tp = as_optimized_type(tp)

    def check(self, op):
        return typep(op, self.tp)

    def as_sexp(self):
        return clist(super(Type, self).as_sexp(),
                     repr(self.tp))


class BinaryOp(MatchBase):

    def __init__(self, provider):
        self.provider = as_provider(provider)

    def xmatch(self, state, op):
        return self.check(op, self.provider.provide(state))

    def as_sexp(self):
        return clist(super(BinaryOp, self).as_sexp(),
                     self.provider.as_sexp())

def defbinop(name, func):
    globals()[name] = new.classobj(name, (BinaryOp,), {'check': staticmethod(func)})

defbinop('Eq', lambda a,b: a==b)
defbinop('Ne', lambda a,b: a!=b)
defbinop('Gt', lambda a,b: a>b)
defbinop('Ge', lambda a,b: a>=b)
defbinop('Lt', lambda a,b: a<b)
defbinop('Le', lambda a,b: a<=b)
defbinop('Is', lambda a,b: a is b)

def set_range(m, i_start, n):
    m.start = i_start
    m.end = i_start + n
    m.length = n
    m.range = m.start, m.end
    return m

def match(matcher, op):
    return as_ore(matcher).match(op)

def search(matcher, seq):
    matcher = as_ore(matcher)
    if not isinstance(matcher, Seq):
        matcher = Seq(matcher)
    window = deque()
    n = len(matcher.children)
    for i_start,el in enumerate(seq):
        window.append(el)
        lw = len(window)
        if lw>=n:
            if lw>n:
                window.popleft()
            m = matcher.match(window)
            if m is not None:
                return set_range(m, i_start, n)
    return None

def replace_one_of(matchers, func, seq):
    matchers = map(as_ore,matchers)
    acc = []
    window = deque()
    n = max(len(matcher.children) for matcher in matchers)
    for i_start,el in enumerate(seq):
        window.append(el)
        lw = len(window)
        if lw>=n:
            if lw>n:
                yield window.popleft()
            for matcher in matchers:
                m = matcher.match(window)
                if m is not None:
                    for el in func(set_range(m, i_start, len(matcher.children))):
                        yield el
                    for i in xrange(m.length):
                        window.popleft()
                    break
    for op in window:
        yield op

def replace(matcher, func, seq):
    matcher = as_ore(matcher)
    iterable = True
    if not isinstance(matcher, Seq):
        matcher = Seq(matcher)
        iterable = False
    if not callable(func):
        value = func
        if not iterable:
            value = [value]
        func = lambda match: value
    return replace_one_of([matcher], func, seq)
