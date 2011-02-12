'''symbols and their packages
'''

from __future__ import with_statement
from __future__ import absolute_import

from contextlib import contextmanager
from itertools import count
import string

from .multimethod import defmethod
from .ports import PortList,connect,disconnect,disconnect_all,get_cells
from .as_string import as_string
from .purity import register_pure
from .atypes import as_type, IsType
from .delete import do_deletion, delete_obj
from . import state as state


__all__ = '''Symbol symbolp make_symbol UnboundSymbolError boundp
           set_symbol_cell get_symbol_cell unset_symbol_cell
           PackageError  SymbolConflict InternalSymbolError
           Package packagep  get_package package_context
           all_used_packages all_use_packages
           get_symbol_package internedp
           import_symbol unimport_symbol
           shadowing_import
           intern_symbol unintern_symbol
           export_symbol unexport_symbol
           use_package unuse_package
           resolve_print_form
           sys_package user_package gensyms_package
           keywords_package attributes_package
           get_sys_symbol syssymbolp
           make_keyword keywordp
           make_attribute attributep
           reset_gensym_counter gensym gensymbolp
           '''.split()


class Symbol(object):

    __slots__ = ['print_form']

    def __init__(self, print_form):
        self.print_form = print_form

    def __repr__(self):
        return 'Symbol(%r)' % (self.print_form,)

    __str__ = lambda self: as_string(self)

register_pure(Symbol)

@register_pure
def symbolp(op):
    return isinstance(op, Symbol)

@register_pure
def make_symbol(print_form):
    return Symbol(print_form)


defmethod(as_type, [Symbol])(IsType)

# # # # # # # # #
# symbol cells  #
# # # # # # # # #
# instead of each symbol having a cell,
# cell values are stored separately in a
# dictionary.  this is done as at runtime
# few symbols are expected to have global
# cells, and this reduces memory usage
# # # # # # # # # # # # # # # # # # # # #

class UnboundSymbolError(LookupError):

    def __init__(self, sym):
        self.sym = sym

    def __str__(self):
        return 'Symbol %s is not bound' % (sym,)

symbol_cells = {}

def boundp(sym):
    return sym in symbol_cells

def set_symbol_cell(sym, value):
    symbol_cells[sym] = value

no_default = None
def get_symbol_cell(sym, val=no_default):
    try:
        return symbol_cells[sym]
    except KeyError:
        if val is not no_default:
            return val
        raise UnboundSymbolError(sym)

def unset_symbol_cell(sym):
    try:
        del symbol_cells[sym]
    except KeyError:
        pass

def get_symbol_cells_map():
    return symbol_cells


# # # # # # #
# packages  #
# # # # # # #

class PackageError(Exception):
    pass

class SymbolConflict(PackageError):
    pass

class InternalSymbolError(SymbolConflict):
    pass

class Package(object):
    '''mapping of print forms to symbols
    '''

    deleted = False
    def __init__(self, name):
        self.name = name
        #set of symbols that are interned in this package
        self.interned = set()
        #symbols that are exported by this package
        #are also interned by this package
        self.exports = set()
        #mapping of print_form's to symbols as seen by this package
        #all interned symbols are automatically imported
        self.imports = {}
        #print_form's that may shadow print_forms in used packages
        #maps from print_form to package where symbol is imported
        self.shadows = {}
        #packages that are used by this package
        self.used_pkgs = PortList(self)
        #packages that use this package
        self.uses_pkgs = PortList(self)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def __str__(self):
        return repr(self)


def packagep(op):
    return isinstance(op, Package)

packages = {}
def get_package(name):
    '''packages are referred to by name, which are lower case strings
    '''
    global packages
    name = name.lower()
    try:
        return packages[name]
    except KeyError:
        packages[name] = Package(name)
        return packages[name]

@contextmanager
def package_context(package):
    '''use as:
        with package_context(pkg):
            stuff
       where stuff is executed with state.package set to pkg
    '''
    if isinstance(package, str):
        package = get_package(package)
    with state(package=package):
        yield None

def all_used_packages(pkg, recursive=True):
    acc = get_cells(pkg.used_pkgs)
    if recursive:
        for pkg in acc[::]:
            acc.extend(all_used_packages(pkg, True))
    return acc

def all_use_packages(pkg, recursive=True):
    acc = get_cells(pkg.uses_pkgs)
    if recursive:
        for pkg in acc[::]:
            acc.extend(all_use_packages(pkg, True))
    return acc


# # # # # # # # # # # # # # # #
#symbol managment in packages #
# # # # # # # # # # # # # # # #

def get_symbol_package(sym):
    for p in packages.itervalues():
        if sym in p.interned:
            return p
    return None

def internedp(sym):
    return get_symbol_package(sym) is not None

def find_print_form_package(package, print_form, require_export):
    '''find package where this symbol is imported
       when require_export is True, the symbol must also be exported
       when require_export is None, then export is not required on
          first package, is required on all used packages
    '''
    try:
        sym = package.imports[print_form]
    except KeyError:
        pass
    else:
        if not require_export or sym in package.exports:
            return package
    if require_export is None:
        require_export = True
    if print_form in package.shadows:
        return find_print_form_package(package.shadows[print_form], print_form,
                                       require_export)
    for used_pkg in get_cells(package.used_pkgs):
        found = find_print_form_package(used_pkg, print_form, require_export)
        if found is not None:
            return found
    return None

