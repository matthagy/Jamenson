'''Block compilation
'''

from __future__ import absolute_import
from __future__ import with_statement

from ..runtime.read import read, readstate, Stream
from ..runtime.copy import make_copy
from . import ir as I
from . import bind
from . import codegen
from .translate import translate_top_level_form
from .declare import OptimizationTradeoffs
from .walk import contains_type
from .preeval import evaluate_compile_time_values
from ..transform.state import run_transformation
from ..transform.progn_flatten import flatten_a_progn


block_compiler = None

class BlockCompiler(object):

    def __init__(self, stream, tradeoffs):
        self.stream = stream
        self.tradeoffs = tradeoffs
        self.top_level_forms = []

    @classmethod
    def create(cls, bytes=None, filename=None, start_lineno=None, tradeoffs=None):
        if bytes is None:
            if filename is None:
                raise RuntimeError('no byte source')
            bytes = open(filename)
        return cls(Stream(bytes, filename=filename, start_lineno=start_lineno),
                   tradeoffs or OptimizationTradeoffs())

    def construct_code(self):
        global block_compiler
        old_block_compiler = block_compiler
        block_compiler = self
        try:
            self.read_all_top_level_forms()
            top_expr = self.combine_expressions()
            top_expr = self.block_transform(top_expr)
            code = self.compile_top_expr(top_expr)
            self.cleanup()
            return code
        finally:
            block_compiler = old_block_compiler

    def cleanup(self):
        self.stream.close()
        self.stream = None
        self.top_level_forms = None

    def read_all_top_level_forms(self):
        while True:
            ir = self.read_and_translate_form()
            if ir is None:
                break
            if ir is False:
                continue
            self.top_level_forms.append(ir)

    def read_and_translate_form(self):
        eof = object()
        with readstate(stream=self.stream, record_forms=True):
            expr = read(eofp=eof)
            if expr is eof:
                return None
            locs = readstate.form_locations
        ir = translate_top_level_form(expr, form_locations=locs, filename=self.stream.filename)
        ir = self.eval_when_check(ir)
        return ir

    def eval_when_check(self, ir):
        assert isinstance(ir, I.toplevel)
        ir = run_transformation(ir, 'flatten_progns')
        self.eval_when_check_expr(ir.expression)
        if contains_type(I.evalwhen, ir, descend_into_functions=True):
            I.syntax_error(ir, 'evalwhen not in toplevel form')
        return ir

    def eval_when_check_expr(self, expr):
        if isinstance(expr, I.evalwhen):
            assert expr.continuation
            self.eval_when_check_expr(expr.expression)
            if I.W_COMPILE_TOPLEVEL in expr.when:
                if len(expr.when)==1:
                    I.replace_with_nop(expr)
                    self.compile_time_eval(expr.expression)
                    return
                else:
                    self.compile_time_eval(make_copy(expr.expression))
            if I.W_LOAD_TOPLEVEL not in expr.when:
                #remove
                I.replace_with_nop(expr)
            else:
                #short circuit eval-when
                I.replace_child(expr, expr.expression)
        elif isinstance(expr, I.progn):
            for sub_expr in expr.exprs:
                self.eval_when_check_expr(sub_expr)
            flatten_a_progn(expr)

    def combine_expressions(self):
        scope = bind.Scope(manage_locals=True)
        exprs = []
        for ir in self.top_level_forms:
            assert isinstance(ir, I.toplevel)
            assert ir.scope.manage_locals
            assert not ir.scope.parent
            ir.scope.manage_locals = False
            ir.scope.parent = scope
            exprs.append(ir.expression)
        progn = I.make_progn(exprs)
        top_expr = I.make_toplevel(progn, scope)
        if self.top_level_forms:
            I.copy_loc(progn, self.top_level_forms[0])
            I.copy_loc(top_expr, self.top_level_forms[0])
        return top_expr

    def common_transform(self, ir):
        ir = evaluate_compile_time_values(ir, self.compile_time_eval)
        ir = common_transform(ir)
        return ir

    enable_marshal_transform = True
    def marshal_transform(self, top_expr):
        if self.enable_marshal_transform:
            top_expr = run_transformation(top_expr, 'to_marshalable')
        return top_expr

    def block_transform(self, top_expr):
        top_expr = self.common_transform(top_expr)
        top_expr = self.marshal_transform(top_expr)
        top_expr.expression = I.copy_loc(I.make_progn([top_expr.expression,
                                                       I.make_constant(None)]),
                                         top_expr)
        return top_expr

    def compile_time_eval(self, ir):
        top = run_transformation(ir, 'as_top_expression')
        top.filename = self.stream.filename #shouldn't be necessary
        code = self.compile_to_code(self.common_transform(top))
        return eval(code)

    def compile_top_expr(self, top_expr):
        return self.compile_to_code(top_expr)

    def compile_to_code(self, ir):
        return codegen.compile_to_code(ir, tradeoffs=self.tradeoffs)

def common_transform(ir):
    return run_transformation(ir, 'default')

def compile_time_eval(ir):
    ir = evaluate_compile_time_values(ir, compile_time_eval)
    ir = common_transform(ir)
    code = codegen.compile_to_code(ir)
    return eval(code)
