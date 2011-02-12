
import string

from jamenson.runtime.multimethod import MultiMethod, defmethod
from jamenson.runtime import state
from jamenson.runtime.atypes import as_string, anytype

__all__ = ['as_string']


#by default use str
@defmethod(as_string, 'anytype')
def meth(op):
    return state.default_as_string(op)


class StringingMixin(object):

    def __str__(self):
        return as_string(self)
    def __repr__(self):
        return as_string(self)

def translation_table():
    tbl = {'\n':'\\n',
           '\t':'\\t',
           '\r':'\\r',
           '"': '\\"'}
    nos = set(' ' + string.digits + string.letters + string.punctuation)
    for c in map(chr, xrange(256)):
        if c not in tbl:
            if c in nos:
                t = c
            else:
                t = r'\x%02x' % ord(c)
            tbl[c] = t
    return tbl

translation_table = translation_table()

@defmethod(as_string, 'str')
def meth(s, #cached globals
         translation_table=translation_table):
    return '"%s"' % ''.join((translation_table[c] for c in s)
                            if len(s)>30 else
                            [translation_table[c] for c in s])


#print as_string(range(3))
