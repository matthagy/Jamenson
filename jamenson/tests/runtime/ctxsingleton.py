
from __future__ import with_statement

import unittest

from jamenson.runtime.ctxsingleton import CtxSingleton


class TestState(CtxSingleton):

    def _cxs_setup_top(self):
        self.a = 5
        self.b = 10
        self.c = 'c'

    def _cxs_copy(self, **kwds):
        cp = self._cxs_super._cxs_copy()
        vars(cp).update(kwds)
        return cp


class TestCtxSingleton(unittest.TestCase):

    def setUp(self):
        self.state = TestState()

    def testtopcls(self):
        self.assertEqual(self.state.a, 5)
        self.assertEqual(self.state.b, 10)
        self.assertEqual(self.state.c, 'c')

    def testtop(self):
        self.assertEqual(self.state.top.a, 5)
        self.assertEqual(self.state.top.b, 10)
        self.assertEqual(self.state.top.c, 'c')

    def testpush(self):
        state = self.state
        eq = self.assertEqual
        eq(state.a, 5)
        eq(state.b, 10)
        eq(state.c, 'c')
        eq(state.top.a, 5)
        eq(state.top.b, 10)
        eq(state.top.c, 'c')
        with state(a=20, b=30, c='k'):
            eq(state.a, 20)
            eq(state.b, 30)
            eq(state.c, 'k')
            eq(state.top.a, 20)
            eq(state.top.b, 30)
            eq(state.top.c, 'k')
            eq(state[0].a, 5)
            eq(state[0].b, 10)
            eq(state[0].c, 'c')
            eq(state.bottom.a, 5)
            eq(state.bottom.b, 10)
            eq(state.bottom.c, 'c')
            with state(a=100):
                eq(state.a, 100)
                eq(state.b, 10)
                eq(state.c, 'c')
                eq(state[1].a, 20)
                eq(state[1].b, 30)
                eq(state[1].c, 'k')
                eq(state.bottom.a, 5)
                eq(state.bottom.b, 10)
                eq(state.bottom.c, 'c')
            with state.top(a=100):
                eq(state.a, 100)
                eq(state.b, 30)
                eq(state.c, 'k')
            eq(state.a, 20)
            eq(state.b, 30)
            eq(state.c, 'k')
        eq(state.a, 5)
        eq(state.b, 10)
        eq(state.c, 'c')

    def testrec(self):
        state = self.state
        eq = self.assertEqual
        def rec(i):
            if i!=0:
                with state(a=state.top.a+1):
                    rec(i-1)
            else:
                al = [state[i].a for i in xrange(1,state.depth)]
                assert al == range(state.depth-1)
        with state(a=0):
            rec(100)


__name__ == '__main__' and unittest.main()
