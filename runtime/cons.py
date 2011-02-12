
from __future__ import with_statement
from __future__ import absolute_import

import cPickle as pickle
from functools import partial

from .multimethod import defmethod
from .copy import copy, copy_obj, set_copy
from .symbol import get_sys_symbol, symbolp, internedp, attributep, register_reset_notifier
from .as_string import as_string
from .atypes import Predicate
from .purity import register_pure
from . import state


__all__ = '''Cons nil clist
'''.split()


class Cons(object):
    '''Cons cell (predominantly) for forming link list
    '''

    __slots__ = 'car cdr'.split()

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __iter__(self):
        op = self
        while op is not nil:
            if not isinstance(op, Cons):
                raise TypeError("iterating over non-Cons cdr")
            yield op.car
            op = op.cdr

    def __nonzero__(self):
        return self is not nil

    def __repr__(self):
        if self is nil:
            return 'nil'
        return '%s(%r, %r)' % (self.__class__.__name__,
                              self.car, self.cdr)

    __str__ = lambda self: as_string(self)

    def __reduce__(self):
        if self is nil:
            return (load_nil, ())
        else:
            return (Cons, (self.car, self.cdr))

    def __eq__(self, other):
        if not isinstance(other, Cons):
            return NotImplemented
        if self is nil or other is nil:
            return self is other
        return self is other or (self.car == other.car and
                                 self.cdr == other.cdr)

register_pure(Cons)

nil = Cons(None, None)
nil.car = nil
nil.cdr = nil

def load_nil():
    return nil

@register_pure
def clist(*seq):
    '''create a forward list from sequence
    '''
    head = acc = nil
    for op in seq:
        cell = Cons(op, nil)
        if acc is nil:
            head = cell
        else:
            acc.cdr = cell
        acc = cell
    return head


@defmethod(as_string, [Cons])
def meth(c):
    acc = []
    format_cons(c, acc.append, set())
    return ''.join(acc)

new_cons = partial(Cons.__new__, Cons)
@defmethod(copy_obj, [Cons])
def meth(c):
    if c is nil:
        return c
    cp = new_cons()
    set_copy(c, cp)
    cp.car = copy(c.car)
    cp.cdr = copy(c.cdr)
    return cp

special_form_emitters = {}

def format_cons(c, emit, memo):
    if c is nil:
        emit('nil')
    elif id(c) in memo:
        emit('#<circular Cons>')
    else:
        memo.add(id(c))
        if state.special_form_emitters_enabled and symbolp(c.car) and c.car in state.special_form_emitters:
            state.special_form_emitters[c.car](c, emit, memo)
        else:
            format_cons_raw(c, emit, memo)
        memo.remove(id(c))

def format_cons_raw(c, emit, memo):
    emit('(')
    while c is not nil:
        emit_op(c.car, emit, memo)
        c = c.cdr
        if c is not nil:
            emit(' ')
        if not isinstance(c, Cons):
            emit('. ')
            emit_op(c, emit, memo)
            break
    emit(')')

def emit_op(op, emit, memo):
    if isinstance(op, Cons):
        format_cons(op, emit, memo)
    else:
        emit(as_string(op))

def register_special_form_emiter(symbol, export=True):
    if isinstance(symbol, str):
        symbol = get_sys_symbol(symbol, export)
    if not internedp(symbol):
        raise RuntimeError("bad formatting symbol %s; must be interned" %
                           (symbol,))
    sfe = state.special_form_emitters
    def wrapper(func):
        sfe[symbol] = func
        return func
    return wrapper

@register_special_form_emiter('quote')
def emit_quote(c, emit, memo):
    emit("'")
    emit_op(c.cdr.car, emit, memo)

@register_reset_notifier
def update_symbols():
    '''only to be used durring testing when packages are
       reset and symbols need reloaded
    '''
    saved = []
    for sym,func in state.special_form_emitters.iteritems():
        assert internedp(sym)
        saved.append([pickle.dumps(sym), func])
    state.special_form_emitters.clear()
    yield None
    state.special_form_emitters.clear()
    for symbytes,func in saved:
        sym = pickle.loads(symbytes)
        assert internedp(sym)
        state.special_form_emitters[sym] = func
    return

@register_pure
def well_form_list_p(op):
    while op is not nil:
        if not isinstance(op, Cons):
            return False
        op = op.cdr
    return True

well_form_list_t = Predicate(well_form_list_p)

@register_pure
def listlen(op):
    l = 0
    while op is not nil:
        l += 1
        op = op.cdr
    return l
