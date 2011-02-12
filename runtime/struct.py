
from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.runtime.struct
    exit()

import sys
import new

from .atypes import anytype, as_optimized_type, typep
no_default = object()

def defstruct(name, *decs, **kwds):
    sys._getframe(1).f_locals[name] = struct = make_struct(name, *decs, **kwds)
    return struct

class BaseStruct(object):

    _properties = []

    def __init__(self, *args, **kwds):
        setkeys = set()
        for arg,(n,d,tp) in zip(args, self._properties):
            if n in kwds:
                raise ValueError("mutliple specifications for %s" % (n,))
            setattr(self, n, arg)
            setkeys.add(n)
        for n,v in kwds.iteritems():
            setkeys.add(n)
            setattr(self, n, v)
        for n,d,tp in self._properties:
            if d is no_default:
                if n not in setkeys:
                    raise ValueError('must specify attribute %r for %s' %
                                     (n, classname(self)))

    def __repr__(self):
        return '%s(%s)' % (classname(self),
                           ', '.join('%s=%r' % (name, getattr(self,name))
                                     for name,default,tp in self._properties))

    def __str__(self):
        return repr(self)

def make_struct(clsname, *decs, **kwds):
    if kwds:
        base_class = kwds.pop('base')
        assert not kwds
    else:
        base_class = BaseStruct
    properties = []
    for dec in decs:
        if isinstance(dec, str):
            name = dec
            tp = anytype
            default = None
        else:
            dec = list(dec)
            if len(dec)==2:
                name, default = dec
            else:
                name, default, tp = dec
            tp = as_optimized_type(tp)
        assert not name.startswith('_')
        properties.append([name, default, tp])
    dct = {'_properties': properties}
    for name, default, tp in properties:
        dct[name] = make_property(name, default, tp)
    return new.classobj(clsname, (base_class,), dct)

def make_property(name, default, tp):
    inner_name = '_'+name
    def get(self):
        try:
            return getattr(self, inner_name)
        except AttributeError:
            if default is no_default:
                raise
            return default
    def set_(self, value):
        if not typep(value, tp):
            raise TypeError("can't assign %r to %s.%s; dosn't conform to type %s" %
                            (value, classname(self), name, tp))
        setattr(self, inner_name, value)
    def del_(self):
        set_(self, default)
    return property(get, set_, del_)

def classname(op):
    return op.__class__.__name__
