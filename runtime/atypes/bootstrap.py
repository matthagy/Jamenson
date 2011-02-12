'''
Bootstrapping of atypes and multimethod.
These two modules are cyclicly dependent and thereby require a
boostrapping procedure to get everything online.
'''

from __future__ import absolute_import

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Boostrapping Process
# ---------------------------------------------------------------------------------
# To remove the cyclic dependencies of multimethods and atypes, we use
# the atypes.cold module to define a similar, less complete, types system.
# This coldatypes system is used to create a cold multimethods system.
# with this we then load the true atypes and define the atype system using the
# cold multimethods.  This results in the warmatypes system, which is a complete
# atype system.  This is used to create the true (hot) multimethods with the
# full type system. The final stage is rebuilding atype using the hot
# multimethods.
#
# It is import to note that we need to save references to all temporary
# modules.  When references are lost, the globals are cleared, rendering
# any functions in them useless.  We still need these functions as the
# hot systems are built on top of the warm and cold systems.
# ---------------------------------------------------------------------------------


def bootstrap():
    '''code has to run with locals scope, as globals are
       trashed in the the boostrapping process.
    '''
    verbose = 0

    from sys import stderr
    from time import time as clock
    from ..modulemagic import impmod, delmod, setmod
    from ..util import strtime

    # Preload following modules so their time isn't included in load time below
    import compiler
    import compiler.ast
    from .. import bases
    from .. import collections
    from . import common
    del compiler, bases, collections, common

    # Module names used in bootstrapping process
    base_name = 'jamenson.runtime'
    coldat_name = base_name + '.atypes.cold'
    mm_name = base_name + '.multimethod'
    at_name = base_name + '.fakeatypes'
    mm_cold_name = base_name + '.atypes._multimethod'
    at_cold_name = base_name + '.atypes._atypes'
    final_at_name = base_name + '.atypes'

    # Timing of bootstrapping stages
    def note(msg):
        tm = clock()
        print >>stderr, '%-18s %-8s (%s)' % (msg, strtime(tm-last[-1]), strtime(tm-start))
        last.append(tm)
    if not verbose:
        from operator import truth as note #simplest builtin nop function
    start = clock()
    last = [start]

    # Save atypes module that will hold all final memebers
    _atypes_ = impmod(final_at_name)

    # Use cold atypes to bootstrap a cold multimethod
    coldatypes = impmod(coldat_name)
    note('cold atypes')
    setmod(at_name, coldatypes)
    coldmultimethod = impmod(mm_cold_name)
    setmod(mm_name, coldmultimethod)
    coldmultimethod.__cold__ = True
    note('cold multimethod')

    # Load full atypes using the cold multimethod.
    # System isn't fully functional, as additional multimethod extensions to
    # this atypes systems can't used the full atypes functionallity.
    # Therefore this atypes systems is refererred to as warm.
    delmod(at_cold_name)
    delmod(at_name)
    warmatypes = impmod(at_cold_name)
    note('warm atypes')
    setmod(at_name, warmatypes)

    # Load hot multimethod with warm atypes.
    # After this stage, multimethods are fully functional with the ability to use all of
    # the atypes system.
    delmod(mm_cold_name)
    delmod(mm_name)
    multimethod = impmod(mm_cold_name)
    multimethod.__cold__ = False
    assert multimethod is not coldmultimethod
    multimethod.coldmultimethod = coldmultimethod
    setmod(mm_name, multimethod)
    note('hot multimethod')

    # Rebuild atypes with hot multimethods
    delmod(at_cold_name)
    delmod(at_name)
    atypes = impmod(at_cold_name)
    setmod(at_name, atypes)
    atypes.coldatypes = coldatypes
    atypes.warmatypes = warmatypes
    vars(_atypes_).update(vars(atypes))
    _atypes_._x_atypes = atypes
    setmod(final_at_name, _atypes_)
    atypes.hack_to_reoptimize_all_method_types()
    note('hot atypes')

    # Load atypes extensions that are dependent on full atypes systems
    from . import extensions
    for name in dir(extensions):
        if not hasattr(_atypes_, name):
            setattr(_atypes_, name, getattr(extensions, name))
    atypes.hack_to_reoptimize_all_method_types()
    atypes.__all__ += extensions.__all__
    note('extensions')

    # Replace warm atypes functionality with hot atypes
    warmatypes.get_type_keyer = atypes.get_type_keyer
    warmatypes.get_key_scorer = atypes.get_key_scorer
    warmatypes.compose_types_scorer = atypes.compose_types_scorer
    warmatypes.keyer_getfunc = atypes.keyer_getfunc
    warmatypes.as_type = atypes.as_type
    vars(_atypes_).update(vars(atypes))
    atypes.hack_to_reoptimize_all_method_types()
    note('heated warm')
