
from __future__ import absolute_import
from __future__ import with_statement

import os
import sys
from subprocess import Popen

from jamenson.runtime.filepat import FilePath
from jamenson.compiler.util import timing

JMC_PATH = FilePath(os.path.expanduser('~/bin/jmc'))
assert JMC_PATH.exists()

build_order = '''
    bootstrap0
    backq
    bootstrap1
    ops
    cxr
    lambda
    iter
    cons
    symbol
    setf
    control
    import
    multimethod
    user
    core
'''.split()

def main():
    with timing() as t:
        for target in build_order:
            build(target)
    print 'build time', t.strtime

def build(path):
    print >>sys.stderr, 'building', path
    sys.stderr.flush()
    mypath = FilePath(__file__)
    path = mypath.sibling(path + '.jms')
    p = Popen(map(str, [JMC_PATH, '-vv', '--nocore', '-p', 'core', path]))
    r = p.wait()
    if r!=0:
        raise RuntimeError("command returned %s" % (r,))

__name__ == '__main__' and main()
