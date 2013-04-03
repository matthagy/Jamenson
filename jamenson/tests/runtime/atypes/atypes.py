
import unittest

from jamenson.runtime.atypes import *
from jamenson.runtime.atypes import (_AnyType, _NotAnyType, Invert, JoinBase, OneOf, AllOf)


class TestAtypes(unittest.TestCase):

    def testas_type(self):
        def test(op, cls):
            self.failUnless(isinstance(as_type(op), cls), '%s is not instance %s' % (op, cls))
        test(int, IsInstanceType)
        test(str, IsInstanceType)
        test(type, IsInstanceType)
        test(None, _NotAnyType)
        test(10, EqType)
        test("adfafddfa", EqType)
        test("adfafddfa", EqType)
        test(12j+10, EqType)
        test(range(3), MemberType)
        test(set(range(3)), MemberType)
        test(set([]), MemberType)
        test(lambda x : 1, Predicate)
        test((int,float,long,complex), OneOf)
        test((type(lambda x :x),type,int), OneOf)


    def testmatch(self):
        def test(tp, op, expect=True):
            self.failUnless(typep(op, as_type(tp))==expect,
                            'typep(%s, %s) != %s' % (op, tp, expect))
        test(int, 1)
        test(int, 0)
        test(int, 20)
        test(int, 20L, False)
        test(long, 20L)
        test(long, 12, False)
        test(float, 1.0)
        test(float, 1, False)
        test(str, 1, False)
        test(str, "adf")
        test(None, 1, False)
        test(None, None, False)
        test(None, 0, False)
        test(None, [], False)
        test(1, 1)
        test(1, 1L)
        test(1L, 1)
        test(1.0, 1.0)
        test(1.0, 1)
        test(1.1, 1, False)
        test(1, 1.1, False)
        test(range(3), 0)
        test(range(3), 1)
        test(range(3), 3, False)
        test(set([]), 0, False)
        test(set([1]), 1)
        test(set([1,2]), 2)
        test(lambda x: True, 1)
        test(lambda x: False, 1, False)
        test(lambda x: x%2==0, 1, False)
        test(lambda x: x%2==0, 0, True)

        evenp = as_optimized_type(intersection((int,long), lambda x : x%2==0))
        oddp = as_optimized_type(intersection((int,long), lambda x : x%2==1))
        bothp = as_optimized_type(intersection(evenp, oddp))
        eitherp = as_optimized_type(union(evenp, oddp))

        test(oddp, 1)
        test(oddp, 2, False)
        test(evenp, 1, False)
        test(evenp, 2, True)
        for x in xrange(0, 6):
            test(bothp, x, False)
            test(eitherp, x, True)

        test(evenp, "", False)
        test(eitherp, [32], False)
        test(eitherp, 1.1, False)
        test(eitherp, 1j, False)

        integerp = as_optimized_type((int,long))
        positivep = as_optimized_type(lambda x : x > 0)
        evenp = as_optimized_type(lambda x : x % 2 == 0)
        even_positive_integer = intersection(integerp, positivep, evenp)

        test(even_positive_integer, 2)
        test(even_positive_integer, -2, False)

    def testjoin(self):
        def test(tp, op, expect=True):
            self.failUnless(typep(op, as_type(tp))==expect,
                            'typep(%s, %s) != %s' % (op, tp, expect))

        test((int,long,str), 1)
        test((int,long,str), 1L)
        test((int,long,str), "1L")
        test((int,long,str), 1.0, False)
        test((int,long,str), [], False)
        test((int,long,str), None, False)
        test([1,2,3,4,"adf",object()], 5, False)
        test((1,2,3), 1)
        test((1,2,3), 4, False)
        test((1,2,3), None, False)
        test((1,2,3), object(), False)
        test((1,2,3), "adf", False)

    def testoptimize(self):
        def test(a,b):
            self.failUnlessEqual(as_optimized_type(a),
                                 as_optimized_type(b))
        def testn(a,b):
            self.failIfEqual(as_optimized_type(a),
                             as_optimized_type(b))
        test(1,1) #sanity
        test(1,[1])
        test(1,[1,1])
        test((notanytype,1), [1])
        test(intersection(anytype,1), [1])
        test((), notanytype)
        test([], notanytype)
        test(intersection(anytype,notanytype), [])
        test(intersection(notanytype, [1,2,3]), [])
        test((int,float,long), IsInstanceType(int,float,long))
        test((int,float,long,int), IsInstanceType(int,float,long))
        test((1,2,3), [1,2,3])
        test((1,2,3), [1L,2,3])
        test((int,(float,(long,int),(int,float))), (int,float,long))
        test(([1,2],3), [1L,2,3])
        test(([1,2],[3],[],[3],[4],0,1,2), range(5))
        x = 1
        test((IsType(x),EqType(x)), IsType(x))
        test(intersection(IsType(x),EqType(x)), IsType(x))
        test(intersection([1,2,3], [2,3,5]), [2,3])
        test(intersection(IsType(1), EqType(1L)), IsType(1))
        testn(intersection(IsType(1), EqType(1L)), EqType(1L))
        test(intersection(IsType(1), IsType(2)), notanytype)
        test(intersection(EqType(1), EqType(2)), notanytype)



__name__ == '__main__' and unittest.main()
