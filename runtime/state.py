
from __future__ import absolute_import

import sys
from .ctxsingleton import CtxSingleton

class RuntimeState(CtxSingleton):

    package = None
    def _cxs_setup_top(self):
        self.default_as_string = str
        self.special_form_emitters_enabled = True
        self.special_form_emitters = {}

    def _cxs_copy(self, **kwds):
        cp = self._cxs_super._cxs_copy(**kwds)
        if cp.special_form_emitters is self.special_form_emitters:
            cp.special_form_emitters = self.special_form_emitters.copy()
        return cp


state = RuntimeState()
sys.modules[__name__.rsplit('.',1)[0]].state  = state
sys.modules[__name__] = state
