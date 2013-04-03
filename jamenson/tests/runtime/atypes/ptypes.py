

import unittest

from jamenson.runtime.atypes import *
from jamenson.runtime.atypes.ptypes import *


class TestPTypes(unittest.TestCase):

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

    def testbasics(self):
        self.chkt(none_type, None)
        self.chkf(none_type, [])
        self.chkt(ellipsis_type, Ellipsis)


    ints = [-10,0,3]
    longs = [-0xffffffffL,-43L, 0L, 12L]
    integers = ints + longs
    floats = [-32e20, -17.09, 0.0, 4.5, 1.0 / 3.0 * 1e40]
    scalars = integers + floats
    complexes = [-100j, 20-3j, 0j, 15j, 100j]
    numbers = complexes + scalars
    strs = ["","adf","1","5L","STUFF"]
    unicodes = map(unicode, strs)
    strings = strs + unicodes
    atoms = ([None, Ellipsis, True, False] +
             numbers + strings)
    objs = [object()]
    tuples = [(), (1,2), ("", "afd"), (1,0j, "adf", object())]
    lists = map(list, tuples)
    dicts = [{}, {1:2}, dict(a="adf",b=object(), c=34)]
    sets = [set(), set(range(5)), set("afdaf")]
    frozensets = map(frozenset, sets)
    all_sets = sets + frozensets
    collections = tuples + lists + dicts + all_sets

    def testnumbers(self):
        self.chktseq(integer_type, self.integers)
        self.chkfseq(integer_type, self.floats + self.complexes +
                                   self.strings + self.objs +
                                   self.collections)
        self.chktseq(scalar_number_type, self.scalars)
        self.chkfseq(scalar_number_type, self.complexes + self.strings +
                                         self.objs + self.collections)
        self.chktseq(number_type, self.numbers)
        self.chkfseq(number_type, self.strings + self.objs + self.collections)

    def teststr(self):
        self.chktseq(string_type, self.strings)
        self.chkfseq(string_type, self.collections + self.numbers)

    def testatomic(self):
        self.chktseq(atomic_type, self.atoms)
        self.chkfseq(atomic_type, self.objs)
        self.chkfseq(atomic_type, self.collections)



__name__ == '__main__' and unittest.main()
