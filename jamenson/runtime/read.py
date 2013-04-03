'''extendible sexpression reader
   converts a stream of bytes into objects
'''

from __future__ import absolute_import
from __future__ import with_statement

import sys
import re
from decimal import Decimal

from .multimethod import MultiMethod, defmethod
from .ctxsingleton import CtxSingleton
from .pattern import get_chars
from .symbol import (resolve_full_symbol_print_form,
                     make_attribute, get_sys_symbol,PackageError,
                     register_reset_notifier)
from .cons import Cons,clist,nil
from .builtins import get_builtin_symbol

__all__ = '''Stream readone read readstate
'''.split()


get_char_puller = MultiMethod('get_char_puller',
                              doc='''returns a function that pulls characters out of the
                                     the argument 1 at a time
                                     ''')

@defmethod(get_char_puller, [object])
def meth(op):
    if not callable(op):
        raise TypeError("dont't know how to read %r" % (op,))
    return op

def iter_char_seq(seq):
    for op in seq:
        yield op
    while True:
        yield ''

@defmethod(get_char_puller, [(str,buffer,list,tuple)])
def meth(seq):
    return iter(iter_char_seq(seq)).next

@defmethod(get_char_puller, [file])
def meth(fp):
    return lambda : fp.read(1)


class Stream(object):
    '''character stream for lexing
       provides a generic interface to various character streams
          ie. files, strings, buffers, etc.
       also records information about position in file
    '''

    def __init__(self, op, filename=None, start_lineno=None):
        self.op = op
        self.read_a_char = get_char_puller(op)
        self.exhausted = False
        self.buffer = []
        self.lineno = start_lineno or 1
        self.colno = 1
        self.previous_colnos = []
        if filename is None:
            try:
                filename = op.name
            except AttributeError:
                pass
        self.filename = filename

    def close(self):
        try:
            close = self.op.close
        except AttributeError:
            pass
        else:
            close()

    def pull_char(self):
        if self.exhausted:
            return ''
        elif self.buffer:
            c = self.buffer.pop()
        else:
            try:
                c = self.read_a_char()
            except StopIteration:
                self.exhausted = True
                return ''
        if c=='\n':
            self.previous_colnos.append(self.colno)
            self.colno = 1
            self.lineno += 1
        else:
            self.colno += 1
        return c

    def push_char(self, c):
        if c:
            assert len(c) == 1
            if c=='\n':
                self.colno = self.previous_colnos.pop()
                self.lineno -= 1
            else:
                self.colno += 1
            self.buffer.append(c)

    def syntax_error(self, msg='Syntax Error', char=''):
        raise SyntaxError(msg, (self.filename, self.lineno, self.colno, char))

    def unexpected_end_of_input(self):
        self.syntax_error('Unexpected end of input')

    def collect(self, pattern, pre=None):
        acc = []
        if pre:
            acc.append(pre)
        while True:
            c = self.pull_char()
            if not c:
                break
            if not re.match(pattern, c):
                self.push_char(c)
                break
            acc.append(c)
        return ''.join(acc)

    def peek_char(self):
        c = self.pull_char()
        self.push_char(c)
        return c

    def looking_at(self, pattern):
        return re.match(pattern, self.peek_char())

    def strip_whitespace(self):
        self.collect('\s')
        if self.looking_at(';'):
            self.collect('[^\n]')
            self.strip_whitespace()

    def get_last_loc(self):
        if self.colno == 1 and self.previous_colnos:
            return self.lineno-1, self.previous_colnos[-1]
        else:
            return self.lineno, max(1, self.colno-1)

default_read_table = {}
default_hash_table = {}
default_print_form_patterns = []

