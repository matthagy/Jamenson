
import unittest

from jamenson.runtime.atypes import *
from jamenson.runtime.atypes.accessors import *

class obj(object):
    def __init__(self, **kwds):
        vars(self).update(kwds)

class TestAccessors(unittest.TestCase):

    def testhasattr(self):
        self.failUnless(typep(obj(a="a"), HasAttr("a")))
        self.failIf(typep(obj(), HasAttr("a")))

    def testhasattropt(self):
        self.failUnlessEqual(HasAttr("a"),
                             as_optimized_type((HasAttr("a"), HasAttr("a"))))
        self.failUnlessEqual(as_optimized_type((HasAttr("a"), HasAttr("b"))),
                             as_optimized_type((HasAttr("a"),
                                                HasAttr("b"),
                                                HasAttr("a"),
                                                HasAttr("b"))))
    def testattr(self):
        self.failUnless(typep(obj(a=5),
                              Attr("a", int)))
        self.failIf(typep(obj(a=5),
                          Attr("a", str)))
        self.failUnlessRaises(AttributeError, typep, obj(), Attr("a", int))

    def testattropt(self):
        def test(a,b):
            self.failUnlessEqual(as_optimized_type(a),
                                 as_optimized_type(b))
        test(Attr("a",int),
             (Attr("a",int), Attr("a", int)))
        test(Attr("a", (int,long)),
             (Attr("a", int), Attr("a", long)))
        test(complement(Attr("a", int)),
             Attr("a", complement(int)))
        test(intersection(Attr("a", complement(int)), Attr("a", complement(long))),
             Attr("a", Invert(IsInstanceType(int,long))))
        test(Attr("a", anytype), anytype)

    def testitem(self):
        self.failUnless(typep([5],  Item(0, int)))
        self.failIf(typep([5],  Item(0, str)))
        self.failUnless(typep(dict(a=5),  Item("a", int)))
        self.failUnlessRaises(IndexError, typep, [10], Item(1, int))
        self.failUnlessRaises(KeyError, typep, {}, Item("a", int))

    def testitemopt(self):
        def test(a,b):
            self.failUnlessEqual(as_optimized_type(a),
                                 as_optimized_type(b))
        test(Item(0,int),
             (Item(0,int), Item(0, int)))
        test(intersection(Item("a", complement(int)), Item("a", complement(long))),
             Item("a", Invert(IsInstanceType(int,long))))
        test(Item("a", anytype), anytype)





__name__ == '__main__' and unittest.main()
