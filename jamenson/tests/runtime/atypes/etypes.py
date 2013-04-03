

import unittest

from jamenson.runtime.atypes import *
from jamenson.runtime.atypes.etypes import *


class TestETypes(unittest.TestCase):

    def chkt(self, tp, op):
        self.failUnless(typep(op, tp), "%r is not of type %s" % (op, tp))

    def chkf(self, tp, op):
        self.failIf(typep(op, tp), "%r is of type %s" % (op, tp))

    def chktseq(self, tp, seq):
        for el in seq:
            self.chkt(tp, el)

    def chkfseq(self, tp, seq):
        for el in seq:
            self.chkf(tp, el)

    evens = [0, 2L, -10, 20L, 1<<40]
    odds = [1,-1,-1001,1001, (1<<40) + 1]
    floats = map(float, evens + odds)
    non_numbers = ["0","1","2","adfadf", object(), [], range(10),
                   set(), dict()]

    def testeven(self):
        self.chktseq(even_type, self.evens)
        self.chkfseq(even_type, self.odds)
        self.chkfseq(even_type, self.floats)
        self.chkfseq(even_type, self.non_numbers)

    def testodd(self):
        self.chktseq(odd_type, self.odds)
        self.chkfseq(odd_type, self.evens)
        self.chkfseq(odd_type, self.floats)
        self.chkfseq(odd_type, self.non_numbers)

    def testzero(self):
        self.chktseq(zero_type, [0, 0L, 0.0, 0j+0])
        self.chkfseq(zero_type, [1,1L,1.0,1j+1,43,12L] + self.non_numbers)

    def testpositive(self):
        self.chktseq(positive_type, [5, 3, 12L, 1.0])
        self.chkfseq(positive_type, [0, -1, -10L, -43.54, 5j, -5j] +
                                    self.non_numbers)

    def testnegative(self):
        self.chktseq(negative_type, [-5, -3, -12L, -1.0])
        self.chkfseq(negative_type, [0, 1, 10L, 43.54, 5j, -5j] +
                                    self.non_numbers)

    def testiter(self):
        self.chktseq(iterable_type, [(), [], {}, set(), "", xrange(10),
                                     (x for x in xrange(10))])
        self.chkfseq(iterable_type, [1, None, lambda x : x])


__name__ == '__main__' and unittest.main()
