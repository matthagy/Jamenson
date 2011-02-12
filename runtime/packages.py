'''Module-like proxies to the key packages
'''

from ..runtime.pkgproxy import PackageProxy

def install():
    names = '''
        sys user gensym keywords attributes core
        '''.split()
    for name in names:
        gbls[name] = PackageProxy(name)
    global all
    __all__ = names

install()
del install

