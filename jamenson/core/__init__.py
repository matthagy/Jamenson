'''Core language functionality implemtned in Jamenson
'''

from __future__ import absolute_import
from __future__ import with_statement

from ..runtime.load import loadfile
from hlab.pathutils import FilePath

installed = False

def install():
    '''Load core.jms (or compiled version if available) to install core
    '''
    global installed
    if installed:
        return
    loadfile(FilePath(__file__).abspath().sibling('core'))
    installed = True
