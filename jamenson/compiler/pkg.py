

from ..runtime.symbol import resolve_and_export_print_form, get_package, use_package, sys_package

compiler_pkg = get_package('compiler')

use_package(compiler_pkg, sys_package)

def get_compiler_symbol(print_form):
    return resolve_and_export_print_form(print_form, compiler_pkg)