class ReaderState(CtxSingleton):

    def _cxs_setup_top(self):
        self.table = default_read_table.copy()
        self.hash_table = default_hash_table.copy()
        self.print_form_patterns = default_print_form_patterns[::]
        self.record_forms = False
        self.read_symbol = read_symbol
        self.stream = None
        self.handle_attribute = True
        self.handle_methods = True
        self.handle_constants = True
        self.end_symbol_chars = ''.join(get_chars(r'\s();'))
        self._cxs_setup_aux()

    def _cxs_copy(self, **kwds):
        cp = self._cxs_super._cxs_copy(**kwds)
        cp._cxs_setup_aux()
        return cp

    def _cxs_setup_aux(self):
        if self.stream is None:
            self.stream = sys.stdin
        if self.parent and self.parent.stream.op is self.stream:
            self.stream = self.parent.stream
        else:
            if not isinstance(self.stream, Stream):
                self.stream = Stream(self.stream)
        self.form_locations = {} if self.record_forms else None

def pull_char():
    return readstate.stream.pull_char()

def push_char(c):
    readstate.stream.push_char(c)

def syntax_error(*args, **kwds):
    readstate.stream.syntax_error(*args, **kwds)

def unexpected_end_of_input():
    readstate.stream.unexpected_end_of_input()

def collect(pattern, pre=None):
    return readstate.stream.collect(pattern, pre)

def peek_char():
    return readstate.stream.peek_char()

def looking_at(pattern):
    return readstate.stream.looking_at(pattern)

def strip_whitespace():
    readstate.stream.strip_whitespace()

def symbol_possible():
    return peek_char() not in readstate.end_symbol_chars

def get_last_loc():
    return readstate.stream.get_last_loc()


EOFRaise = object()
def readone(bytesource, eofp=EOFRaise,
            filename=None, start_lineno=None,
            record_forms=None, inherit_state=True):
    '''read a single item from byte source
    '''
    kwds = dict(stream=Stream(bytesource, filename=filename,
                              start_lineno=start_lineno))
    if record_forms is not None:
        kwds['record_forms'] = bool(record_forms)
    with (readstate.top if inherit_state else readstate)(**kwds):
        return read(eofp)

def read(eofp=EOFRaise):
    '''read one object out of current state
    '''
    strip_whitespace()
    c = peek_char()
    if not c:
        if eofp is EOFRaise:
            unexpected_end_of_input()
        return eofp
    reader = readstate.table.get(c, readstate.read_symbol)
    if readstate.record_forms:
        loc = get_last_loc()
    op = reader()
    if readstate.record_forms:
        readstate.form_locations[id(op)] = loc if id(op) not in readstate.form_locations else None
    return op


# # # # # #
# readers #
# # # # # #

def register_reader_aux(pattern, func, table=None):
    if table is None:
        table = default_read_table
    for c in get_chars(pattern):
        table[c] = func
    return func

def register_reader(chars, table=None):
    def wrap(func):
        return register_reader_aux(chars, func, table)
    return wrap

def register_hash_reader(chars, table=None):
    if table is None:
        table = default_hash_table
    def wrap(func):
        return register_reader_aux(chars, func, table)
    return wrap

@register_reset_notifier
def update_symbols():
    '''this function is just to be used durring testing when packages are rebuilt
       and symbols need reloaded
    '''
    yield None
    global quote_sym, attr_sym, make_attr_sym, make_meth_sym
    quote_sym = get_sys_symbol('quote')
    attr_sym = get_builtin_symbol('attr')
    make_attr_sym = get_builtin_symbol('make-attr-getter')
    make_meth_sym = get_builtin_symbol('make-call-method')
    return

list(update_symbols())


# # # # # #
# symbols #
# # # # # #

def read_symbol_ident(c):
    '''resolve a print form to a symbol, uses current package for bare symbols
       see resolve_full_symbol_print_form in symbol module
    '''
    try:
        return resolve_full_symbol_print_form(c)
    except PackageError,e:
        syntax_error(str(e))

def read_symbol():
    return read_symbol_ex(pull_char())

def read_symbol_ex(c):
    c = collect_symbol(c)
    for matcher,func in reversed(readstate.print_form_patterns):
        m = matcher(c)
        if m:
            return func(c,m)
    return read_symbol_ident(c)

