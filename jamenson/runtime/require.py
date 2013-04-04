'''Simple require framework to ensure certain packages are loaded
'''

from __future__ import absolute_import
from __future__ import with_statement

import sys
import re
import os
from contextlib import contextmanager

from .filepath import FilePath, DirPath

from .ctxsingleton import CtxSingleton
from .symbol import Symbol
#from .load import loadfile #at bottom

class RequireError(Exception):
    pass

class RequireState(CtxSingleton):

    def _cxs_setup_top(self):
        self.search_paths = ['.']
        self.loaded_packages = set()

state = RequireState()

@contextmanager
def files_search_path(filepath=None):
    if filepath is None:
        yield None
    else:
        directory = FilePath(filepath).abspath().parent()
        with state.top(search_paths = [directory] + state.top.search_paths):
            yield None

def require(*names):
    from .load import loadfile
    for name in names:
        name = normalize_name(name)
        if name in state.loaded_packages:
            return
        basepath = get_name_path(name)
        state.loaded_packages.add(name)
        try:
            loadfile(basepath, state.search_paths)
        except Exception:
            tp,value,tb = sys.exc_info()
            try:
                state.loaded_packages.remove(name)
            except Exception:
                pass
            raise tp,value,tb

def normalize_name(name):
    if isinstance(name, Symbol):
        name = name.print_form
    parts = re.split(r'[/.]+', name.strip())
    return '.'.join(parts)

def get_name_path(name):
    return name.replace('.', '/')