def check_print_form_conflict(package, print_form):
    '''check if print_form can be introduced into package
       without creating a symbol conflict with existing symbols
    '''
    export_package = find_print_form_package(package, print_form, None)
    if export_package is package:
        raise SymbolConflict('print_form %s already imported in package %s' %
                             (print_form, package.name))
    elif export_package:
        raise SymbolConflict('print_form %s inherited from package %s' %
                             (print_form, export_package.name))

def check_import_conflict(package, sym):
    check_print_form_conflict(package, sym.print_form)

def import_symbol(sym, package=None):
    '''map print form of sym to sym within the
       context of this package

       symbol is not necessarily interned in exported
       from this package
    '''
    if package is None:
        package = state.package
    check_import_conflict(package, sym)
    package.imports[sym.print_form] = sym
    return sym

def unimport_symbol(sym, package=None):
    if package is None:
        package = state.package
    if sym in package.exports:
        unexport_symbol(sym, package)
    if sym in package.interned:
        unintern_symbol(sym)
    try:
        isym =  package.imports.pop(sym.print_form)
    except KeyError:
        raise PackageError("can't unimport %s; not imported in %s" %
                           sym.print_form, package.name)
    else:
        if sym is not isym:
            package.imports[sym.print_form] = isym
            raise PackageError("can't remove %s; print_form has different symbol in this package"
                               % (sym.print_form, package.name))

def shadowing_import(sym, package=None):
    '''resolve mapping of symbol print_form to specific
       package, such that this mapping will shadow any future
       use_package that would introduce a symbol conflict
    '''
    src_pkg = get_symbol_package(sym)
    if src_pkg is None:
        raise PackageError("can't shadow uninterned symbols")
    if package is None:
        package = state.package
    check_import_conflict(package, sym)
    package.shadows[sym.print_form] = src_pkg

def _intern_symbol(sym, package):
    package.interned.add(sym)
    package.imports[sym.print_form] = sym
    return sym

def intern_symbol(sym, package=None):
    if internedp(sym):
        raise SymbolConflict('cannot intern %s; already interned' % (sym,))
    if package is None:
        package = state.package
    check_import_conflict(package, sym)
    return _intern_symbol(sym, package)

def unintern_symbol(sym):
    package = get_symbol_package(sym)
    if not package:
        raise PackageError('symbol is not interned')
    for pkg in all_use_packages(package, recursive=True):
        if sym in pkg.exports:
            raise PackageError("can't unintern %s::%s; exported in package %s" %
                               (package.name, sym.print_form, pkg.name))
    package.interned.remove(sym)
    assert package.imports[sym.print_form] is sym
    del package.imports[sym.print_form]

def export_symbol(sym, package=None):
    if package is None:
        package = state.package
    if sym.print_form not in package.imports:
        import_symbol(sym, package)
    package.exports.add(sym)

def unexport_symbol(sym, package=None):
    if package is None:
        package = state.package
    try:
        package.exports.remove(sym)
    except KeyError:
        raise PackageError("can't unexport %s from %s; not exported" %
                           (sym, package))

def check_package_cycle(up_pkg, chk_pkg):
    if chk_pkg is up_pkg:
        return True
    return any(check_package_cycle(up, chk_pkg)
               for up in get_cells(up_pkg.used_pkgs))

def use_package(src_pkg, dest_pkg=None):
    if dest_pkg is None:
        dest_pkg = state.package
    if check_package_cycle(src_pkg, dest_pkg) or check_package_cycle(dest_pkg, src_pkg):
        raise PackageError("can't use %s in %s; creates cycle"
                           % (src_pkg.name, dest_pkg.name))
    shadow_print_forms = set(dest_pkg.shadows)
    for sym in src_pkg.exports:
        if sym.print_form not in shadow_print_forms:
            check_import_conflict(dest_pkg, sym)
    connect(dest_pkg.used_pkgs,
            src_pkg.uses_pkgs)

def unuse_package(src_pkg, dest_pkg=None):
    if dest_pkg is None:
        dest_pkg = state.package
    disconnect(dest_pkg.used_pkgs,
               src_pkg.uses_pkgs)

def resolve_print_form(print_form, package=None):
    if package is None:
        package = state.package
    pkg = find_print_form_package(package, print_form, None)
    if pkg is not None:
        return pkg.imports[print_form]
    #new symbol, intern in this package
    return _intern_symbol(Symbol(print_form), package)

def symbol_visibility(sym, package=None):
    ''' None -> no visibility
        True -> directly visible
        "imported" -> imported, but not through intern or use_package
    '''
    if package is None:
        package = state.package
    pkg = find_print_form_package(package, sym.print_form, None)
    if pkg is None:
        return None
    if pkg.imports[sym.print_form] is not sym:
        return None
    if pkg is package:
        return True
    if sym not in pkg.exports:
        return 'imported'
    return True


