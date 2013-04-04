'''
'''

from __future__ import absolute_import

import __builtin__
import tempfile
from contextlib import contextmanager, closing
from random import randrange

from .filepath import FilePath, DirPath


@contextmanager
def temporary_file(*args, **kwds):
    tmp_path = FilePath(tempfile.mktemp(*args, **kwds))
    try:
        yield tmp_path
    finally:
        tmp_path.unlink_carefully()

@contextmanager
def temporary_directory(*args, **kwds):
    tmp_path = DirPath(tempfile.mktemp(*args, **kwds))
    tmp_path.reqdir()
    try:
        yield tmp_path
    finally:
        tmp_path.rmdir_carefully(recursive=True)


rnd_holder = '<RND>'

@contextmanager
def temp_file_proxy(path, mode='w', tmp_suffix = '~tmp~%s~' % rnd_holder, open=__builtin__.open, **kwds):
    path = FilePath(path)

    if rnd_holder not in tmp_suffix:
        tmp_path = FilePath(path + tmp_suffix)
    else:
        while True:
            assert tmp_suffix.count(rnd_holder) == 1
            rnd_tmp_suffix = tmp_suffix.replace(rnd_holder, '%X' % randrange(0xffffffff))
            tmp_path = FilePath(path + rnd_tmp_suffix)
            if not tmp_path.exists():
                break

    if tmp_path.exists():
        raise RuntimeError("temporary file %s already exists" % (tmp_path,))

    try:
        with closing(open(tmp_path, mode, **kwds)) as fp:
            yield fp
        tmp_path.rename(path)
    finally:
        tmp_path.unlink_carefully()
