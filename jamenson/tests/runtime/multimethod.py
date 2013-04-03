
import unittest

from jamenson.runtime import multimethod as MM
from jamenson.runtime.multimethod import (MultiMethodError, only, before, after, around,
                                          InconsistenCallSignature, InvalidMethodArguments,
                                          NoSuchMethod, MultiMethod, InvalidCallArguments,
                                          MethodSignature, TypeSignature, Method,
                                          defmethod, current_method)
from jamenson.runtime.atypes import *


class TestMultiMethod(unittest.TestCase):

    def testidentity(self):
        mm = MultiMethod('identity')
        @defmethod(mm, 'object')
        def meth(op):
            return op
        eq = self.failUnlessEqual
        eq(1, mm(1))
        eq('xxx', mm('xxx'))
        o = object()
        eq(o, mm(o))
        o = range(10)
        eq(o, mm(o))

    def testadd(self):
        add = MultiMethod('add')
        @defmethod(add, '(int,float,long),(int,float,long)')
        def meth(a,b):
            return a+b
        def test(a,b):
            self.failUnlessEqual(a+b, add(a,b))
        test(0,0)
        test(1,10)
        test(0.0,0.0)
        test(12,5.6)

    def testsinglecombination(self):
        mm = MultiMethod()
        @defmethod(mm, 'int')
        def meth(op):
            return 'int'
        @defmethod(mm, 'float')
        def meth(op):
            return 'float'
        @defmethod(mm, 'long')
        def meth(op):
            return 'long'
        @defmethod(mm, 'object')
        def meth(op):
            return 'object'
        self.failUnlessEqual(mm(1), 'int')
        self.failUnlessEqual(mm(1.0), 'float')
        self.failUnlessEqual(mm(1L), 'long')
        self.failUnlessEqual(mm(1j), 'object')
        self.failUnlessEqual(mm('1'), 'object')

    def testsingleunhandled(self):
        mm = MultiMethod()
        @defmethod(mm, 'int')
        def meth(op):
            return 'int'
        self.failUnlessEqual(mm(1), 'int')
        self.failUnlessRaises(NoSuchMethod, mm, 1L)
        self.failUnlessRaises(NoSuchMethod, mm, '1')
        self.failUnlessRaises(NoSuchMethod, mm, ['1'])

    def testmulticombination(self):
        mm = MultiMethod()
        @defmethod(mm, 'int,int')
        def meth(a,b):
            return 'int+int'
        @defmethod(mm, 'long,int')
        def meth(a,b):
            return 'long+int'
        @defmethod(mm, 'object,object')
        def meth(a,b):
            return 'object+object'
        self.failUnlessEqual(mm(1,1), 'int+int')
        self.failUnlessEqual(mm(1L,1), 'long+int')
        self.failUnlessEqual(mm(1L,1L), 'object+object')

    def testmultiunhandled(self):
        mm = MultiMethod()
        @defmethod(mm, 'int,int')
        def meth(a,b):
            return 'int+int'
        @defmethod(mm, 'long,int')
        def meth(a,b):
            return 'long+int'
        self.failUnlessEqual(mm(1,1), 'int+int')
        self.failUnlessEqual(mm(1L,1), 'long+int')
        self.failUnlessRaises(MultiMethodError, mm, 1L, 1L)
        self.failUnlessRaises(MultiMethodError, mm, 1, 1L)
        self.failUnlessRaises(MultiMethodError, mm, '1', '1')
        self.failUnlessRaises(MultiMethodError, mm, 1)
        self.failUnlessRaises(MultiMethodError, mm, 1, 1, 1)

    def testkeywords(self):
        mm = MultiMethod()
        @defmethod(mm, 'int,b=int')
        def meth(a,b=3):
            return 'int+int'
        @defmethod(mm, 'int,b=long')
        def meth(a,b=3L):
            return 'int+long'
        self.failUnlessEqual(mm(1,b=1), 'int+int')
        self.failUnlessEqual(mm(1,1), 'int+int')
        self.failUnlessEqual(mm(1,b=1L), 'int+long')
        self.failUnlessEqual(mm(1,1L), 'int+long')
        self.failUnlessEqual(mm(1), 'int+long')
        self.failUnlessRaises(NoSuchMethod, mm, 1L)
        self.failUnlessRaises(NoSuchMethod, mm, 1L, 1L)
        self.failUnlessRaises(NoSuchMethod, mm, 1L, 1)
        self.failUnlessRaises(NoSuchMethod, mm, 1L, b=1)
        self.failUnlessRaises(InvalidMethodArguments, mm, 1, c=1)

    def testdiffkeywords(self):
        mm = MultiMethod()
        @defmethod(mm, 'a=int')
        def meth(a=1):
            return 'a'
        def trydef():
            @defmethod(mm, 'b=int')
            def meth(b=1):
                return 'b'
        self.failUnlessRaises(InconsistenCallSignature, trydef)
        def trydef():
            @defmethod(mm, 'int')
            def meth(b=1):
                return 'b'
        self.failUnlessRaises(InconsistenCallSignature, trydef)
        def trydef():
            @defmethod(mm, 'int,a=int')
            def meth(b=1):
                return 'b'
        self.failUnlessRaises(InconsistenCallSignature, trydef)

    def testoverride(self):
        mm = MultiMethod('override')
        @defmethod(mm, 'int')
        def meth(a):
            return 'org'
        @defmethod(mm, 'int')
        def meth(a):
            return 'ovr'
        self.failUnlessEqual(mm(1), 'ovr')

    def testbefore(self):
        mm = MultiMethod('before')
        order = []
        @defmethod(mm, 'int')
        def meth(a):
            order.append('org')
            return 'int'
        before_state = []
        @defmethod(mm, 'int', combination=before)
        def meth(a):
            order.append('before')
            before_state.append(a)
            return None
        self.failUnlessEqual(mm(3), 'int')
        self.failUnlessEqual(len(before_state), 1)
        self.failUnlessEqual(before_state[0], 3)
        self.failUnlessEqual(len(order), 2)
        self.failUnlessEqual(order, ['before','org'])

    def testafter(self):
        mm = MultiMethod('after')
        order = []
        @defmethod(mm, 'int')
        def meth(a):
            order.append('org')
            return 'int'
        after_state = []
        @defmethod(mm, 'int', combination=after)
        def meth(a):
            order.append('after')
            after_state.append(a)
            return None
        self.failUnlessEqual(mm(3), 'int')
        self.failUnlessEqual(len(after_state), 1)
        self.failUnlessEqual(after_state[0], 3)
        self.failUnlessEqual(len(order), 2)
        self.failUnlessEqual(order, ['org','after'])

    def testaround(self):
        mm = MultiMethod('around')
        @defmethod(mm, 'int')
        def meth(a):
            return 'org%d' % a
        @defmethod(mm, 'int', combination=around)
        def meth(callnext, a):
            return '%s:%d' % (callnext(a), a+10)
        self.failUnlessEqual(mm(0), 'org0:10')

    def testpred(self):
        integert = as_optimized_type((int,long))
        oddt = as_optimized_type(intersection(integert, lambda x : x % 2 == 1))
        event = as_optimized_type(intersection(integert, lambda x : x % 2 == 0))
        mm = MultiMethod()
        @defmethod(mm, 'oddt', ns=locals())
        def meth(x):
            return 'odd'
        @defmethod(mm, 'event', ns=locals())
        def meth(x):
            return 'even'
        @defmethod(mm, 'str')
        def meth(x):
            return 'neither'
        self.failUnlessEqual(mm(0), 'even')
        self.failUnlessEqual(mm(1), 'odd')
        self.failUnlessEqual(mm('1'), 'neither')
        self.failUnlessRaises(NoSuchMethod, mm, [1])

    def testmember(self):
        known = [1,2,3,4,"adf",object()]
        mm = MultiMethod()
        @defmethod(mm, 'known', ns=locals())
        def meth(x):
            return "known"
        @defmethod(mm, 'anytype')
        def meth(x):
            return "unkown"
        for x in known:
            self.failUnlessEqual(mm(x), "known")
        self.failUnlessEqual(mm(2L), "known")
        self.failUnlessEqual(mm(5), "unkown")
        self.failUnlessEqual(mm(1.05), "unkown")
        self.failUnlessEqual(mm("abc"), "unkown")
        self.failUnlessEqual(mm(object()), "unkown")

    def testdirect(self):
        mm = MultiMethod(cache=False)
        l = [1]
        @defmethod(mm, "lambda x, l=l: x in l", ns=locals())
        def meth(op):
            return True
        @defmethod(mm, "anytype")
        def meth(op):
            return False
        self.failUnlessEqual(mm(1), True)
        self.failUnlessEqual(mm(0), False)
        l.append(0)
        self.failUnlessEqual(mm(1), True)
        self.failUnlessEqual(mm(0), True)
        l.remove(1)
        self.failUnlessEqual(mm(1), False)
        self.failUnlessEqual(mm(0), True)

    def testpattern(self):
        mm = MultiMethod()
        @defmethod(mm, "lambda x : x>0")
        def meth(x):
            return x * mm(x-1)
        @defmethod(mm, "anytype")
        def meth(x):
            return 1
        self.failUnlessEqual(mm(0), 1)
        self.failUnlessEqual(mm(1), 1)
        self.failUnlessEqual(mm(2), 2)
        self.failUnlessEqual(mm(4), 4*3*2)
        from numpy import multiply
        self.failUnlessEqual(mm(10), multiply.reduce(range(1,11)))

    def testguard(self):
        mm = MultiMethod()
        rationalt = int,long,float
        i = intersection
        @defmethod(mm, "rationalt", ns=locals())
        def meth(x):
            return 1
        @defmethod(mm, "i(rationalt, lambda x: x>0)", ns=locals())
        def meth(x):
            return x * mm(x-1)
        @defmethod(mm, "anytype")
        def meth(x):
            raise TypeError("mm not supported for type %r" % (x,))
        self.failUnlessEqual(mm(0), 1)
        self.failUnlessEqual(mm(2), 2)
        self.failUnlessEqual(mm(4), 4*3*2)
        self.failUnlessRaises(TypeError, mm, 1j)
        self.failUnlessRaises(TypeError, mm, "1")
        self.failUnlessRaises(TypeError, mm, range(3))

    def testvectorize(self):
        mm = MultiMethod()
        rationalt = int,long,float
        i = intersection
        def vectorize(mm, vtype=list):
            @defmethod(mm, 'vtype', ns=locals())
            def meth(x):
                return map(mm, x)
        @defmethod(mm, "rationalt", ns=locals())
        def meth(x):
            return 1
        @defmethod(mm, "i(rationalt, lambda x: x>0)", ns=locals())
        def meth(x):
            return x * mm(x-1)
        @defmethod(mm, "anytype")
        def meth(x):
            raise TypeError("mm not supported for type %r" % (x,))
        self.failUnlessEqual(mm(0), 1)
        self.failUnlessEqual(mm(2), 2)
        self.failUnlessEqual(mm(4), 4*3*2)
        self.failUnlessRaises(TypeError, mm, 1j)
        self.failUnlessRaises(TypeError, mm, "1")
        self.failUnlessRaises(TypeError, mm, range(4))
        vectorize(mm)
        self.failUnlessEqual(mm(range(4)), [1,1,2,6])
        self.failUnlessRaises(TypeError, mm, [1,2,"3"])
        self.failUnlessRaises(TypeError, mm, "adfadf")
        self.failUnlessRaises(TypeError, mm, (1,2,3))

    def testclassify(self):
        mm = MultiMethod()
        @defmethod(mm, "anytype, list")
        def meth(op, acc):
            pass
        @defmethod(mm, "int, list", combination=around)
        def meth(callnext, op, acc):
            callnext(op, acc)
            acc.append('int')
        @defmethod(mm, "float, list", combination=around)
        def meth(callnext, op, acc):
            callnext(op, acc)
            acc.append('float')
        @defmethod(mm, "str, list", combination=around)
        def meth(callnext, op, acc):
            callnext(op, acc)
            acc.append('str')
        @defmethod(mm, "intersection(int, lambda x : x%2==0), list", combination=around)
        def meth(callnext, op, acc):
            callnext(op, acc)
            acc.append("even")
        @defmethod(mm, "intersection((int,float), lambda x : x>0), list", combination=around)
        def meth(callnext, op, acc):
            callnext(op, acc)
            acc.append("positive")
        def classify(op):
            acc = list()
            mm(op, acc)
            return acc
        def test(op, keys):
            self.failUnlessEqual(set(classify(op)), set(keys))
        test(-1, ["int"])
        test(1, ["int","positive"])
        test(4, ["int","positive","even"])
        test(1.2, ["float","positive"])
        test("adf", ["str"])
        test([], [])

    def testcurrentmethod(self):
        self.failUnlessRaises(MultiMethodError, current_method)
        mm = MultiMethod()
        @defmethod(mm, "int")
        def meth(x):
            self.failUnlessEqual(current_method(), mm)
            return x
        mm(1)
        self.failUnlessRaises(MultiMethodError, current_method)

    def testinherit(self):

        mm_vectorized = MultiMethod()
        @defmethod(mm_vectorized, "list")
        def meth(x):
            return map(current_method(), x)

        mm = MultiMethod(inherit_from=[mm_vectorized])
        @defmethod(mm, "(int,long,float)")
        def meth(op):
            return -op
        self.failUnlessEqual(mm(1), -1)
        self.failUnlessEqual(mm(1L), -1L)
        self.failUnlessEqual(mm(1.0), -1.0)
        self.failUnlessRaises(NoSuchMethod, mm, "adf")
        self.failUnlessRaises(NoSuchMethod, mm, (1,2))
        self.failUnlessEqual(mm([1,2,3L,-2,-5L,1.5,-2.3]),
                             [-1,-2,-3,2,5,-1.5,2.3])
        self.failUnlessRaises(NoSuchMethod, mm, [1,2,3.2,"st"])









__name__ == '__main__' and unittest.main()