# # # # # # # # # #
#builtin packages #
# # # # # # # # # #

builtin_packages = []
def builtin_packagep(op):
    return op in builtin_packages

def get_buildin_package(name):
    pkg = get_package(name)
    if not builtin_packagep(pkg):
        builtin_packages.append(pkg)
    return pkg

def resolve_and_export_print_form(print_form, package=None):
    if package is None:
        package = state.package
    sym = resolve_print_form(print_form, package)
    if sym not in package.exports:
        export_symbol(sym, package)
    return sym

def get_sys_symbol(print_form, export=True):
    return (resolve_and_export_print_form if export
            else resolve_print_form)(print_form.lower(), sys_package)

def syssymbolp(sym):
    return get_symbol_package(sym) is sys_package

def make_keyword(print_form):
    return resolve_and_export_print_form(print_form, keywords_package)

def keywordp(sym):
    return get_symbol_package(sym) is keywords_package

def keywordp(sym):
    return get_symbol_package(sym) is keywords_package

def make_attribute(print_form):
    return resolve_and_export_print_form(print_form, attributes_package)

def attributep(sym):
    return get_symbol_package(sym) is attributes_package

def reset_gensym_counter(start=0):
    global gensym_counter
    gensym_counter = iter(count(start)).next

reset_gensym_counter()

def gensym(base='g'):
    if base and (base[-1].isdigit() or base[-1] == '+'):
        base += '+'
    while True:
        print_form = '%s%d' % (base, gensym_counter())
        if print_form not in gensyms_package.imports:
            break
    return _intern_symbol(Symbol(print_form), gensyms_package)

def gensymbolp(sym):
    return get_symbol_package(sym) is gensyms_package

def gensym_base(sym):
    parts = list(sym.print_form)
    while parts and parts[-1].isdigit():
        parts.pop()
    if parts and parts[-1] == '+':
        parts.pop()
    return ''.join(parts)

def reduce_symbol(sym):
    if gensymbolp(sym):
        #gensyms always remade
        return gensym, (gensym_base(sym),)
    else:
        pkg = get_symbol_package(sym)
        #print sym.print_form, pkg and pkg.name
        return load_sym, (sym.print_form, pkg and pkg.name)

Symbol.__reduce__ = reduce_symbol
del reduce_symbol

def load_sym(print_form, pkg):
    if pkg:
        return resolve_print_form(print_form, get_package(pkg))
    return Symbol(print_form)

@defmethod(as_string, [Symbol])
def meth(sym):
    package = get_symbol_package(sym)
    if package is None or package is gensyms_package:
        return '#:%s' % sym.print_form
    elif package is keywords_package:
        return ':%s' % sym.print_form
    elif symbol_visibility(sym):
        return sym.print_form
    elif sym in package.exports:
        return '%s:%s' % (package.name, sym.print_form)
    else:
        return '%s::%s' % (package.name, sym.print_form)

def resolve_full_symbol_print_form(c, package=None):
    '''lexical rules for interpreting a symbol literal
        within the context of package
    '''
    if '::' in c:
        pkgname, print_form = c.split('::',1)
        return resolve_print_form(print_form, get_package(pkgname))
    elif ':' in c:
        if c.startswith(':'):
            return make_keyword(c[1:])
        pkgname, print_form = c.split(':',1)
        pkg = find_print_form_package(get_package(pkgname), print_form, True)
        if pkg is None:
            raise InternalSymbolError("%s dosn't export symbol %s" %
                                      (pkgname, print_form))
        return pkg.imports[print_form]
    elif c.startswith('&'):
        return get_sys_symbol(c)
    else:
        return resolve_print_form(c, package)

@defmethod(delete_obj, [Package])
def meth(package):
    global packages
    if builtin_packagep(package):
        raise PackageError("can't delete builtin package %s" % package.name)
    package.interned.clear()
    package.exports.clear()
    package.shadows.clear()
    package.imports.clear()
    disconnect_all(package.used_pkgs)
    disconnect_all(package.uses_pkgs)
    name = package.name
    package.name = '#<deleted:%s>' % name
    package.deleted = True
    del packages[name]

# # # # # # # # # # # # # # # # # #
# resetting of all package state  #
# # # # # # # # # # # # # # # # # #
# only to be used durring testing
# # # # # # # # # # # # # # # # #

reset_notifiers = []
def register_reset_notifier(func):
    reset_notifiers.append(func)
    return func

def reset_packages():
    '''only to be used during testing!
    '''
    gens = [func() for func in reset_notifiers]
    for gen in gens:
        try:
            gen.next()
        except StopIteration:
            pass
    bltin = builtin_packages[::]
    del builtin_packages[::]
    for pkg in bltin:
        do_deletion(pkg)
    for name in 'sys user core gensyms keywords attributes'.split():
        globals()['%s_package' % name] = get_buildin_package(name)
    state.top.__class__.package = user_package
    use_package(sys_package, dest_pkg=user_package)
    use_package(sys_package, dest_pkg=core_package)
    for gen in gens:
        try:
            gen.next()
        except StopIteration:
            pass

reset_packages()

