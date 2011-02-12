
from __future__ import with_statement

import unittest
import tempfile
from decimal import Decimal

from jamenson.runtime import state
from jamenson.runtime.symbol import (make_symbol, symbolp, boundp,
                                     UnboundSymbolError, set_symbol_cell, get_symbol_cell, unset_symbol_cell,
                                     PackageError, SymbolConflict, InternalSymbolError,
                                     packagep, get_package, package_context,
                                     all_used_packages, all_use_packages,
                                     get_symbol_package, internedp,
                                     find_print_form_package,
                                     import_symbol, unimport_symbol,
                                     shadowing_import,
                                     intern_symbol, unintern_symbol,
                                     export_symbol, unexport_symbol,
                                     use_package, unuse_package,
                                     resolve_print_form,
                                     get_sys_symbol, syssymbolp,
                                     make_keyword, keywordp,
                                     make_attribute, attributep,
                                     reset_packages,
                                     reset_gensym_counter, gensym, gensymbolp,
                                     resolve_full_symbol_print_form)
from jamenson.runtime.builtins import get_builtin_symbol, bltn_pkg
from jamenson.runtime.symbol import reset_packages
from jamenson.runtime.read import readone, readstate
from jamenson.runtime.cons import Cons, clist, nil
from jamenson.runtime.as_string import as_string
from jamenson.runtime.delete import delete, delete_obj

