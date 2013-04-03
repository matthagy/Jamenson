
import unittest

from jamenson.runtime.as_string import as_string

class TestStr(unittest.TestCase):

    def teststr(self):
        self.failUnlessEqual('"abc"', as_string('abc'))
        self.failUnlessEqual('""', as_string(''))
        self.failUnlessEqual('" x y z"', as_string(' x y z'))

    def testesc(self):
        self.failUnlessEqual(r'"a\nb\nc"', as_string('a\nb\nc'))
        self.failUnlessEqual(r'"\xff\x00"', as_string('\xff\x00'))
        self.failUnlessEqual(r'"\"inner\""', as_string('"inner"'))
        self.failUnlessEqual(r'"\"a-b-c\""', as_string('"a-b-c"'))

__name__ == '__main__' and unittest.main()
