'''Jamenson Compiler Front End
'''

from __future__ import absolute_import
from __future__ import with_statement

import sys

from ..runtime.filepath import FilePath
from ..compiler.util import timing
from ..compiler.block import BlockCompiler
from ..runtime.compiled import write_code, dump_code
from .jmbase import JMBase


def main():
    global jmc
    jmc = JMC()
    jmc.main()

class JMC(JMBase):

    def process_target_in_package(self, target):
        dest = self.get_dest_path(target)
        compiler = self.create_compiler(target)
        self.vmsg(0, 'compiling %s', target)
        with timing() as time:
            code = compiler.construct_code()
        self.vmsg(1, 'elapsed time %s', time.strtime)
        self.emit_code(code, dest)

    @staticmethod
    def get_dest_path(target):
        if target == '-':
            return '-'
        base = target.basename()
        if base.endswith('.jms'):
            base = base.rsplit('.',1)[0]
        return target.sibling(base + '.jmc')

    def create_compiler(self, target):
        return (FrontEndCompiler.create(filename='<stdin>', bytes=sys.stdin)
                if target == '-' else
                FrontEndCompiler.create(filename=target))

    @staticmethod
    def emit_code(code, dest):
        if dest == '-':
            dump_code(code, sys.stdout)
        else:
            write_code(code, dest)


class vtiming(timing):

    def __init__(self, v, name):
        super(vtiming, self).__init__(name)
        self.v = v
        jmc.vemit(self.v, '%s: %s: ' % (jmc.get_prog_name(), self.name,))

    def emit(self):
        jmc.vemit(self.v, self.strtime + '\n')


class FrontEndCompiler(BlockCompiler):

    def read_all_top_level_forms(self):
        jmc.vmsg(1, 'loading forms')
        with timing() as time:
            op = super(FrontEndCompiler, self).read_all_top_level_forms()
        jmc.vmsg(1, 'loaded forms in %s', time.strtime)
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
