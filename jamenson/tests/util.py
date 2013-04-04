
import unittest

from jamenson.runtime.filepath import FilePath,DirPath

def basepath():
    filebase = FilePath(__file__).abspath().stripext()
    backpath = __name__.replace('.','/')
    assert filebase.endswith(backpath)
    path = DirPath(filebase[:-len(backpath)])
    assert path.isdir()
    return path
basepath = basepath()

loader = unittest.TestLoader()

def load_file_tests(path):
    path = path.stripext()
    assert path.startswith(basepath)
    name = path[len(basepath)+1::].replace('/','.')
    mod = __import__(name, fromlist=name.rsplit('.',1)[-1:])
    return loader.loadTestsFromModule(mod)

def load_directory_tests(path, recursive=True):
    tests = []
    for p in DirPath(path):
        if p.isdir():
            if recursive:
                tests.extend(load_directory_tests(p, recursive=True))
        elif p.endswith('.py') and not p.basename().startswith('.'):
            tests.extend(load_file_tests(p))
    return tests

def test_directory(basefile):
    basefile = FilePath(basefile)
    assert basefile.basename().startswith('__init__.py')
    tests = unittest.TestSuite(load_directory_tests(basefile.abspath().parent()))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(tests)


