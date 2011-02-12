
from jamenson.runtime.atypes import *
from jamenson.runtime.multimethod import *

odd_int_t = as_optimized_type(intersection(union(int,long), lambda x: x%2==1))

print typep(7, odd_int_t)
print typep(6L, odd_int_t)
print typep("adafd", odd_int_t)

py_numbers = as_optimized_type((int,long,float,complex))
sequence_t = as_type(lambda op: hasattr(op, "__iter__"))
py_number_seq = intersection(sequence_t, lambda op: all(typep(el, py_numbers) for el in op))

print py_number_seq

print typep(3, py_numbers)
print typep(range(3), sequence_t)
print typep(range(3), py_number_seq)
print typep("adfadf", py_number_seq)
print typep([2,23,334,324.342], py_number_seq)
