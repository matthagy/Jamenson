
import unittest

from jamenson.runtime.picklep import picklep

#global functions
from dis import dis
from pprint import pprint
from tokenize import tokenize


class TestPicklep(unittest.TestCase):

    def check_pickleable(self, op):
        self.failUnless(picklep(op), '%s is not pickleable' % (op,))

    def check_nonpickleable(self, op):
        self.failIf(picklep(op), '%s is pickleable' % (op,))

    def test_atomic(self):
        test = self.check_pickleable
        test(None)
        test(3)
        test(10.3)
        test(5L)
        test('adfaf')
        test(u'afafd')
        test(1j)

    def test_collections(self):
        test = self.check_pickleable
        test(())
        test([])
        test({})
        test(set())
        test(frozenset())
        test((1,2,3))
        test(range(10))
        test({'a':10L})
        test(set('adfafadfadffad'))
        test(frozenset(range(20)))
        test({'zzz':[range(5)]*10})

    def test_builtins(self):
        test = self.check_pickleable
        test(object)
        test(type)
        test(IOError)
        test(ValueError("stuff"))
        test(map)
        test(xrange(20))

    def test_global_functions(self):
        test = self.check_pickleable
        test(dis)
        test(pprint)
        test(tokenize)

    def test_non_pickleable(self):
        test = self.check_nonpickleable
        test(lambda a,b: None)

    def test_cyclic_collections(self):
        test = self.check_pickleable
        l = []
        l.append(l)
        test(l)
        x = []
        d = {'a':x}
        x.append(d)
        test(d)
        test(x)


__name__ == '__main__' and unittest.main()
