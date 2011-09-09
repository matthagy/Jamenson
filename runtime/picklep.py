'''Determine if an object can be pickled.
'''


from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.runtime.picklep
    exit()

import sys
import types

from .multimethod import MultiMethod, defmethod
from .atypes import anytype
from .marshalp import iter_col_elements

# this has gotten too complicated, just force true check
import cPickle as pickle

def picklep(op):
    try:
        pickle.dumps(op)
        return True
    except (pickle.PicklingError, StandardError):
        return False


# picklep = MultiMethod('picklep',
#                        doc='''
#                        predicate to determine if an object is pickleable
#                        ''')


# #by default, not pickleable
# @defmethod(picklep, [anytype])
# def meth(op):
#     return False

# builtin_pickleable_types = set([
#     types.BooleanType,
#     types.ComplexType,
#     types.EllipsisType,
#     types.FloatType,
#     types.IntType,
#     types.LongType,
#     types.NoneType,
#     types.NotImplementedType,
#     types.SliceType,
#     types.StringType,
#     types.UnicodeType
#     ])

# builtin_nonpickleable_types = set([
#     types.BufferType,
#     types.BuiltinMethodType,
#     types.CodeType,
#     types.DictProxyType,
#     types.FileType,
#     types.FrameType,
#     types.GeneratorType,
#     types.GetSetDescriptorType,
#     types.MemberDescriptorType,
#     types.MethodType,
#     types.ModuleType,
#     types.TracebackType,
#     types.UnboundMethodType,
#     types.XRangeType
#     ])

# builtin_collections_types = set([
#     types.DictionaryType,
#     types.ListType,
#     types.TupleType,
#     type(set)
#     ])

# builtin_mayablepickleable_types = set([
#     types.BuiltinFunctionType,
#     types.ClassType,
#     types.FunctionType,
#     types.InstanceType,
#     types.LambdaType,
#     types.ObjectType,
#     types.TypeType,
#     ])

# builtin_types = builtin_pickleable_types | builtin_nonpickleable_types | \
#                 builtin_collections_types | builtin_mayablepickleable_types

# #always pickleable
# @defmethod(picklep, [tuple(builtin_pickleable_types)])
# def meth(op):
#     return True

# #never pickleable
# @defmethod(picklep, [tuple(builtin_nonpickleable_types)])
# def meth(op):
#     return False

# #collections
# composite_types = tuple(builtin_collections_types)
# @defmethod(picklep, [composite_types])
# def meth(col):
#     return pickleable_collection(col, set())

# def pickleable_collection(col, memo):
#     if id(col) in memo:
#         return True
#     memo.add(id(col))
#     for el in iter_col_elements(col):
#         if isinstance(el, composite_types):
#             if not pickleable_collection(el, memo):
#                 return False
#         elif not picklep(el):
#             return False
#     return True


# # old style classes
# @defmethod(picklep, [types.InstanceType])
# def meth(op):
#     return picklep(op.__class__) and picklep(op.__dict__)

# @defmethod(picklep, [types.ClassType])
# def meth(c):
#     return picklep_global(c, c.__module__, c.__name__)

# # new style classes
# @defmethod(picklep, [object])
# def meth(op):
#     cls = type(op)
#     has_getstate = hasattr(cls, '__getstate__')
#     if hasattr(cls, '__slots__'):
#         if not has_getstate:
#             pass
#     #objects are pickleable if they define a __getstate__ or don't have a __slots__
#     return ((not hasattr(cls, '__slots__') or hasattr(cls, '__getstate__')) and
#             picklep(cls))

# @defmethod(picklep, [type])
# def meth(tp):
#     return tp in builtin_types or picklep_global(tp, tp.__module__, tp.__name__)

# # functions
# @defmethod(picklep, [types.FunctionType])
# def meth(func):
#     return picklep_global(func, func.__module__, func.func_name)

# @defmethod(picklep, [types.BuiltinFunctionType])
# def meth(func):
#     return picklep_global(func, func.__module__, func.__name__)


# def picklep_global(op, module_name, op_name):
#     if module_name == '__main__':
#         return False
#     try:
#         module = sys.modules[module_name]
#     except KeyError:
#         return False
#     return getattr(module, op_name, None) is op