def collect_symbol(c):
    r'''greedily collect the largest symbol print_form possible
        handles escapes as follows:
           o  \ is escape character
           o  end_symbol_chars is a collection of character that
              would force ending of collction
           o  when one of these is prefixed by the escape character
              the two character combination is replaced by the bare
              termination character
                 ie. \) -> )
                     \\n -> \n
           o  when the second character is not an escape requiring character
              then both character are included
                 ie. \x -> \x
                     \- -> \-
    '''
    for x in c[::-1]:
        push_char(x)
    acc = []
    escaped = False
    end_symbol_chars = readstate.end_symbol_chars
    pull_char = readstate.stream.pull_char
    while True:
        c = pull_char()
        if escaped:
            if c not in end_symbol_chars and c not in readstate.table:
                acc.append('\\')
            acc.append(c)
            escaped = False
        elif c=='\\':
            escaped = True
        elif c in end_symbol_chars:
            push_char(c)
            break
        elif not c:
            break
        else:
            acc.append(c)
    return ''.join(acc)


# # # # # # # # # # #
# symbol rewriting  #
# # # # # # # # # # #
# recognize symbol patterns by regular expression and replace
# the symbol with some other form

def register_print_form_pattern(pattern):
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    match = pattern.match
    def wrap(func):
        default_print_form_patterns.append([match,func])
        return func
    return wrap

#constant symbols
@register_print_form_pattern(r'^nil$')
def get_nil(c, match):
    if readstate.handle_constants:
        return nil
    return read_symbol_ident(c)

@register_print_form_pattern(r'^t$')
def get_t(c, match):
    if readstate.handle_constants:
        return True
    return read_symbol_ident(c)

@register_print_form_pattern(r'^None$')
def get_None(c, match):
    if readstate.handle_constants:
        return None
    return read_symbol_ident(c)

@register_print_form_pattern(r'^[^\.]+\.[^\.]+')
def handle_attr(c, match):
    '''syntax sugar for attributes.
       rewrite dotted symols as attribute access using special form attr
         a.b.c -> (attr (attr a attributes:b) attributes:c)
    '''
    if not readstate.handle_attribute or c.endswith('.'):
        return read_symbol_ident(c)
    parts = c.split('.')
    acc = read_symbol_ident(parts.pop(0))
    for part in parts:
        acc = clist(attr_sym, acc, make_attribute(part))
    return acc

def make_dotted_form(sym, c):
    '''pythonesque syntax sugar
    '''
    return clist(sym, *map(make_attribute, c.split('.')))

@register_print_form_pattern(r'^\.\.')
def handle_getattr(c, match):
    '''use special form make-attr-getter
         ..a.b.c -> (make-attr-getter attributes:a attributes:b attributes:c)
       ie.
       (..a.b.c (getit)) is equivalent to
         (attr (attr (attr (getit) a) b) c)
       also
         (map .inner.first seq) instead of
           (map (lambda (op) op.inner.first) seq)
    '''
    if not (readstate.handle_methods and  readstate.handle_attribute):
        return read_symbol_ident(c)
    return make_dotted_form(make_attr_sym, c[2:])

@register_print_form_pattern(r'^\.[^.]')
def handle_method(c, match):
    ''' use special form make-call-method to for method syntax sugar
           .a.b.c -> (make-call-method attributes:a attributes:b attributes:c)
        useful as
          (.a.b.c (get-op) "stuff") is equivalent to
             ((attr (attr (attr (get-op) attribute:a) attribute:b) attribute:c) "stuff")
        and
          (map .get_stuff seq) is equivalent to
            (map (lambda (op) (op.get_stuff)) seq)
    '''
    if not readstate.handle_methods:
        return read_symbol_ident(c)
    return make_dotted_form(make_meth_sym, c[1:])

#as currently defined, simpler patterns are first
#more efficient to try them first when they succeed
default_print_form_patterns.reverse()


# # # # # #
# numbers #
# # # # # #

