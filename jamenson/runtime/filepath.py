from __future__ import absolute_import

import sys
import os
import pwd
import grp
import re
import shutil
import errno
from glob import iglob


#Exceptions
class MissingFile(Exception):

    def __init__(self, path):
        self.path = path
        msg = 'Missing file %s' % path
        error.__init__(self, msg)

class MissingDir(MissingFile):

    def __init__(self, path):
        self.path = path
        msg = 'Missing directory %s' % path
        error.__init__(self, msg)

pth = os.path
pathsep = pth.sep
pathjoin = pth.join
pathsplit = pth.split
pathsplitext = pth.splitext
pathexists = pth.exists
isabspath = pth.isabs
for i in ['abspath','dirname','basename',
          'isfile','isdir','islink','ismount',
          'normpath','realpath']:
      globals()[i] = getattr(pth,i)
del pth

def stripext(path):
    return pathsplitext(path)[0]

def chown(path, user=None, group=None):
    '''Chown that defaults to files current owner/group
       and can accept string agruments performing
       necessary lookups
    '''
    if None in (user,group):
        s = os.stat(path)
        if user is None:
            user = s.st_uid
        if group is None:
            group = s.st_gid
    if type(user) is str:
        user = pwd.getpwnam(user).pw_uid
    if type(group) is str:
        for name,_,gid,_ in grp.getgrall():
            if name == group:
                group = gid
                break
        else:
            raise ValueError('Unkown group %r' % (group,))
    os.chown(path, user, group)

def chgrp(path, group):
    chown(path, user=None, group=None)

def chmod(path, *args):
    '''chmod that can take special format directes (same as unix chmod)
       Format <WHO><ADD/SUB><WHAT>
       For instance:
            u+x User add execute
            -w All types minus write
            ug+rw User group add read write
            ug+r-w User group add read write, remove write
    '''
    if len(args) == 1 and type(args[0]) in [int,long]:
        mode = int(args[1])
    else:
        mode = _chmod_parse(os.stat(path).st_mode, args)
    os.chmod(path, mode)

_chmod_rgx = re.compile('([augo]*)((?:[+-][wrx]+)+)')
_chmod_arg_rgx = re.compile('([+-])([wrx]+)')

def _chmod_parse(mode, args):
    actions = {}
    args = ' '.join(args).split()
    for arg in args:
        try:
            m = _chmod_rgx.match(arg)
            if m is None:
                raise ValueError
            who,action = m.groups()
            if not who:
               who = 'a'
            actlist = _chmod_arg_rgx.findall(action)
            if not actlist:
                raise ValueError
            who = who.replace('a','uog')
            for w in who:
                try:
                    act = actions[w]
                except KeyError:
                    act = actions[w] = {}
                for addsub,privs in actlist:
                    for p in privs:
                        act[p] = addsub
        except ValueError:
            raise ValueError('bad chmod arg %r' % (arg,))
    md = {'o': mode & 07,
          'g' : (mode & 070) / 010,
          'u' : (mode & 0700) / 0100}
    actm = {'x':01,'w':02,'r':04}
    for who,acts in actions.iteritems():
         for priv,addsub in acts.iteritems():
             num = actm[priv]
             if addsub == '+':
                 md[who] |= num
             else:
                 md[who] = (~num) & num
    newmode = md['o'] + md['g']*010 + md['u']*0100
    return newmode


class BasePath(str):
    '''a path that is not tied to the file system'''

    def __new__(cls, filepath, relative=None):
        if isinstance(filepath, cls):
            return filepath
        if isinstance(filepath, unicode):
            filepath = filepath.encode()
        if not isinstance(filepath, str):
            raise TypeError("cannot create %s instance from %s" % (cls.__name__, filepath))
        filepath = normpath(filepath)
        return str.__new__(cls, filepath)

    def __init__(self, filepath, relative=None):
        if relative is None:
            relative = not isabspath(filepath)
        self.relative = relative

    def __repr__(self):
        return '%s(%s, relative=%r)' % (
                self.__class__.__name__,
                str.__repr__(self),
                self.relative)

    __str__ = str.__str__

    def dirname(self):
        return dirname(self)

    def dirpath(self):
        return self._dir_class(self.dirname())

    def basename(self):
        return basename(self)
    def extension(self):
        return pathsplitext(self)[-1]
    def hasExtension(self, *exts):
        return pathsplitext(self)[-1] in exts
    def stripext(self):
        return self.__class__(stripext(self))

    def parent(self, depth=None, klass=None):
        if klass is None:
            klass = self._dir_class
        if depth is not None:
            if type(depth) not in [int, long]:
                raise TypeError('depth must be an int')
            if depth < 0:
                raise ValueError('depth must be positive')
            if depth == 0:
                return self
        p,_ = pathsplit(self)
        if self == p:
            raise ValueError('path has no parent; root directory')
        p = klass(p, relative=self.relative)
        if depth:
            return p.parent(depth-1)
        return p

    def fragment(self, relative_to=None):
        if relative_to is None:
            relative_to = os.getcwd()
        relative_to = self._dir_class(relative_to).abspath()
        path = self.abspath() if self.relative else self

        assert path.startswith(relative_to)
        return self.__class__(path[len(relative_to)+1::])

