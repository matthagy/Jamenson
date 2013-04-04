'''Base class for compiler (jmc) and interprator (jms)
'''

from __future__ import absolute_import
from __future__ import with_statement

import sys
import os.path
from contextlib import contextmanager
from optparse import OptionParser

from ..runtime.filepath import FilePath
from ..runtime.require import files_search_path
from ..runtime import state as runtime_state
from ..runtime.symbol import get_package, use_package, all_used_packages
from ..core import install as install_core

class JMBase(object):

    def main(self):
        self.configure()
        if not self.nocore:
            install_core()
        for target in self.targets:
            self.process_target(target)

    def process_target(self, target):
        with files_search_path(FilePath(target) if target != '-' else None):
            with runtime_state.top():
                self.setup_package()
                self.process_target_in_package(target)

    def process_target_in_package(self, target):
        raise RuntimeError('process_target_in_package not implemented')

    def setup_package(self):
        if self.package is None:
            return
        runtime_state.package = get_package(self.package)
        for name in 'sys user'.split():
            pkg = get_package(name)
            if pkg is not runtime_state.package and pkg not in all_used_packages(runtime_state.package):
                use_package(pkg)

    def configure(self):
        options, args = self.get_opt_parser().parse_args()
        for name in dir(options):
            if not name.startswith('_'):
                setattr(self, name, getattr(options, name))
        targets = []
        for arg in args:
            target = FilePath(arg)
            if not target.exists():
                self.msg('skipping non-existent file %s', target)
            else:
                targets.append(target)
        if not targets:
            self.msg('no targets specified')
        self.targets = targets

    def get_opt_parser(self):
        parser = OptionParser()
        parser = OptionParser(usage='%prog [OPTIONS] [TARGETS]',
                                  epilog=__doc__,
                                  add_help_option=False)
        parser.add_option('-?','--help',
                          action='help',
                          help='show this help message and exit')
        parser.add_option('-v','--verbose',
                          dest='verbosity',
                          default=0,
                          action='count',
                          help='increment extent of messages durring compiling')
        parser.add_option('-p','--package',
                          dest='package',
                          default=None,
                          action='store',
                          metavar='PACKAGE',
                          help='specify initial package for compiling')
        parser.add_option('--nocore',
                          dest='nocore',
                          default=False,
                          action='store_true',
                          help="don't load core language functionality")
        return parser

    @staticmethod
    def get_prog_name():
        return os.path.basename(sys.argv[0])

    @staticmethod
    def emit(bytes):
        sys.stderr.write(bytes)
        sys.stderr.flush()

    def msg(self, msg='', *args):
        self.emit('%s: %s\n' % (self.get_prog_name(), msg%args if args else msg))

    def err(self, *args):
        self.msg(*args)
        sys.exit(1)

    verbosity = 0

    def verbosity_check(self, v):
        return v <= self.verbosity

    def vmsg(self, msg_verbosity, *args):
        if self.verbosity_check(msg_verbosity):
            self.msg(*args)

    def vemit(self, msg_verbosity, bytes):
        if self.verbosity_check(msg_verbosity):
            self.emit(bytes)