def read_digits(pre=None):
    if pre:
        for c in pre[::-1]:
            push_char(c)
        pre = None
    digits = ''
    if looking_at('-'):
        digits += pull_char()
    digits += collect('\d')
    if looking_at('\.'):
        pull_char()
        digits = '%s.%s' % (digits, collect('\d'))
        return digits, float(digits)
    try:
        return digits, int(digits)
    except ValueError:
        print 'XXXXX', repr(digits), readstate.stream.lineno, readstate.stream.colno
        raise

@register_reader(r'+-\.\d')
def read_number():
    c = pull_char()
    if c=='.' and looking_at(r'\.'):
        return read_symbol_ex(c)
    neg = c=='-'
    dropped = ''
    decimal = False
    if c in '-+':
        if not looking_at('\d'):
            return read_symbol_ex(c)
        dropped += c
        c = pull_char()
    if c=='0' and looking_at(r'[xob\d]'):
        dropped += c
        if looking_at('[xX]'):
            dropped += pull_char()
            radix = 16
            pattern = r'[\dA-Fa-f]'
        elif looking_at('[bB]'):
            dropped += pull_char()
            radix = 2
            pattern = r'[01]'
        elif looking_at('dD'):
            dropped += pull_char()
            radix = 10
            pattern = '\d'
        else:
            if looking_at('[oO]'):
                dropped += pull_char()
            radix = 8
            pattern = '[0-7]'
        chars = collect(pattern)
        if looking_at('d'):
            decimal = True
            pull_char()
        if symbol_possible():
            return read_symbol_ex(dropped + chars + ('d' if decimal else ''))
        if not chars:
            return 0
        i = int(chars, radix)
        if decimal:
            i = Decimal(str(i))
        if neg:
            i*=-1
        return i
    if c=='.' and not looking_at('\d'):
        return read_symbol_ex(c)
    digits,n = read_digits(c)
    dropped += digits
    if neg:
        n *= -1
    if looking_at('[eE]'):
        dropped += pull_char()
        digits,exp = read_digits()
        dropped += digits
        n *= 10 ** exp
    if looking_at('d'):
        decimal = True
        pull_char()
    if symbol_possible():
        return read_symbol_ex(dropped + ('d' if decimal else ''))
    if decimal:
        n = Decimal(dropped)
    return n


# # # # #
# cons  #
# # # # #

@register_reader('(')
def read_cons():
    pull_char()
    head = acc = nil
    while True:
        strip_whitespace()
        if looking_at(r'\)'):
            pull_char()
            return head
        if looking_at(r'\.'):
            pull_char()
            if symbol_possible():
                push_char('.')
            else:
                acc.cdr = read()
                strip_whitespace()
                if not looking_at(r'\)'):
                    syntax_error()
                pull_char()
                return head
        cell = Cons(read(), nil)
        if acc is nil:
            head = cell
        else:
            acc.cdr = cell
        acc = cell

# # # # # #
# string  #
# # # # # #

@register_reader('"')
def read_string():
    pull_char()
    acc = []
    escaped = False
    while True:
        c = pull_char()
        if not c:
            unexpected_end_of_input()
        if escaped:
            escaped = False
            if c=='n':
                c = '\n'
            elif c=='t':
                c = '\t'
            elif c=='\\' or c=='"':
                pass
            elif c=='x':
                a = pull_char()
                b = pull_char()
                if not b:
                    unexpected_end_of_input()
                try:
                    d = int(a+b, 16)
                    if not (0<=d<=0xff):
                        raise ValueError
                except ValueError:
                    syntax_error('invalid character escape \\x%s%s' % (a,b))
                c = chr(d)
            else:
                c = '\\' + c
        elif c=='\\':
            escaped = True
            continue
        elif c=='"':
            break
        acc.append(c)
    return ''.join(acc)


# # # # #
# quote #
# # # # #

@register_reader("'")
def read_quote():
    pull_char()
    return clist(quote_sym, read())

# # # # #
# hash  #
# # # # #

@register_reader('#')
def read_hash():
    pull_char()
    c = peek_char()
    if not c:
        unexpected_end_of_input()
    try:
        reader = readstate.hash_table[c]
    except KeyError:
        syntax_error("no read macro for hash escape %r" % (c,))
    return reader()

readstate = ReaderState()