BasePath._dir_class = BasePath

class FilePath(BasePath):
    '''Adds in file system code'''

    def exists(self):
        return pathexists(self)
    def size(self):
        return os.path.getsize(self)

    def isabs(self):
        return isabspath(self)
    def isfile(self):
        return isfile(self)
    def isdir(self):
        return isdir(self)

    def atime(self):
        return os.path.getatime(self)
    def ctime(self):
        return os.path.getctime(self)
    def mtime(self):
        return os.path.getmtime(self)

    def newer_than(self, other):
        if not isinstance(other, FilePath):
            other = FilePath(other)
        try:
            return self.mtime() > other.mtime()
        except OSError:
            return False

    def abspath(self):
        if not self.relative:
            return self
        return self.__class__(abspath(self), relative=False)

    def unlink(self):
        os.unlink(self)

    def unlink_carefully(self, raise_exc=False):
        """Unlink a file in an environment where other processes may be trying to
           unlink same file
        """
        try:
            self.unlink()
        except OSError, e:
            if e.errno != errno.ENOENT:
                if raise_exc:
                    raise
                else:
                    pass
                    #msg('failed to unlink file %s: %s', self, e)

    def rename(self, name):
        os.rename(self, name)

    def chown(self, user=None, group=None):
        chown(self, user, group)

    def chmod(self, *args):
        chmod(self, *args)

    def requireexists(self):
        if not self.exists():
            raise MissingFile(self)

    def sibling(self, basename):
        return self.parent().child(basename)
    def fsibling(self, basename):
        return self.parent().fchild(basename)
    def dsibling(self, basename):
        return self.parent().dchild(basename)

    def open(self, flags='r'):
        return open(self, flags)

    def touch(self, times=None):
        with file(self, 'a'):
            os.utime(self, times)

class DirPath(FilePath):

    def child(self, jpath, klass=None):
        if isabspath(jpath):
            raise ValueError("shouldn't use %r.child for "
                            "absolute paths (%r)" %
                            (self.__class__.__name__,jpath))
        path = pathjoin(self, jpath)
        if klass is None:
            if isdir(path):
                klass = self.__class__
            else:
                klass = self._file_class
        return klass(path, relative=self.relative)

    def fchild(self, jpath):
        return self.child(jpath, klass=self._file_class)
    def dchild(self, jpath):
        return self.child(jpath, klass=self.__class__)

    def listdir(self):
        return map(self.child, os.listdir(self))

    def __contains__(self, fn):
        return fn in os.listdir(self)

    def mkdir(self, recursive=False, mode=0777):
        mkdir = [os.mkdir, os.makedirs][bool(recursive)]
        mkdir(self, mode)

    def reqdir(self):
        if not self.exists():
            self.mkdir(recursive=True)

    def safely_reqdir(self):
        """Create directory in an environment where other processes may be trying to
           create same directory
        """
        try:
            self.reqdir()
        except OSError,e:
            if e.errno != errno.EEXIST:
                raise

    def rmdir(self, recursive=False):
        rmdir = [os.rmdir, shutil.rmtree][bool(recursive)]
        rmdir(self)

    def rmdir_carefully(self, recursive=False, raise_exc=False):
        """Unlink a file in an environment where other processes may be trying to
           unlink same file
        """
        try:
            self.rmdir(recursive=recursive)
        except OSError, e:
            if e.errno != errno.ENOENT:
                if raise_exc:
                    raise
                else:
                    msg('failed to rmdir %s: %s', self, e)

    def itercontents(self, recursive=False):
        for path in self.listdir():
            yield path
            if recursive and path.isdir():
                for i in path.itercontents(True):
                    yield i

    def __iter__(self):
        return self.itercontents()

    def glob(self, pattern):
        for path in iglob(self + pathsep + pattern.lstrip(pathsep)):
            yield self._dir_class(path) if isdir(path) else self._file_class(path)


FilePath._dir_class = DirPath
DirPath._file_class = FilePath

