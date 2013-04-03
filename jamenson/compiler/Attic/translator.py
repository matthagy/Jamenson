
from __future__ import with_statement

from ..runtime.ctxsingleton import CtxSingleton
from ..runtime.read import read, readstate

class TranslatorState(CtxSingleton):

    def _cxs_setup_top(self):
        self.sexp_table = default_sexp_translation_table.copy()
        self.translate_auxillary = None
        self.scope = None
        self.sexp_depth = 0
        self.tag_bodies = []

def translate_expression(expr, filename=None, start_lineno=None, record_forms=None):
    with setup_reader(expr, filename, start_lineno, record_forms):
        
        return exit_reader(node, record_forms)
