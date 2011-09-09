'''Utilities for dealing with compiled code
'''

from __future__ import absolute_import
from __future__ import with_statement

import marshal
from types import CodeType

from hlab.tempfile import temp_file_proxy
from .require import files_search_path

#unique 8 byte identification of compiled jamenson source code
magic_numbers = [0xEC, 0xE0, 0xF3, 0xF3, 0xE7, 0xE0, 0xE6, 0xF8]
magic_bytes = ''.join(map(chr, magic_numbers))

def write_code(code, path):
    assert isinstance(code, CodeType)
    with temp_file_proxy(path, 'wb') as fp:
        dump_code(code, fp)

def dump_code(code, fp):
    fp.write(magic_bytes)
    marshal.dump(code, fp)

def read_code(path):
    with open(path, 'rb') as fp:
        start = fp.read(len(magic_bytes))
        if start != magic_bytes:
            raise IOError('invalid file head; %r expected %r' % (start, magic_bytes))
        return marshal.load(fp)

def compile_source(path, bytes=None, enable_marshal_transform=False):
    '''default compiler
    '''
    with files_search_path(path):
        return compile_source_ex(path, bytes, enable_marshal_transform)

def compile_source_ex(path, bytes=None, enable_marshal_transform=False):
    #import for side effects needed for code evaluation
    from . import builtins
    #defer loading compiler if not needed
    from ..compiler.block import BlockCompiler
    compiler = BlockCompiler.create(filename=path, bytes=bytes)
    compiler.enable_marshal_transform = enable_marshal_transform
    return compiler.construct_code()
