
from __future__ import with_statement

import cPickle as pickle
import unittest

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
from jamenson.runtime.multimethod import MultiMethod, defmethod, NoSuchMethod
from jamenson.runtime.atypes import intersection, union
from jamenson.runtime.delete import do_deletion

class TestSymbol(unittest.TestCase):

    def setUp(self):
        reset_packages()
        global sys_package, user_package, gensyms_package
        global keywords_package, attributes_package
        from jamenson.runtime.symbol import  sys_package, user_package, gensyms_package
        from jamenson.runtime.symbol import  keywords_package, attributes_package
        self.testpkg = get_package('testpkg')
        self.testpkg2 = get_package('testpkg2')
        self.testpkg3 = get_package('testpkg3')

    def tearDown(self):
        do_deletion(self.testpkg)
        do_deletion(self.testpkg2)
        do_deletion(self.testpkg3)

    def testsymboleq(self):
        s = make_symbol('adf')
        self.failUnlessEqual(s,s)

    def testsymbolp(self):
        self.failUnless(symbolp(make_symbol('adf')))

    def testsetsymbol(self):
        sym = make_symbol('adfadf')
        set_symbol_cell(sym, 20)
        self.failUnless(boundp(sym))
        try:
            self.failUnlessEqual(get_symbol_cell(sym), 20)
        finally:
            unset_symbol_cell(sym)

    def testunset(self):
        sym = make_symbol('adfadf')
        set_symbol_cell(sym, 20)
        self.failUnless(boundp(sym))
        unset_symbol_cell(sym)
        self.failIf(boundp(sym))
        self.failUnlessRaises(UnboundSymbolError, lambda : get_symbol_cell(sym))

    def testpackagep(self):
        self.failUnless(packagep(sys_package))
        self.failIf(packagep(1))

    def testimport(self):
        with state(package=self.testpkg):
            sym = make_symbol('stuff')
            self.failIf(internedp(sym))
            import_symbol(sym)
            self.failUnlessEqual(find_print_form_package(state.package, sym.print_form, False),
                                 state.package)
            self.failIf(internedp(sym))
            unimport_symbol(sym)
            self.failIf(find_print_form_package(state.package, sym.print_form, False))
            self.failIf(internedp(sym))

    def testintern(self):
        with state(package=self.testpkg):
            sym = make_symbol('stuff')
            self.failIf(internedp(sym))
            intern_symbol(sym)
            self.failUnless(internedp(sym))
            self.failUnlessEqual(find_print_form_package(state.package, sym.print_form, False),
                                 state.package)
            unintern_symbol(sym)
            self.failIf(internedp(sym))
            self.failIf(find_print_form_package(state.package, sym.print_form, False))

    def testreintern(self):
        with state(package=self.testpkg):
            sym = make_symbol('stuff')
            intern_symbol(sym)
            self.failUnless(internedp(sym))
            self.failUnlessRaises(SymbolConflict, lambda : intern_symbol(sym))
            with state(package=self.testpkg2):
                self.failUnless(internedp(sym))
                self.failUnlessRaises(SymbolConflict, lambda : intern_symbol(sym))
                self.failIf(find_print_form_package(state.package, sym.print_form, False))
            unintern_symbol(sym)
            with state(package=self.testpkg2):
                self.failIf(internedp(sym))
                intern_symbol(sym)
                self.failUnless(internedp(sym))
                self.failUnlessRaises(SymbolConflict, lambda : intern_symbol(sym))
            self.failUnlessRaises(SymbolConflict, lambda : intern_symbol(sym))
            self.failUnless(internedp(sym))
            self.failIf(find_print_form_package(state.package, sym.print_form, False))
            unintern_symbol(sym)

    def testexport(self):
        with state(package=self.testpkg):
            sym = make_symbol('stuff')
            export_symbol(sym)
            self.failUnlessEqual(find_print_form_package(state.package, sym.print_form, False),
                                 self.testpkg)
            with state(package=self.testpkg2):
                self.failIf(find_print_form_package(state.package, sym.print_form, False))
                use_package(self.testpkg)
                self.failUnlessEqual(find_print_form_package(state.package, sym.print_form, False),
                                     self.testpkg)
                self.failUnlessRaises(SymbolConflict, lambda : import_symbol(sym))
            unimport_symbol(sym)
            self.failIf(find_print_form_package(state.package, sym.print_form, False))
            with state(package=self.testpkg2):
                self.failIf(find_print_form_package(state.package, sym.print_form, False))

    def testexportconflict(self):
        sym = make_symbol('stuff')
        sym2 = make_symbol('stuff')
        with state(package=self.testpkg):
            intern_symbol(sym)
            export_symbol(sym)
        with state(package=self.testpkg2):
            intern_symbol(sym2)
            export_symbol(sym2)
            self.failUnlessRaises(SymbolConflict, lambda : use_package(self.testpkg))
        with state(package=self.testpkg):
            self.failUnlessRaises(SymbolConflict, lambda : use_package(self.testpkg2))

    def testpkgcycle(self):
        use_package(self.testpkg, self.testpkg2)
        self.failUnlessRaises(PackageError, lambda : use_package(self.testpkg2, self.testpkg))

    @staticmethod
    def doresolve(sym, pkg=None, sep='::'):
        if pkg is None:
            ident = sym.print_form
        else:
            ident = '%s%s%s' % (pkg.name, sep, sym.print_form)
        return resolve_full_symbol_print_form(ident)

    def testshadow(self):
        sym1 = make_symbol('stuff')
        sym2 = make_symbol('stuff')
        res = self.doresolve
        with state(package=self.testpkg):
            intern_symbol(sym1)
            export_symbol(sym1)
        with state(package=self.testpkg2):
            intern_symbol(sym2)
            export_symbol(sym2)
        with state(package=self.testpkg3):
            shadowing_import(sym1)
            use_package(self.testpkg2)
            use_package(self.testpkg)
            self.failUnlessEqual(sym1, res(sym1))
            self.failUnlessEqual(sym2, res(sym1, self.testpkg2, ':'))
            self.failUnlessEqual(sym2, res(sym1, self.testpkg2, '::'))
            self.failUnlessEqual(sym1, res(sym1, self.testpkg, ':'))
            self.failUnlessEqual(sym1, res(sym1, self.testpkg, '::'))

    def testinternal(self):
        sym = make_symbol('stuff')
        res = self.doresolve
        with state(package=self.testpkg):
            intern_symbol(sym)
        with state(package=self.testpkg2):
            self.failUnlessRaises(InternalSymbolError, res, sym, self.testpkg, ':')
            self.failUnlessEqual(sym, res(sym, self.testpkg, '::'))
            with state(package=self.testpkg):
                export_symbol(sym)
            self.failUnlessEqual(sym, res(sym, self.testpkg, ':'))
            self.failUnlessEqual(sym, res(sym, self.testpkg, '::'))

    def testkeyword(self):
        key = resolve_full_symbol_print_form(':symbol')
        self.failUnless(keywordp(key))
        self.failUnlessEqual(key, resolve_full_symbol_print_form(':symbol'))
        self.failUnlessEqual(key, self.doresolve(key, keywords_package, '::'))
        self.failUnlessEqual(key, self.doresolve(key, keywords_package, ':'))
        self.failIfEqual(key, resolve_full_symbol_print_form(':Symbol'))
        self.failIfEqual(key, resolve_full_symbol_print_form(':SYMBOL'))

    def testattribute(self):
        attr = make_attribute('something')
        self.failUnless(attributep(attr))
        self.failUnlessEqual(attr, make_attribute('something'))
        self.failIfEqual(attr, make_attribute('Something'))
        self.failIfEqual(attr, make_attribute('SOMETHING'))

    def testgensym(self):
        g = gensym()
        self.failUnless(gensymbolp(g))
        self.failUnlessRaises(InternalSymbolError, self.doresolve, g, gensyms_package, ':')
        self.failUnlessEqual(g, self.doresolve(g, gensyms_package, '::'))
        g = gensym('XXX')
        self.failUnless(g.print_form.startswith('XXX'))
        self.failIf(str(g).startswith('XXX'))
        self.failUnless(str(g).startswith('#:'))
        self.failUnless('XXX' in str(g))
        self.failIf('xxx' in str(g))
        self.failIfEqual(g, gensym('XXX'))
        reset_gensym_counter()
        g0 = gensym('XXX')
        reset_gensym_counter()
        g1 = gensym('XXX')
        self.failIfEqual(g0, g1)

    def testsyssymbols(self):
        s1 = get_sys_symbol('xxx', export=False)
        self.failUnless(syssymbolp(s1))
        s2 = get_sys_symbol('XXX', export=False)
        self.failUnlessEqual(s1,s2)
        self.failUnless(None is find_print_form_package(user_package, 'xxx', None))
        self.failUnless(None is find_print_form_package(user_package, 'XXX', None))
        self.failUnlessEqual(s1, self.doresolve(s1, sys_package, '::'))
        self.failUnlessRaises(InternalSymbolError, self.doresolve, s1, sys_package, ':')
        s3 = get_sys_symbol('xxx', export=True)
        self.failUnlessEqual(s3, s1)
        self.failUnless(sys_package is find_print_form_package(sys_package, 'xxx', None))
        self.failUnlessEqual(s1, self.doresolve(s1))
        self.failUnlessEqual(s1, self.doresolve(s1, sys_package, ':'))
        self.failUnlessEqual(s1, self.doresolve(s1, sys_package, '::'))

    def testpickle(self):
        def pick(op):
            return pickle.loads(pickle.dumps(op))
        def test(op):
            self.failUnlessEqual(pick(op), op)
        a0 = make_symbol('a')
        b0 = make_symbol('b')
        self.failIfEqual(a0, pick(a0))
        with state(package=self.testpkg):
            a1 = intern_symbol(make_symbol('a'))
            b1 = intern_symbol(make_symbol('b'))
            test(a1)
            self.failIfEqual(a0, pick(a1))
            self.failIfEqual(a1, pick(a0))
            self.failIfEqual(b0, pick(a0))
            self.failIfEqual(b1, pick(a1))
        test(a1)
        self.failIfEqual(a0, pick(a1))
        self.failIfEqual(a1, pick(a0))
        self.failIfEqual(b0, pick(a0))
        self.failIfEqual(b1, pick(a1))
        with state(package=self.testpkg2):
            a2 = intern_symbol(make_symbol('a'))
            test(a2)
        test(a2)
        self.failIfEqual(a1, pick(a2))
        self.failIfEqual(a2, pick(a1))

    def testpkgcontext(self):
        self.failIfEqual(state.package,self.testpkg)
        with package_context(self.testpkg):
            self.failUnlessEqual(state.package,self.testpkg)
            with package_context(self.testpkg2):
                self.failUnlessEqual(state.package,self.testpkg2)
            self.failUnlessEqual(state.package,self.testpkg)
        self.failIfEqual(state.package,self.testpkg)

    def testsymboldispatch(self):
        s1,s2,s3 = syms = map(make_symbol, 's1 s2 s3'.split())
        mm = MultiMethod()
        @defmethod(mm,'s1', ns=locals())
        def meth(x):
            return '1'
        @defmethod(mm,'(s2,s3)', ns=locals())
        def meth(x):
            return '23'
        self.failUnlessEqual(mm(s1),'1')
        self.failUnlessEqual(mm(s2),'23')
        self.failUnlessEqual(mm(s3),'23')
        self.failUnlessRaises(NoSuchMethod, mm, 1)
        self.failUnlessRaises(NoSuchMethod, mm, 's1')
        self.failUnlessRaises(NoSuchMethod, mm, make_symbol('s1'))

    #Add difficult edge cases as they arise

__name__ == '__main__' and unittest.main()
