
from __future__ import absolute_import
from __future__ import with_statement

import sys
import os.path
from contextlib import contextmanager

from ..runtime.require import files_search_path
from ..runtime import state as runtime_state
from ..runtime.symbol import get_package, use_package, all_used_packages


def get_prog_name():
    return os.path.basename(sys.argv[0])

def emit(bytes):
    sys.stderr.write(bytes)
    sys.stderr.flush()

def msg(msg='', *args):
    emit('%s: %s\n' % (get_prog_name(), msg%args if args else msg))

def err(*args):
    msg(*args)
    sys.exit(1)

verbosity = 0
def set_verbosity(v):
    global verbosity
    verbosity = v

def verbosity_check(v):
    return v<=verbosity

def vmsg(msg_verbosity, *args):
    if verbosity_check(msg_verbosity):
        msg(*args)

def vemit(msg_verbosity, bytes):
    if verbosity_check(msg_verbosity):
        emit(bytes)

@contextmanager
def evaling_context(filename, package_name=None):
    with files_search_path(filename):
        with runtime_state.top():
            if package_name is not None:
                runtime_state.package = get_package(package_name)
                for name in 'sys user'.split():
                    pkg = get_package(name)
                    if pkg not in all_used_packages(runtime_state.package):
                        use_package(pkg)
            yield None

