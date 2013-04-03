'''Extended Types
'''

from __future__ import absolute_import

from . import as_optimized_type, anytype, union, intersection, typep
from .ptypes import integer_type, none_type, number_type, scalar_number_type
from .accessors import HasAttr

__all__ = '''even_type odd_type
             zero_type positive_type negative_type
             recursions_type iterable_type
'''.split()


even_type = intersection(integer_type, lambda x : x%2==0)
odd_type = intersection(integer_type, lambda x : x%2==1)
zero_type = intersection(number_type, lambda x : x==0)
positive_type = intersection(scalar_number_type, lambda x: x>0)
negative_type = intersection(scalar_number_type, lambda x: x<0)

recursions_type = as_optimized_type((intersection(integer_type, positive_type),
                                     none_type))

#str has no __iter__ attribute, handle it with a monkey patch
iterable_type = union(HasAttr('__iter__'), str)

