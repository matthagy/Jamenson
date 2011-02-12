'''Jamenson Executable
'''

from __future__ import absolute_import
from __future__ import with_statement

import sys
import marshal
from hlab.pathutils import FilePath
from optparse import OptionParser

from .util import err, msg, vmsg, vemit, set_verbosity, get_prog_name, evaling_context
from ..runtime import builtins #import for side effects
from ..runtime import load
from ..runtime.compiled import compile_source_ex

def main():
    global config
    config = configure()
    if not config.nouser:
        #populate user package through side effects
        from ..core import user
    for arg in config.args:
        evaluate(arg)

def evaluate(op):
    with evaling_context(FilePath(op) if op != '-' else None, config.package):
        eval(get_stdin_code() if op=='-' else get_file_code(op))

def get_file_code(path):
    path = FilePath(path)
    if not path.exists():
        err('no such file %s', path)
    return load.get_code(path)

def get_stdin_code():
    return compile_source_ex('<stdin>', sys.stdin)

def configure():
    parser = OptionParser()
    parser = OptionParser(usage='%prog [TARGET]',
                          epilog=__doc__,
                          add_help_option=False)
    parser.add_option('-?','--help',
                      action='help',
                      help='show this help message and exit')
    parser.add_option('-v','--verbose',
                      dest='verbosity',
                      default=0,
                      action='count',
                      help='increment extent of messages durring evaluation')
    parser.add_option('-p','--package',
                      dest='package',
                      default=None,
                      action='store',
                      metavar='PACKAGE',
                      help='specify initial package for compiling')
    parser.add_option('--nouser',
                      dest='nouser',
                      default=False,
                      action='store_true',
                      help="don't populate user package")
    options,args = parser.parse_args()
    if not args:
        args = ['-']
    options.args = args
    set_verbosity(options.verbosity)
    return options

