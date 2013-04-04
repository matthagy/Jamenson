'''Jamenson Interperator
'''

from __future__ import absolute_import
from __future__ import with_statement

import sys

from ..runtime import load
from ..runtime.filepath import FilePath
from ..runtime.compiled import compile_source_ex
from .jmbase import JMBase

def main():
    JMS().main()

class JMS(JMBase):

    def process_target_in_package(self, target):
        eval(self.get_stdin_code() if target=='-' else self.get_file_code(target))

    def get_stdin_code(self, target):
        return compile_source_ex('<stdin>', sys.stdin)

    def get_file_code(self, path):
        path = FilePath(path)
        if not path.exists():
            self.err('no such file %s', path)
        return load.get_code(path)

