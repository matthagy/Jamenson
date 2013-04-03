'''Algebric Type System

   This is a wrapper module that attempts to load the
   pre-compiled version from core (not yet implemented),
   reverting back to the python version when not available.

   See bootstrap.py for a discussion of the cyclic dependencies
   between multimethod and atypes, as well as how this is handled.
'''

from __future__ import absolute_import

def load(name):
    '''Code has to run with locals scope, as globals are trashed in the
       the boostrapping process.
    '''
    if name == '__main__':
        #don't run as main
        import jamenson.runtime.atypes
        return
    if 0:
        import sys
        from jamenson import core
        if not core.dummy:
            #attempt to use core when available
            sys.modules[name] = core.modules.runtime.atypes
            return
    from .bootstrap import bootstrap
    bootstrap()

load(__name__)
