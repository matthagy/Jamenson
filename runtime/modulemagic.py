'''utilities for working with modules
'''

import sys

def impmod(name):
    '''import module by name
    '''
    return __import__(name, fromlist=name.rsplit('.',1)[-1:] if '.' in name else [])

def delmod(name):
    '''delete module by name
    '''
    try:
        parent,attr = get_mod_parent_and_attr(name)
        delattr(parent,name)
    except AttributeError:
        pass
    try:
        del sys.modules[name]
    except KeyError:
        pass

def setmod(name, op):
    '''assign object to module name
    '''
    parent,attr = get_mod_parent_and_attr(name)
    setattr(parent, attr, op)
    sys.modules[name] = op
    op.__name__ = name

def get_mod_parent_and_attr(name):
    '''By name, get module parent and attribute name of target module in this parent
    '''
    parts = name.split('.')
    attr = parts.pop()
    thing = sys.modules[parts.pop(0)]
    for part in parts:
        thing = getattr(thing, part)
    return thing, attr

