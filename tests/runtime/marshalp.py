
import unittest

from jamenson.runtime.marshalp import marshalp

try:
    from numpy import arange
except ImportError:
    arange = None



class TestMarshalp(unittest.TestCase):

    def test_atomic(self):
        def test(op):
            self.failUnless(marshalp(op), '%s is not marshalp' % (op,))
        test(None)
        test(3)
        test(10.3)
        test(5L)
        test('adfaf')
        test(u'afafd')
        test(1j)

    def test_collections(self):
        def test(op):
            self.failUnless(marshalp(op), '%s is not marshalp' % (op,))
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

    def test_non_marshal(self):
        def test(op):
            self.failIf(marshalp(op), '%s is marshalp' % (op,))
        test(object())
        test(type)
        if arange is not None:
            test(arange(3))
        test(type(None))

    def test_cyclic_collections(self):
        def test(op):
            self.failIf(marshalp(op))
        l = []
        l.append(l)
        test(l)
        x = []
        d = {'a':x}
        x.append(d)
        test(d)
        test(x)

    def test_code(self):
        def test(op):
            self.failUnless(marshalp(op))
        def x(a,b):
            return a+b
        test(x.func_code)
        test((lambda : None).func_code)


__name__ == '__main__' and unittest.main()


