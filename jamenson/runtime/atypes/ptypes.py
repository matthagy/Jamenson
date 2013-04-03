'''Python Types
'''

from __future__ import absolute_import

import new

from . import as_optimized_type, anytype, union, intersection, typep

__all__ = '''none_type ellipsis_type integer_type scalar_number_type
             number_type string_type atomic_type set_type collection_type
             code_type function_type marshal_type'''.split()


none_type = as_optimized_type(type(None))
ellipsis_type = as_optimized_type(type(Ellipsis))
integer_type = as_optimized_type((int,long))
scalar_number_type = as_optimized_type((int,long,float))
number_type = as_optimized_type((scalar_number_type, complex))
string_type = as_optimized_type((str,unicode))
atomic_type = as_optimized_type((number_type, string_type,
                                 bool, none_type, ellipsis_type))
set_type = as_optimized_type((set,frozenset))
collection_type = as_optimized_type((tuple, list, dict, set_type))
code_type = as_optimized_type(new.code)
function_type = as_optimized_type(new.function)
marshal_type = as_optimized_type((atomic_type, collection_type, code_type))


