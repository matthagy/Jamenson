
import unittest
import cPickle as pickle
from random import Random
import operator

from jamenson.runtime.collections import OrderedDict, OrderedSet

class TestOrderedDict(unittest.TestCase):

    def setUp(self):
        self.rnd = Random(0xC0EDA55)
        self.seq = range(1000)
        self.rnd.shuffle(self.seq)
        self.od = OrderedDict()
        for k in self.seq:
            self.od[k] = self.rnd.random()

    def testorder(self):
        self.failUnlessEqual(list(self.od), self.seq)
        k,v = map(list, zip(*self.od.iteritems()))
        self.failUnlessEqual(k, self.seq)

    def testcp(self):
        od2 = OrderedDict(self.od)
        self.failUnlessEqual(list(od2), self.seq)
        self.failUnlessEqual(od2, self.od)

    def testdictcp(self):
        d = dict(self.od)
        self.failUnlessEqual(d, self.od)

    def testpickle(self):
        od2 = pickle.loads(pickle.dumps(self.od))
        self.failUnlessEqual(list(od2), self.seq)
        self.failUnlessEqual(od2, self.od)


class TestOrderedSet(unittest.TestCase):

    def setUp(self):
        self.rnd = Random(0xC0EDA55)
        def rndseq():
            start = self.rnd.randrange(-50,50)
            length = self.rnd.randrange(80,300)
            seq = range(start,start+length)
            self.rnd.shuffle(seq)
            return seq
        self.seqs = [rndseq() for _ in xrange(5)]


    setop_names = '''and_ eq ge gt le lt ne or_ sub xor
                  '''.split()
    setop_funcs = list(getattr(operator,x) for x in setop_names)


    def testsetish(self):
        for seq in self.seqs:
            s = set(seq)
            os = OrderedSet(seq)
            self.failUnlessEqual(s, os)
            self.failUnlessEqual(s.copy(), os.copy())
            for seq2 in self.seqs:
                s2 = set(seq2)
                os2 = OrderedSet(seq2)
                for name,func in zip(self.setop_names, self.setop_funcs):
                    self.failUnlessEqual(func(s,s2), func(os,os2),
                                         'set operation "%s" is not consistent for seqs; \n %s \n %s \n gives \n %s \n %s'
                                         % (name, seq, seq2,
                                            func(s,s2), func(os,os2)))

    def testorder(self):
        for seq in self.seqs:
            self.failUnlessEqual(list(OrderedSet(seq)), seq)

    def testoporder(self):
        for seq in self.seqs:
            os = OrderedSet(seq)
            for seq2 in self.seqs:
                os2 = OrderedSet(seq2)
                for name,func in zip(self.setop_names, self.setop_funcs):
                    oso = func(os,os2)
                    if isinstance(oso, bool):
                        continue
                    order = []
                    for x in seq+seq2:
                        if x in oso and x not in order:
                            order.append(x)
                    osorder = list(oso)
                    self.failUnlessEqual(order, osorder,
                                         'set operation "%s" does\'t preserve order for \n %s \n %s expected: \n %s \n given: %s'
                                         % (name, seq, seq2,
                                            order, osorder))


    def testpickle(self):
        for seq in self.seqs:
            s = set(seq)
            os = OrderedSet(seq)
            os2 = pickle.loads(pickle.dumps(os))
            self.failUnlessEqual(list(os), seq)
            self.failUnlessEqual(os2, os)


__name__ == '__main__' and unittest.main()

