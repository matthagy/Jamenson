'''declare default transformations
'''

from __future__ import absolute_import

from .state import register_transformation, register_transformation_set, add_default_transformation


from .marshal import transform_to_marshalable
from .globals import transform_global_symbol_use
from .preeval import replace_loadtimes
from .top import transform_to_top_expression
from .constant_reduction import handle_constants
from .constant_copy import insert_copy_constants
from .progn_flatten import flatten_progns

rt = register_transformation

def radt(name, func, *rules):
    register_transformation(name, func, *rules)
    add_default_transformation(name)

def after(name): return ['after', name]
def before(name): return ['before', name]

radt('as_top_expression', transform_to_top_expression)
radt('replace_loadtimes', replace_loadtimes, after('as_top_expression'))
radt('reduce_constants', handle_constants, after('replace_loadtimes'))
radt('insert_copy_constants', insert_copy_constants, after('reduce_constants'))
radt('global_symbol_use', transform_global_symbol_use, after('insert_copy_constants'))
rt('to_marshalable', transform_to_marshalable)
rt('flatten_progns', flatten_progns)
