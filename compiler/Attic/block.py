'''Block compilation
'''

from __future__ import absolute_import
from __future__ import with_statement

from ..runtime.read import read, readstate, Stream
from ..runtime.copy import copy
from .translate import translate_top_level_form
from .global_trans import transform_global_symbol_use
from .marshal_trans import marshal_transform
from .top_trans import as_top_expression
from .preeval import transform_load_times, evaluate_compile_time_values
from .codegen import compile_to_code
from . import ir as I
from . import bind

from .constants import collect_constants
from ..runtime.marshalp import marshalp

class BlockCompiler(object):

    def __init__(self, stream):
        self.stream = stream
        self.top_level_forms = []

    @classmethod
    def create(cls, bytes=None, filename=None, start_lineno=None):
        if bytes is None:
            if filename is None:
                raise RuntimeError('no byte source')
            bytes = open(filename)
        return cls(Stream(bytes, filename=filename, start_lineno=start_lineno))

    def construct_code(self):
        self.read_all_top_level_forms()
        top_expr = self.combine_expressions()
        top_expr = self.block_transform(top_expr)
        code = self.compile_top_expr(top_expr)
        self.cleanup()
        return code

    def cleanup(self):
        self.stream.close()
        self.stream = None
        self.top_level_forms = None

    def read_all_top_level_forms(self):
        while True:
            ir = self.read_and_translate_form()
            if not ir:
                break
            if not self.eval_when_check(ir):
                continue
            self.top_level_forms.append(ir)

    def read_and_translate_form(self):

    def combine_expressions(self):

def block_compile(bytes=None, filename=None, start_lineno=None):
    if bytes is None:
        if filename is None:
            raise RuntimeError('no byte source')
        bytes = open(filename)
    stream = Stream(bytes, filename=filename, start_lineno=start_lineno)
    irs = []
    while 1:
        ir = read_and_translate(stream)
        if ir is None:
            break
        print I.ir_location_str(ir)
        if not eval_when_check(ir):
            continue
        irs.append(ir)
    top_expr = combine_expressions(irs)
    top_expr = block_transform(top_expr)
    code = compile_to_code(top_expr)
    return code

def read_and_translate(stream):
    eof = object()
    with readstate(stream=stream, record_forms=True):
        expr = read(eofp=eof)
        if expr is eof:
            return None
        locs = readstate.form_locations
    ir = translate_top_level_form(expr, form_locations=locs, filename=stream.filename)
    assert isinstance(ir, I.toplevel)
    return ir

def eval_when_check(ir):
    assert isinstance(ir, I.toplevel)
    if isinstance(ir.expression, I.evalwhen):
        when = ir.expression.when
        #short circuit eval-when
        ex = ir.expression.expression
        del ir.expression.expression
        del ir.expression
        ir.expression = ex
        if I.W_COMPILE_TOPLEVEL in when:
            evaluate_compile_toplevel(ir if len(when)==1 else copy(ir))
        if I.W_LOAD_TOPLEVEL not in when:
            return False
    return True

def combine_expressions(irs):
    scope = bind.Scope(manage_locals=True)
    exprs = []
    for ir in irs:
        assert isinstance(ir, I.toplevel)
        assert ir.scope.manage_locals
        assert not ir.scope.parent
        ir.scope.manage_locals = False
        ir.scope.parent = scope
        exprs.append(ir.expression)
    progn = I.make_progn(exprs)
    top_expr = I.make_toplevel(progn, scope)
    if irs:
        I.copy_loc(progn, irs[0])
        I.copy_loc(top_expr, irs[0])
    return top_expr

def evaluate_compile_toplevel(ir):
    compile_time_eval(copy(ir))

def compile_time_eval(ir):
    return eval(compile_to_code(common_transform(as_top_expression(ir))))

def common_transform(ir):
    ir = evaluate_compile_time_values(ir, compile_time_eval)
    ir = transform_load_times(ir)
    ir = transform_global_symbol_use(ir)
    return ir

def block_transform(top_expr):
    top_expr = common_transform(top_expr)
    top_expr = marshal_transform(top_expr)
    top_expr.expression = I.make_progn([top_expr.expression,
                                        I.make_constant(None)])
    return top_expr

