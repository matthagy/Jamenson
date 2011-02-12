'''Transform code s.t. the resulting code object can be marshalled.
   This is accomplished by pickling all non marhsallable constants and
   aranging for constants to be unpickled when program is loaded.
'''

from __future__ import absolute_import
from __future__ import with_statement

import cPickle as pickle
import pickle

from ..runtime.symbol import gensym
from ..runtime.marshalp import marshalp
from ..compiler import ir as I
from ..compiler import bind
from ..compiler.walk import IRWalker, ReducingWalker, propigate_location
from ..compiler.constants import collect_constants, ConstantsCollection
from ..compiler.annotate import annotate


class MarshalChecker(ReducingWalker):

    descend_into_functions = True

    def __init__(self):
        super(MarshalChecker, self).__init__(all)

    def visit_constant(self, node):
        return marshalp(node)

    def visit_compile_time_value(self, node):
        raise RuntimeError("compile_time_value not translated")

    def visit_load_time_value(self, node):
        raise RuntimeError("load_time_value not translated")


def marshalable_ir(node):
    return MarshalChecker().visit(node)


class MarshalTransformer(IRWalker):
    '''associate a gensym with each non-marshallable constant
    '''

    descend_into_functions = True

    def __init__(self, constants, constants_gensyms):
        super(MarshalTransformer, self).__init__()
        self.constants = constants
        self.constants_gensyms = constants_gensyms

    def visit_constant(self, cnst):
        if cnst.result_ignored: #won't be included in code
            return
        if cnst.value not in self.constants: #marshallable
            return
        gensym = self.constants_gensyms[self.constants.index(cnst.value)]
        scope = I.get_node_local_scope(cnst)
        rb = I.make_read_binding(scope.use_symbol(gensym))
        propigate_location(cnst, rb)
        I.replace_child(cnst, rb)


def transform_to_marshalable(ir):
    assert isinstance(ir, I.toplevel)
    #annotate to determine unused constants
    annotate(ir)
    constants = collect_constants(ir, descend_into_functions=True, skip_unused_constants=True)
    non_marshal_constants = filter(lambda op: not marshalp(op), constants)
    if not non_marshal_constants:
        return ir
    non_marshal_constants = ConstantsCollection(non_marshal_constants)
    constants_gensyms = list(gensym('const') for i in non_marshal_constants)
    map(ir.scope.register_local, constants_gensyms)
    MarshalTransformer(non_marshal_constants, constants_gensyms).visit(ir)
    set_gensyms = I.make_unpack_seq(places=map(ir.scope.use_symbol, constants_gensyms),
                                    seq=I.make_call(callee=I.make_attrget(obj=I.make_import_name('cPickle'),
                                                                          name='loads'),
                                                    args=[I.make_constant(pickle.dumps(list(non_marshal_constants)))],
                                                    kwd_names=[], kwd_values=[],
                                                    star_args=None, star_kwds=None))
    propigate_location(ir, set_gensyms)
    ir.expression = I.make_progn([set_gensyms, ir.expression])
    return ir


