
from __future__ import with_statement

import cPickle as pickle
import unittest

from jamenson.runtime.ports import *

class TestSymbol(unittest.TestCase):

    def testdanglingsingle(self):
        self.failUnlessRaises(DanglingPort, get_cell, Port(0))

    def testsingle(self):
        a = Port(1)
        b = Port(2)
        self.failUnlessEqual(count_connections(a), 0)
        self.failUnlessEqual(count_connections(b), 0)
        self.failUnlessRaises(DanglingPort, get_cell, a)
        self.failUnlessRaises(DanglingPort, get_cell, b)
        self.failUnlessEqual(get_cells(a), [])
        self.failUnlessEqual(get_cells(b), [])
        connect(a,b)
        self.failUnlessEqual(count_connections(a), 1)
        self.failUnlessEqual(count_connections(b), 1)
        self.failUnlessEqual(get_cell(a), 2)
        self.failUnlessEqual(get_cell(b), 1)
        self.failUnlessEqual(get_cells(a), [2])
        self.failUnlessEqual(get_cells(b), [1])
        disconnect(a,b)
        self.failUnlessEqual(count_connections(a), 0)
        self.failUnlessEqual(count_connections(b), 0)
        self.failUnlessRaises(DanglingPort, get_cell, a)
        self.failUnlessRaises(DanglingPort, get_cell, b)
        self.failUnlessEqual(get_cells(a), [])
        self.failUnlessEqual(get_cells(b), [])

    def testsinglereconnect(self):
        a = Port(1)
        b = Port(2)
        c = Port(3)
        connect(a,b)
        self.failUnlessEqual(get_cell(a), 2)
        self.failUnlessEqual(get_cell(b), 1)
        self.failUnlessRaises(DanglingPort, get_cell, c)
        connect(a,c)
        self.failUnlessEqual(get_cell(a), 3)
        self.failUnlessEqual(get_cell(c), 1)
        self.failUnlessRaises(DanglingPort, get_cell, b)
        connect(c,b)
        self.failUnlessEqual(get_cell(b), 3)
        self.failUnlessEqual(get_cell(c), 2)
        self.failUnlessRaises(DanglingPort, get_cell, a)

    def testlistlist(self):
        a = PortList(1)
        b = PortList(2)
        a = Port(1)
        b = Port(2)
        self.failUnlessEqual(count_connections(a), 0)
        self.failUnlessEqual(count_connections(b), 0)
        self.failUnlessRaises(DanglingPort, get_cell, a)
        self.failUnlessRaises(DanglingPort, get_cell, b)
        self.failUnlessEqual(get_cells(a), [])
        self.failUnlessEqual(get_cells(b), [])
        connect(a,b)
        self.failUnlessEqual(count_connections(a), 1)
        self.failUnlessEqual(count_connections(b), 1)
        self.failUnlessEqual(get_cell(a), 2)
        self.failUnlessEqual(get_cell(b), 1)
        self.failUnlessEqual(get_cells(a), [2])
        self.failUnlessEqual(get_cells(b), [1])
        disconnect(a,b)
        self.failUnlessEqual(count_connections(a), 0)
        self.failUnlessEqual(count_connections(b), 0)
        self.failUnlessRaises(DanglingPort, get_cell, a)
        self.failUnlessRaises(DanglingPort, get_cell, b)
        self.failUnlessEqual(get_cells(a), [])
        self.failUnlessEqual(get_cells(b), [])

    def testmsinglelist(self):
        seq = range(10)
        singles = map(Port, seq)
        pl = PortList(None)
        for p in singles:
            connect(p, pl)
        self.failUnlessEqual(count_connections(pl), len(seq))
        for p in singles:
            self.failUnlessEqual(count_connections(p), 1)
            self.failUnlessEqual(get_cell(p), None)
        self.failUnlessEqual(get_cells(pl), seq)
        self.failUnlessRaises(AmbiguousConnection, get_cell, pl)
        disconnect_all(pl)
        self.failUnlessEqual(count_connections(pl), 0)
        for p in singles:
            self.failUnlessEqual(count_connections(p), 0)
            self.failUnlessRaises(DanglingPort, get_cell, p)
        self.failUnlessRaises(DanglingPort, get_cell, pl)
        self.failUnlessEqual(get_cells(pl), [])


__name__ == '__main__' and unittest.main()
