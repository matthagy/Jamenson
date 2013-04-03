
from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.compiler.declare
    exit()

from ..runtime.atypes import as_optimized_type, MemberType, typep
from ..runtime.struct import defstruct

optimize_value_t = as_optimized_type(MemberType(range(4)))

defstruct('OptimizationTradeoffs',
          ['speed',  1, optimize_value_t],
          ['safety', 3, optimize_value_t],
          ['debug',  2, optimize_value_t],
          ['space',  1, optimize_value_t],
          ['compile_speed', 0, optimize_value_t])

