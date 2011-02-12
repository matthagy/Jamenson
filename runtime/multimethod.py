'''Multimethods (generic functions)

   Loads core compiled multimethods when available (not yet implemented),
   otherwise use atypes boostrapping procedure to create an atypes aware
   multimethod implementation.
'''

def load(name):
    '''Code has to run with locals scope, as globals are trashed in the
       the boostrapping process.
    '''
    if name == '__main__':
        #don't run as main
        import jamenson.runtime.multimethod
        return
    if 0:
        import sys
        from jamenson import core
        if not core.dummy:
            #attempt to use core when available
            sys.modules[name] = core.moudles.runtime.multimethod
            return
    #import atypes for bootstrapping, has side effect of loading multimethods
    import jamenson.runtime.atypes

load(__name__)
