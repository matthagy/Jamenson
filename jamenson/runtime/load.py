'''Utilities for loading jamenson source and compiled code
'''

from __future__ import absolute_import
from __future__ import with_statement

import os
import marshal
from warnings import warn

from .filepath import FilePath, DirPath

from .util import strtime
from .compiled import read_code, compile_source
#from .require import files_search_path #bottom

SOURCE_TYPE, COMPILED_TYPE = LOAD_TYPES = range(2)
SOURCE_EXT = 'jms'
COMPILED_EXT = 'jmc'

class LoadError(Exception):
    pass

class StaleCompilation(Warning):
    pass

def loadfile(path, search_paths=()):
    #import for side effects needed for code evaluation
    from . import builtins
    realpath,tp = find_load_target(path, search_paths)
    code = get_code(realpath, tp)
    from .require import files_search_path
    with files_search_path(realpath):
        eval(code)

def get_code(path, tp=None):
    if tp is None:
        tp = COMPILED_TYPE if path.endswith('.'+ COMPILED_EXT) else SOURCE_TYPE
    if tp==SOURCE_TYPE:
        return compile_source(path)
    elif tp==COMPILED_TYPE:
        return read_code(path)
    raise RuntimeError("bad load type %r" % (tp,))

def find_load_target(path, search_paths=()):
    path = FilePath(os.path.normpath(os.path.expanduser(path)))
    for search_dir in [None] if path.isabs() else search_paths:
        check_path = path if search_dir is None else DirPath(search_dir).child(path)
        if check_path.exists():
            return check_path, SOURCE_TYPE
        if check_path.endswith('.'+SOURCE_EXT) or check_path.endswith('.'+COMPILED_EXT):
            continue
        compiled_path = FilePath(check_path + '.' + COMPILED_EXT)
        source_path = FilePath(check_path + '.' + SOURCE_EXT)
        if compiled_path.exists():
            if source_path.exists():
                delta = source_path.mtime() - compiled_path.mtime()
                if delta > 0:
                    warn(StaleCompilation('source %s is newer than compilation target by %s' %
                                          (source_path, strtime(delta))))
            return compiled_path, COMPILED_TYPE
        if source_path.exists():
            return source_path, SOURCE_TYPE
    raise LoadError("no suitable target for %r" % (path,))

from .require import files_search_path
