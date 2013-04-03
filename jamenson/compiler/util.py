
from __future__ import absolute_import

from types import GeneratorType
from time import time

from ..runtime.util import strtime

list_and_generator = list, GeneratorType
def flatten_lists_and_generators(op):
    if not isinstance(op, list_and_generator):
        yield op
    else:
        for el in op:
            for sel in flatten_lists_and_generators(el):
                yield sel

def collect_list(func):
    def wrap(*args, **kwds):
        return list(func(*args, **kwds))
    return wrap


class timing(object):

    def __init__(self, name=None):
        self.name = name
        self.start = self.end = 0

    @property
    def elapsed(self):
        return self.end - self.start

    @property
    def strtime(self):
        return strtime(self.elapsed)

    def __enter__(self):
        self.start  = time()
        return self

    def __exit__(self, *exc_info):
        self.end = time()
        if self.name is not None:
            self.emit()
        return False

    def emit(self):
        print '%s: %s' % (self.name, self.strtime)


