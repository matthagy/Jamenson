'''Jamenson Compiler Front End
'''

from __future__ import absolute_import
from __future__ import with_statement

from hlab.pathutils import FilePath
from optparse import OptionParser

from .util import err, msg, vmsg, vemit, set_verbosity, get_prog_name, evaling_context
from ..compiler.util import timing
from ..compiler.block import BlockCompiler
from ..runtime.require import state as require_state
from ..runtime import state as runtime_state
from ..runtime.symbol import get_package, use_package
from ..runtime.compiled import write_code


def main():
    global config
    config = configure()
    if not config.nouser:
        #populate user package through side effects
        from ..core import user
    for target in config.targets:
        compile_target(target)

class vtiming(timing):

    def __init__(self, v, name):
        super(vtiming, self).__init__(name)
        self.v = v
        vemit(self.v, '%s: %s: ' % (get_prog_name(), self.name,))

    def emit(self):
        vemit(self.v, self.strtime + '\n')

def compile_target(target):
    dest = get_dest_path(target)
    with evaling_context(FilePath(target) if target != '-' else None, config.package):
        compiler = FrontEndCompiler.create(filename=target.abspath())
        vmsg(0, 'compiling %s', target)
        with timing() as time:
            code = compiler.construct_code()
        vmsg(1, 'elapsed time %s', time.strtime)
        write_code(code, dest)

def get_dest_path(target):
    base = target.basename()
    if base.endswith('.jms'):
        base = base.rsplit('.',1)[0]
    return target.sibling(base + '.jmc')

def configure():
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
    parser.add_option('--nouser',
                      dest='nouser',
                      default=False,
                      action='store_true',
                      help="don't populate user package")
    options,args = parser.parse_args()
    targets = []
    for arg in args:
        target = FilePath(arg)
        if not target.exists():
            msg('skipping non-existent file %s', target)
            continue
        targets.append(target)
    if not targets:
        msg('no targets specified')
    options.targets = targets
    set_verbosity(options.verbosity)
    return options


class FrontEndCompiler(BlockCompiler):

    def read_all_top_level_forms(self):
        vmsg(1, 'loading forms')
        with timing() as time:
            op = super(FrontEndCompiler, self).read_all_top_level_forms()
        vmsg(1, 'loaded forms in %s', time.strtime)
        return op

    def read_and_translate_form(self):
        self.stream.strip_whitespace()
        with vtiming(2, 'load %s.%d' % (self.stream.filename.basename(), self.stream.lineno)):
            return super(FrontEndCompiler, self).read_and_translate_form()

    def block_transform(self, top_expr):
        with vtiming(1, 'transforming top level expressions'):
            return super(FrontEndCompiler, self).block_transform(top_expr)

    def compile_top_expr(self, top_expr):
        with vtiming(1, 'generating code'):
            return super(FrontEndCompiler, self).compile_top_expr(top_expr)


