
'''objects used by runtime
'''

from itertools import count
import string

class symbol(object):

    #instance cache for `is based comparisions and `id based hashing
    _cache = {}

    __slots__ = ['printForm']

    @classmethod
    def raw(cls, printForm):
        self = object.__new__(cls)
        self.printForm = printForm
        return self

    def __new__(cls, printForm):
        try:
            return cls._cache[printForm]
        except KeyError:
            self = cls._cache[printForm] = cls.raw(printForm)
            return self

    def __repr__(self):
        return 'symbol(%s)' % (self.printForm)

    def __str__(self):
        return bprint(self)

    def __reduce__(self):
        if gensymbolp(self):
            return (gensym, (self.printForm[2:],))
        else:
            return (symbol, (self.printForm,))


def reset_gensym_counter(start=0):
    global gensym_counter
    gensym_counter = iter(count(start)).next

reset_gensym_counter()

def gensym(base='gensym'):
    return symbol.raw('#:%s%d' % (base,gensym_counter()))

def gensymbolp(op):
    return op.printForm not in symbol._cache


class cons(object):

    __slots__ = 'car cdr'.split()

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __iter__(self):
        op = self
        while op is not nil:
            if not isinstance(op, cons):
                raise TypeError("iterating over non-cons cdr")
            yield op.car
            op = op.cdr

    def __nonzero__(self):
        return self is not nil

    def __repr__(self):
        return str(self)
        #if self is nil:
        #    return 'nil'
        #return 'cons(%r, %r)' % (self.car, self.cdr)

    def __str__(self):
        return bprint(self)

    def __reduce__(self):
        if self is nil:
            return (load_nil, ())
        else:
            return (cons, (self.car, self.cdr))

    def __eq__(self, other):
        if not isinstance(other, cons):
            return NotImplemented
        return self is other or (self.car == other.car and
                                 self.cdr == other.cdr)

nil = cons(None, None)
nil.car = nil
nil.cdr = nil

def load_nil():
    return nil

def clist(*seq):
    head = acc = nil
    for op in seq:
        cell = cons(op, nil)
        if acc is nil:
            head = cell
        else:
            acc.cdr = cell
        acc = cell
    return head

def bprint(op):
    acc = []
    bprint_collect_parts(acc.append, set(), op)
    return ''.join(acc)

noQuoteChars = set(string.ascii_letters +
                   string.digits +
                   string.punctuation + ' ') - set('"')
escapeChars = {
    '\n': '\\n',
    '\t': '\\t',
    '"': '\\"'}

qsymbol = symbol('%quote')
def bprint_collect_parts(emit, memo, op):
    if isinstance(op, symbol):
        emit(op.printForm)
    elif op is nil:
        emit('nil')
    elif isinstance(op, cons):
        if op.car is qsymbol:
            assert op.cdr.cdr is nil, 'bad quote %r' % (op.cdr,)
            emit("'")
            bprint_collect_parts(emit, memo, op.cdr.car)
            return
        if id(op) in memo:
            emit('#<circular cons>')
            return
        memo.add(id(op))
        emit('(')
        first = True
        while op is not nil:
            if first:
                first = False
            else:
                emit(' ')
            bprint_collect_parts(emit, memo, op.car)
            if isinstance(op.cdr, cons):
                op = op.cdr
            else:
                emit(' . ')
                bprint_collect_parts(emit, memo, op.cdr)
                break
        emit(')')
    elif isinstance(op, (int,long,float)):
        emit(str(op))
    elif op is None or op is False or op is True:
        emit(str(op).lower())
    elif isinstance(op, str):
        emit('"')
        for c in op:
            if c in noQuoteChars:
                emit(c)
            elif c in escapeChars:
                emit(escapeChars[c])
            else:
                emit('\\x%x' % ord(c))
        emit('"')
    else:
        emit('#<')
        emit(repr(op))
        emit('>')


class MacroFunction(object):

    __slots__ = ['func', 'robust']

    def __init__(self, func, robust=False):
        self.func = func
        self.robust = robust

    def __call__(self, *args, **kwds):
        raise RuntimeError("cannot directly call macro %s" % self.func.__name__)

    def macroExpand(self, translator, *args, **kwds):
        return self.func(translator, *args, **kwds)

    def __getstate__(self):
        return self.func, self.robust

    def __setstate__(self, state):
        self.func, self.robust = state

import types
class obj(object):

    def __init__(self, **kwds):
        vars(self).update(kwds)

    def __repr__(self):
        return '(%s %s)' % (self.__class__.__name__,
                           ' '.join(":%s %r" % t
                                     for t in vars(self).iteritems()))

