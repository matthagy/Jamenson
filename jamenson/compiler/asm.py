'''Assembly (byte code) utilities
'''

from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.compiler.asm
    exit()

import byteplay as B

from .util import collect_list
from ..runtime import ore as O


def finalize_instructions(ops):
    ops = fix_set_lineno(ops)
    if not (ops and ops[-1][0] == B.RETURN_VALUE):
        ops.append((B.RETURN_VALUE, None))
    return ops

@collect_list
def fix_set_lineno(ops):
    '''ensure SetLinenos are monotonically increasing, and remove extras
    '''
    lastLineno = None
    for op,arg in ops:
        if op is not B.SetLineno:
            yield op,arg
        # (number > None) is always True
        elif arg > lastLineno:
            lastLineno = arg
            yield op,arg

def first_lineno(ops):
    for op,arg in ops:
        if op is B.SetLineno:
            return arg
    return None

optimizations = []

def optimization(func):
    optimizations.append(func)
    return func

def optimize_instructions(ops):
    '''peep hole optimizations on operations (no global analysis)
    '''
    for optimization in optimizations:
        ops = optimization(ops)
    return ops

@optimization
@collect_list
def dead_code_elimination(ops):
    '''eliminate anything after unconditional jumps until label
    '''
    ujumps = B.JUMP_FORWARD, B.JUMP_ABSOLUTE
    itr = iter(ops)
    for op,arg in itr:
        yield op,arg
        if op in ujumps:
            for op,arg in itr:
                if isinstance(op, B.Label):
                    yield op,arg
                    break

@optimization
def shortcut_jumps(ops):
    '''find jumps that land on other jumps and use last jump
    '''
    #Not yet implemented
    return ops

#ore to match a bytecode operation
def Op(type, arg=None):
    return O.Seq(O.Eq(type) if not isinstance(type, O.MatchBase) else type,
                 O.succeed if arg is None else arg)

def replacer(pattern):
    if isinstance(pattern, list):
        pattern = O.Seq(*pattern)
    pattern = O.as_ore(pattern)
    if not isinstance(pattern, (O.Seq, O.Or)):
        pattern = O.Seq(pattern)
    if isinstance(pattern, O.Seq):
        pattern = O.Or(pattern)
    assert isinstance(pattern, O.Or)
    for child in pattern.children:
        assert isinstance(child, O.Seq)
    def inner(func):
        def run(ops):
            return list(O.replace_one_of(pattern.children, func, ops))
        return run
    return inner


# # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                 reverse not jumps logic               #
#-------------------------------------------------------#
# replace [NOT, JUMP_IF_FALSE] with [JUMP_IF_TRUE] and  #
#         [NOT, JUMP_IF_TRUE]  with [JUMP_IF_FALSE]     #
#-------------------------------------------------------#

reverse_condition_jumps_ore = [
    Op(B.UNARY_NOT),
    Op(O.Save("op", O.Or(O.Eq(B.JUMP_IF_FALSE),
                         O.Eq(B.JUMP_IF_TRUE))),
       O.Save("label"))]

reverse_condition_jumps_map = {B.JUMP_IF_FALSE : B.JUMP_IF_TRUE,
                               B.JUMP_IF_TRUE  : B.JUMP_IF_FALSE}

@optimization
@replacer(reverse_condition_jumps_ore)
def reverse_not_jumps_logic(match):
    yield [reverse_condition_jumps_map[match.load('op')], match.load('label')]


# # # # # # # # # # # # # # # # # # # #
#          reverse is logic           #
#-------------------------------------#
# replace [NOT, IS] with [IS_NOT] and #
#         [NOT, IS_NOT] with [IS]     #
#-------------------------------------#

reverse_is_logic_ore = [
    Op(B.UNARY_NOT),
    Op(B.COMPARE_OP,
       O.Save("compare", O.Or(O.Eq('is'), O.Eq('isnot'))))]

reverse_is_logic_map = {'isnot' : 'is',
                        'is'    : 'isnot'}

@optimization
@replacer(reverse_is_logic_ore)
def reverse_is_logic(match):
    yield B.COMPARE_OP, reverse_is_logic[match.load('compare')]


# # # # # # # # # # # # # # # # # # # # # # # # # # #
#               simplify_redundant_loads            #
#---------------------------------------------------#
# replace [STORE x, LOAD x] with [DUPTOP, STORE x]  #
#---------------------------------------------------#

simplify_redundant_loads_ore = \
        O.Or(*(O.Seq(O.Save('op', Op(store, O.Save('arg'))),
                                  Op(load, O.Eq(O.Load('arg'))))
               for store,load in [[B.STORE_FAST, B.LOAD_FAST],
                                  [B.STORE_DEREF, B.LOAD_DEREF]]))

@optimization
@replacer(simplify_redundant_loads_ore)
def simplify_redundant_loads(match):
    '''replace [STORE x, LOAD x] with [DUPTOP, STORE x]
    '''
    op,arg = match.loads('op', 'arg')
    yield B.DUP_TOP, None
    yield op
