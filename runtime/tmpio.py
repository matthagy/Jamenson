
from __future__ import absolute_import
from __future__ import with_statement

import warnings

from hlab.tempfile import temp_file_proxy as hlab_temp_file_proxy

def temp_file_proxy(*args, **kwds):
    warnings.warn("temp_file_proxy is deprecated; moved to hlab.tempfile",
                  DeprecationWarning, stacklevel=2)
    return hlab_temp_file_proxy(*args, **kwds)


