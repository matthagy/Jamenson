
from __future__ import with_statement

import unittest

from jamenson.runtime.delete import do_deletion, delete, state, delete_obj

class TestDelete(unittest.TestCase):

    def testatomic(op):
        do_deletion(1)
        do_deletion(1L)
        do_deletion(3.4)
        do_deletion(True)
        do_deletion(1j)
        do_deletion('adf')
        do_deletion(r'adf')
        do_deletion(None)

    def testlist(self):
        l = range(3)
        do_deletion(l)
        self.failUnlessEqual(l, [])

    def testdict(self):
        d = dict((x,str(x)) for x in xrange(5))
        do_deletion(d)
        self.failUnlessEqual(d, {})

    def testset(self):
        s = set(range(5))
        do_deletion(s)
        self.failUnlessEqual(s, set())


    def testrecursions(self):
        l0 = [1,2,3]
        l1 = [1,2,l0]
        l2 = ['a','b',l1]
        l3 = ['xxx','zzz',l2]
        l4 = [3.3,43L,l3]
        do_deletion(l4, recursions=2)
        self.failUnlessEqual(l4, [])
        self.failUnlessEqual(l3, [])
        self.failUnlessEqual(l0, [1,2,3])
        self.failUnlessEqual(l1, [1,2,l0])
        self.failUnlessEqual(l2, ['a','b',l1])

    def testrec(self):
        l = [[1,2],{'a':'b',3:'3'}, "stuff"]
        l.append(l)
        do_deletion(l)
        self.failUnlessEqual(l, [])



__name__ == '__main__' and unittest.main()