class TestRead(unittest.TestCase):

    def setUp(self):
        reset_packages()
        global sys_package, user_package, gensyms_package
        global keywords_package, attributes_package
        from jamenson.runtime.symbol import  sys_package, user_package, gensyms_package
        from jamenson.runtime.symbol import  keywords_package, attributes_package
        self.testpkg1 = get_package('testpkg1')
        self.testpkg2 = get_package('testpkg2')
        self.testpkg3 = get_package('testpkg3')

    def tearDown(self):
        delete(self.testpkg1)
        delete(self.testpkg2)
        delete(self.testpkg3)

    def check_eq(self, a,b):
        if isinstance(a,float) or isinstance(b,float):
            self.failUnlessAlmostEqual(a,b)
        else:
            self.failUnlessEqual(a,b)

    def check_literal(self, op):
        self.check_eq(readone(op), eval(op))

    def check_constant(self, op, cnst):
        self.check_eq(readone(op), cnst)

    def check_literals(self, lits):
        if isinstance(lits,str):
            lits = lits.split()
        for op in lits:
            self.check_literal(op)

    def testdecimal(self):
        self.check_literals('''
        1 0 10 -1 1000 23423 2342345235 2342325235235 -0
        -2134432 -34 -8 1000
        ''')

    def testhex(self):
        self.check_literals('''
        0x12 0x324 0x324235 -0x1 0x0
        -0x2343 0xff 0xaa 0xadaf324 0xff00 0xfa0adf
        0xDEEDBEEF 0xDeedBeef -0xC0EDA55 0xC0Eda55
        ''')

    def testoct(self):
        self.check_literals('''
        0234 -02 00 01 07 07777 -077 0353 -011
        0320324320230320320 -03224654046535404230
        ''')
        self.check_constant('0o0', 0)
        self.check_constant('0o1', 1)
        self.check_constant('-0o1', -1)
        self.check_constant('0o777',0777)
        self.check_constant('-0o505',-0505)
        self.check_constant('-0o130230323',-0130230323)

    def testbin(self):
        self.check_constant('0b0', 0)
        self.check_constant('0b1', 1)
        self.check_constant('-0b1', -1)
        self.check_constant('-0b100', -4)
        self.check_constant('0b1111', 15)
        self.check_constant('0b1' + '0'*20, 1<<20)
        self.check_constant('-0b1010101', -(1+4+16+64))

    def testfloat(self):
        self.check_literals('''
        0.0 1.0 -1.0 214. 52.0342
        .01 0.01
        12e10 -1.32e10 234.23e-10 -32.23e-23
        ''')
        self.check_constant('82.01e-12.32', 82.01 * 10 ** -12.32)

    def testdecimal(self):
        self.check_constant('1d', Decimal('1'))
        self.check_constant('1.00d', Decimal('1.00'))
        self.check_constant('1.00e-3d', Decimal('1.00e-3'))
        self.check_constant('-10.32d', Decimal('-10.32'))
        self.check_constant('010d', Decimal('8'))
        self.check_constant('0b100', Decimal('4'))

    def teststring(self):
        self.check_literal(r'"aadf"')
        self.check_literal(r'"a df"')
        self.check_literal(r'" a df "')
        self.check_literal(r'"  "')
        self.check_literal(r'""')
        self.check_literal(r'" \tad\tadf\nadf\nadf"')
        self.check_literal(r'" \xaf  \x326"')
        self.check_literal(r'"adf\"adf\"adf"')
        self.check_constant('"adf\nadf"', 'adf\nadf')

    def testfile(self):
        t = tempfile.NamedTemporaryFile()
        try:
            print >>t, '12.324'
            t.flush()
            with open(t.name) as fp:
                self.failUnlessEqual(readone(fp), 12.324)
        finally:
            t.close()

    def testbuffer(self):
        s = '12.324'
        self.failUnlessEqual(readone(buffer(s)), float(s))

    def testlist(self):
        s = '12.324'
        self.failUnlessEqual(readone(list(s)), float(s))

    def testsymbol(self):
        sym = readone('stuff')
        self.failUnless(symbolp(sym))
        self.failUnlessEqual(sym.print_form, 'stuff')
        self.failUnlessEqual(get_symbol_package(sym), state.package)
        sym2 = readone('  stuff  ')
        self.failUnlessEqual(sym, sym2)
        sym3 = readone('  STUFF  ')
        self.failIfEqual(sym2, sym3)

    def testhairysymbols(self):
        def test(rep, pform=None):
            if pform is None:
                pform = rep
            sym = readone(rep)
            self.failUnless(symbolp(sym))
            self.failUnlessEqual(sym.print_form, pform)
        test('1+')
        test('1-2')
        test('1-2')
        test(r'\"', '"')
        test(r'\(\)', '()')
        test(r'\(||\)', '(||)')
        test(r'\#junk', '#junk')
        test(r'this\ thing', 'this thing')
        test(r'\;not\ a\ comment',';not a comment')

    def testpkg(self):
        with state(package=self.testpkg1):
            s1 = readone('stuff')
        with state(package=self.testpkg2):
            s2 = readone('stuff')
        self.failIfEqual(s1, s2)
        with state(package=self.testpkg1):
            self.failUnlessEqual(s1, readone('stuff'))
        self.failUnlessEqual(s1, readone('testpkg1::stuff'))
        self.failUnlessEqual(s2, readone('testpkg2::stuff'))
        self.failUnlessRaises(SyntaxError, readone, 'testpkg1:stuff')
        self.failUnlessRaises(SyntaxError, readone, 'testpkg2:stuff')
        with state(package=self.testpkg1):
            export_symbol(s1)
        self.failUnlessEqual(s1, readone('testpkg1:stuff'))
        self.failUnlessEqual(s2, readone('testpkg2::stuff'))
        self.failUnlessRaises(SyntaxError, readone, 'testpkg2:stuff')

    def testcons(self):
        self.failUnlessEqual(readone('()'), nil)
        self.failUnlessEqual(readone('(1 2 3)'), clist(1,2,3))
        self.failUnlessEqual(readone('(  1 2 3   )'), clist(1,2,3))
        self.failUnlessRaises(SyntaxError, readone, '( 1 3 3')
        self.failUnlessEqual(readone('(  "abd" 2 "gfh"   )'), clist("abd",2,"gfh"))
        self.failUnlessEqual(readone('(+ 1 2)'), clist(readone('+'), 1, 2))
        self.failUnlessEqual(readone('(() (1 2) (+ 3 (stuff)))'),
                                     clist(nil, clist(1,2),
                                           clist(readone('+'), 3, clist(readone('stuff')))))
        self.failUnlessEqual(readone('(1 . 2)'), Cons(1,2))

    def testquote(self):
        q = get_sys_symbol('quote')
        self.failUnlessEqual(readone("'()").car, q)
        self.failUnlessEqual(readone("'()"), clist(q, nil))
        self.failUnlessEqual(readone("'3243"), clist(q, 3243))
        self.failUnlessEqual(readone("'stuff"), clist(q, readone("stuff")))
        self.failUnlessEqual(readone("'(+ 1 2)"), clist(q, clist(readone('+'), 1, 2)))

    def testattr(self):
        attr = get_builtin_symbol('attr')
        self.failUnlessEqual(readone('a.b'),
                             clist(attr, readone('a'), make_attribute('b')))
        self.failUnlessEqual(readone('a.b.c'),
                             clist(attr, clist(attr, readone('a'),
                                               make_attribute('b')),
                                   make_attribute('c')))

    def testattrget(self):
        getter = get_builtin_symbol('make-attr-getter')
        self.failUnlessEqual(readone('..stuff'),
                             clist(getter, make_attribute('stuff')))
        self.failUnlessEqual(readone('..stuff.rough'),
                             clist(getter, make_attribute('stuff'), make_attribute('rough')))
        self.failUnlessEqual(readone('..stuff.rough.enough'),
                             clist(getter,
                                   make_attribute('stuff'),
                                   make_attribute('rough'),
                                   make_attribute('enough')))

    def testmeth(self):
        meth = get_builtin_symbol('make-call-method')
        self.failUnlessEqual(readone('.stuff'),
                             clist(meth, make_attribute('stuff')))
        self.failUnlessEqual(readone('.stuff.rough'),
                             clist(meth, make_attribute('stuff'), make_attribute('rough')))
        self.failUnlessEqual(readone('(.stuff.rough.enough a b)'),
                             clist(clist(meth,
                                         make_attribute('stuff'),
                                         make_attribute('rough'),
                                         make_attribute('enough')),
                                   readone('a'), readone('b')))

    def testhash(self):
        self.failUnlessRaises(SyntaxError, readone, '#.')
        self.failUnlessRaises(SyntaxError, readone, '#+')
        sym = make_symbol('abc')
        sym2 = make_symbol('')
        with readstate(hash_table={'.': lambda : sym,
                                   '+': lambda : sym2}):
            self.failUnlessEqual(readone('#.'), sym)
            self.failUnlessEqual(readone('#+'), sym2)
        self.failUnlessRaises(SyntaxError, readone, '#.')
        self.failUnlessRaises(SyntaxError, readone, '#+')

    def testinvariant(self):
        def test(s):
            use_package(bltn_pkg)
            try:
                self.failUnlessEqual(as_string(readone(s)), s)
            finally:
                unuse_package(bltn_pkg)
        test("12")
        test("0")
        test("32.4")
        test("adfadf")
        test("special::adfadf")
        test("(1 2 3)")
        test("(+ 4 5)")
        test('"adfafd"')
        test('("adfafd")')
        test('(+ "prefix-" "inner" "-suffix")')
        test("a.b")
        test(".a.b")
        test('(.choice.join ".")')
        test('(map .first seq)')
        test('(map .state.first seq)')
        test('(map ..first seq)')
        test('(map ..state.first seq)')
        test('(map (compose str .get_cell ..element) seq)')

    def testcomment(self):
        def test(a,b):
            self.failUnlessEqual(readone(a), readone(b))

__name__ == '__main__' and unittest.main()
