from __future__ import absolute_import
from __future__ import with_statement

from .symbol import get_package, Package, resolve_print_form, symbol_cells, find_print_form_package
from .modulemagic import setmod


class PackageProxy(object):

    def __init__(self, package):
        if isinstance(package, str):
            package = get_package(package)
        assert isinstance(package, Package)
        self._package = package

    def __getattr__(self, name):
        sym = self._attribute_to_symbol(name)
        try:
            return symbol_cells[sym]
        except KeyError:
            raise AttributeError("package '%s' has no attribute %r (symbol %r)" % (self.package.name, name, sym.print_form))

    def __setattr__(self, name, value):
        if name.startswith('_'):
            self.__dict__[name] = value
        else:
            symbol_cells[self._attribute_to_symbol(name)] = value

    def _attribute_to_symbol(self, name):
        assert not name.startswith('_')
        hyphen_name = name.replace('_', '-')
        if find_print_form_package(self._package, hyphen_name, None) is not None:
            name = hyphen_name
        return resolve_print_form(name, self._package)

    def install(self, modname):
        setmod(modname, self)
        return self

    def __dir__(self):
        return list(self.__dict__) + list(self._package.imports)

