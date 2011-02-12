
import unittest
import cPickle as pickle

from jamenson.runtime.cons import Cons, clist, nil

class TestCons(unittest.TestCase):

    def testcons(self):
        c = Cons(1,1)
        self.failUnless(isinstance(c, Cons))
        self.failUnlessEqual(c.car, 1)
        self.failUnlessEqual(c.cdr, 1)

    def testnil(self):
        self.failUnlessEqual(nil.car, nil)
        self.failUnlessEqual(nil.cdr, nil)

    def testclist(self):
        c = clist(1,2,3)
        self.failUnless(isinstance(c, Cons))
        self.failUnlessEqual(c.car, 1)
        self.failUnlessEqual(c.cdr.car, 2)
        self.failUnlessEqual(c.cdr.cdr.car, 3)
        self.failUnlessEqual(c.cdr.cdr.cdr, nil)

    def testiter(self):
        seq = range(10)
        self.failUnlessEqual(list(clist(*seq)), seq)

    def teststr(self):
        self.failUnlessEqual(str(clist(1,2,3)), '(1 2 3)')
        self.failUnlessEqual(str(clist()), 'nil')

    def testpickle(self):
        def test(op):
            self.failUnlessEqual(pickle.loads(pickle.dumps(op)), op)
        test(nil)
        test(clist(1,2))
        test(clist(clist('a','b'),'c'))


__name__ == '__main__' and unittest.main()
