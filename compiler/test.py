
from __future__ import absolute_import
from __future__ import with_statement

if __name__ == '__main__':
    import jamenson.compiler.test
    exit()

import marshal
from .util import timing

with timing('import'):
    from . import untranslate
    from ..runtime.symbol import get_sys_symbol, set_symbol_cell
    from .block import BlockCompiler


filename = 'test.jms'



class MyBlockCompiler(BlockCompiler):

    def __init__(self, *args, **kwds):
        super(MyBlockCompiler, self).__init__(*args, **kwds)

    def read_and_translate_form(self):
        with timing('%s.%d' % (self.stream.filename, self.stream.lineno)):
            return super(MyBlockCompiler, self).read_and_translate_form()

    def combine_expressions(self):
        with timing('combine expressions'):
            return super(MyBlockCompiler, self).combine_expressions()

    def block_transform(self, top_expr):
        with timing('block transform'):
            return super(MyBlockCompiler, self).block_transform(top_expr)

    def compile_top_expr(self, top_expr):
        with timing('codegen'):
            return super(MyBlockCompiler, self).compile_top_expr(top_expr)

compiler = MyBlockCompiler.create(filename=filename)
with timing('compile'):
    code = compiler.construct_code()

#from dis import dis
#dis(code)

with timing('dump'):
    bytes = marshal.dumps(code)

print 'bytes', len(bytes)

with timing('load'):
    code = marshal.loads(bytes)

with timing('eval'):
    eval(code)


