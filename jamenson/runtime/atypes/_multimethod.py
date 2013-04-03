'''Multimethods (generic functions)
'''

from __future__ import absolute_import

import sys

from compiler import parse as py_compiler_parse
from compiler.ast import Keyword as AstKeyword

from ..bases import CachingBase
from ..collections import OrderedDict
from ..fakeatypes import (as_optimized_type, type_name, compose_types_scorer,
                          no_score, best_score, worst_score)

__all__ = '''MultiMethodError only before after around
             InconsistenCallSignature InvalidMethodArguments
             NoSuchMethod
             MultiMethod
             defmethod defboth_wrapper
             current_method
'''.split()

not_specified = object()

class MultiMethodError(Exception):
    pass


def parse_sig(sig, gbls=None, lcls=None):
    '''hideous hack to allow signatures to be defined as
           "int,int,c=str,d=object"
       ie.
          parse_sig("int,int,c=str,d=object") ->
             (int, int), [("c",str), ("d",object)]
       properly handles order of keywords
    '''
    callstr = '_parse_sig_func_(%s)' % sig
    co = compile(callstr, '<string>', 'eval')
    if gbls is None:
        gbls = dict()
    if lcls is None:
        lcls = {}
    lcls = gbls.copy()
    lcls['_parse_sig_func_'] = lambda *args, **kwds: (args,kwds)
    args,kwds = eval(co, gbls, lcls)
    ast = py_compiler_parse(callstr, mode='eval')
    kwds_order = [arg.name for arg in ast.node.args
                  if isinstance(arg, AstKeyword)]
    kwds = sorted(kwds.iteritems(),
                  key=lambda (name,_): kwds_order.index(name))
    return args, kwds


class InvalidCallArguments(Exception):

    def __init__(self, expected_sig, given_sig):
        self.expected_sig = expected_sig
        self.given_sig = given_sig

    def __str__(self):
        return 'bad call arguments %s for signature %s' % (self.given_sig, self.expected_sig)


class MethodSignature(CachingBase):

    __slots__ = ['nags','kwds']

    def _init_cached(self, nargs, kwds):
        self.nargs = nargs
        self.kwds = kwds

    @classmethod
    def get_key(cls, nargs, kwds):
        return int(nargs), tuple(kwds)

    @classmethod
    def from_sig_string(cls, s):
        callstr = 'func(%s)' % (s,)
        ast = py_compiler_parse(callstr, mode='eval')
        kwds = [arg.name for arg in ast.node.args
                if isinstance(arg, AstKeyword)]
        return cls(len(ast.node.args) - len(kwds), kwds)

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__,
                               self.nargs, self.kwds)

    def __str__(self):
        acc = ['arg%d' % i for i in xrange(self.nargs)]
        acc.extend('%s=' for s in self.kwds)
        return '(%s)' % ', '.join(acc)

    @classmethod
    def from_call(cls, args, kwds):
        return cls(len(args), kwds)

    def bad_call(self, args, kwds):
        raise InvalidCallArguments(self, self.from_call(args, kwds))

    def partition_call_vector(self, args, kwds):
        if not self.kwds:
            if len(args) != self.nargs or kwds:
                self.bad_call(args, kwds)
            return args
        return self.partition_call_vector_kwds(self, args, kwds)

    class no_kwd(object):
        def __repr__(self):
            return '<no-kwd>'
    no_kwd = no_kwd()

    @staticmethod
    def partition_call_vector_kwds(self, args, kwds):
        nargs = len(args)
        if nargs < self.nargs or nargs > self.nargs + len(self.kwds):
            self.bad_call(args, kwds)
        if kwds and not (set(kwds) <= set(self.kwds)):
            self.bad_call(args, kwds)
        call_vector = list(args)
        for kwd in self.kwds[nargs-self.nargs:]:
            call_vector.append(kwds.get(kwd, self.no_kwd))
        return call_vector

    def as_types_of_call_vector(self, vec, keyers, default):
        if not self.kwds:
            return tuple([typer(arg) for typer,arg in zip(keyers, vec)])
        return tuple([typer(arg) if arg is not self.no_kwd else default
                      for typer,arg in zip(keyers, vec)])

    def perform_call(self, vec, func):
        if not self.kwds:
            return func(*vec)
        return self.perform_call_kwds(self, vec, func)

    @staticmethod
    def perform_call_kwds(self, vec, func):
        no_kwd = self.no_kwd
        return func(*vec[:self.nargs],
                    **dict([(k,v) for k,v in zip(self.kwds, vec[self.nargs:])
                            if v is not no_kwd]))

    def type_sig_from_call_vector(self, vec):
        return TypeSignature(map(type, vec[:self.nargs]),
                             [(k,type(v)) for k,v in zip(self.kwds, vec[self.nargs:])
                              if v is not no_kwd])

def format_signature(args, kwds, format_value=repr):
    if isinstance(kwds, dict):
        kwds = kwds.iteritems()
    acc = map(format_value, args)
    acc.extend('%s=%s' % (name,format_value(tp))
               for name,tp in kwds)
    return '(%s)' % ', '.join(acc)


class CallSignature(object):

    def __init__(self, args, kwds):
        self.args = args
        self.kwds = kwds

    def __str__(self):
        return format_signature(self.args, self.kwds)

    @classmethod
    def from_call(cls, *args, **kwds):
        return cls(args, kwds)


class TypeSignature(CachingBase):

    __slots__ = ['args','kwds','types']

    def _init_cached(self, args, kwds):
        self.args = args
        self.kwds = kwds
        self.types = self.args + tuple(t for k,t in self.kwds)

    @classmethod
    def get_key(cls, args, kwds):
        return tuple(map(as_optimized_type, args)), tuple((k,as_optimized_type(t)) for k,t in kwds)

    @classmethod
    def from_sig_string(cls, s, *args, **kwds):
        return cls(*parse_sig(s, *args, **kwds))

    def __str__(self):
        return format_signature(self.args, self.kwds, type_name)

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__,
                               self.args, self.kwds)

    def calculate_method_signature(self):
        if not self.kwds:
            return MethodSignature(len(self.args), ())
        return MethodSignature(len(self.args),
                               [k for k,v in self.kwds])






# # # # # # # # # # # # # # # # #
# method combination compilers  #
# # # # # # # # # # # # # # # # #

class CombinationType(object):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

only,before,after,around = map(CombinationType, 'only before after around'.split())

combination_compilers = {}

def compile_only(mm, method, last_func):
    return method.func

combination_compilers[only] = compile_only

def missing_inner(mm, method):
    raise MultiMethodError("combination=%s %s with no inner method" %
                           (method.combination, mm.name))

def wrapper_fixup(mm):
    def wrap(func):
        func.func_name = mm.name
        return func
    return wrap

def compile_before(mm, method, last_func):
    if last_func is None:
        missing_inner(mm, method)
    before = method.func
    @wrapper_fixup(mm)
    def wrap(*args, **kwds):
        before(*args, **kwds)
        return last_func(*args, **kwds)
    return wrap

combination_compilers[before] = compile_before

def compile_after(mm, method, last_func):
    if last_func is None:
        missing_inner(mm, method)
    after = method.func
    @wrapper_fixup(mm)
    def wrap(*args, **kwds):
        op = last_func(*args, **kwds)
        after(*args, **kwds)
        return op
    return wrap

combination_compilers[after] = compile_after

def compile_around(mm, method, last_func):
    if last_func is None:
        missing_inner(mm, method)
    around = method.func
    @wrapper_fixup(mm)
    def wrap(*args, **kwds):
        return around(last_func, *args, **kwds)
    return wrap

combination_compilers[around] = compile_around


# # # # # # # # #
# multimethods  #
# # # # # # # # #

class Method(object):
    '''one method of definitive signiature and a corresponding function
       for a multimethods.  also contains a combination rule for
       combination with other methods
    '''

    __slots__ = ['type_sig','func','combination','scorers']

    def __init__(self, type_sig, func, combination):
        self.type_sig = type_sig
        self.func = func
        self.combination = combination


class InconsistenCallSignature(MultiMethodError):

    def __init__(self, mm, invalid_sig):
        self.mm = mm
        self.invalid_sig = invalid_sig

    def __str__(self):
        return 'invalid method signature %s for %s' % (self.invalid_sig, self.mm)


class InvalidMethodArguments(MultiMethodError):

    def __init__(self, mm, meth_sig):
        self.mm = mm
        self.meth_sig = meth_sig

    def __str__(self):
        return 'invalid arguments to %s; called with %s' % (self.mm, self.meth_sig)


class NoSuchMethod(MultiMethodError):

    def __init__(self, mm, call_sig):
        self.mm = mm
        self.call_sig = call_sig

    def __str__(self):
        return 'no such method for %s called with %s' % (self.mm, self.call_sig)

    def __repr__(self):
        return str(self)


def score_call_vector(scorers, call_key):
    acc = []
    for scorer,key in zip(scorers, call_key):
        if key is not_specified:
            score = worst_score
        else:
            score = scorer(key)
            if score is no_score:
                return score
        acc.append(score)
    #print 'score',self.type_sig,score
    return acc

class MultiMethod(object):
    '''
    '''

    def __init__(self, name='<multilambda>', doc='', signature=None,
                 default_combination=None, cache=True, inherit_from=()):
        self.name = name
        self.doc = doc
        self.methods = []
        if isinstance(signature, str):
            signature = MethodSignature.from_sig_string(signature)
        self.signature = signature
        self.default_combination = default_combination
        self.type_keyers = None
        self.all_methods = None
        self.scorers = {}
        self.callcache = dict() if cache else None
        for i_f in inherit_from:
            self.inherit_from(i_f)

    def __str__(self):
        return '%s%s' % (self.name, self.signature if self.signature else '<unspecified>')

    def __call__(self, *args, **kwds):
        if not self.type_keyers:
            self.build_type_keys()
        self.get_signature()
        try:
            call_vector = self.signature.partition_call_vector(args, kwds)
        except InvalidCallArguments,e:
            raise InvalidMethodArguments(self, e.given_sig)
        call_key = self.signature.as_types_of_call_vector(call_vector, self.type_keyers, not_specified)
        if self.callcache is None:
            func = self.calculate_method(call_key)
        else:
            try:
                func = self.callcache[call_key]
            except KeyError:
                func = self.callcache[call_key] = self.calculate_method(call_key)
            except TypeError:
                #unhashable key, go direct
                func = self.calculate_method(call_key)
        return self.signature.perform_call(call_vector, func)

    inherts_from_port = None
    inherts_to_port = None
    def inherit_from(self, parent):
        if self.inherts_from_port is None:
            from jamenson.runtime.ports import PortList, connect
            self.inherts_from_port = PortList(self)
        parent.inherts_to(self)

    def inherts_to(self, child):
        from jamenson.runtime.ports import PortList, connect
        if self.inherts_to_port is None:
            self.inherts_to_port = PortList(self)
        connect(self.inherts_to_port, child.inherts_from_port)

    def register_method(self, typesig, func, combination):
        methsig = typesig.calculate_method_signature()
        if not self.signature:
            self.signature = methsig
        elif methsig is not self.signature:
            raise InconsistenCallSignature(self, methsig)
        self.methods.append(Method(typesig, func, combination))
        self.invalidate()

    def invalidate(self):
        if self.callcache:
            self.callcache.clear()
        self.type_keyers = None
        self.all_methods = None
        if self.inherts_to_port:
            from jamenson.runtime.ports import get_cells
            for child in get_cells(self.inherts_to_port):
                child.invalidate()

    def build_type_keys(self):
        self.all_methods = self.get_all_methods()
        if not self.all_methods:
            raise MultiMethodError("no methods defined for %s" % (self.name))
        argument_types = zip(*[meth.type_sig.types for meth in self.all_methods])
        keyers_and_scorers = map(compose_types_scorer, argument_types)
        self.type_keyers,scorers = zip(*keyers_and_scorers)
        meths_scorers = zip(*scorers)
        for method,meth_scorers in zip(self.all_methods, meths_scorers):
            self.scorers[method] = meth_scorers

    def get_signature(self):
        if self.signature is None:
            if self.inherts_from_port is None:
                raise RuntimeError("no methods defined")
            from jamenson.runtime.ports import get_cells
            for parent in get_cells(self.inherts_from_port):
                if self.signature is None:
                    self.signature = parent.get_signature()
                elif self.signature is not parent.signature:
                    raise InconsistenCallSignature(self, parent.signature)
        return self.signature

    def get_all_methods(self):
        if self.all_methods is not None:
            return self.all_methods
        meths = self.methods
        if self.inherts_from_port is not None:
            from jamenson.runtime.ports import get_cells
            for parent in get_cells(self.inherts_from_port):
                meths = parent.get_all_methods() + meths
        self.all_methods = meths
        return meths

    def calculate_method(self, call_key):
        applicable_methods = []
        for meth in self.all_methods:
            score = score_call_vector(self.scorers[meth], call_key)
            if score is not no_score:
                applicable_methods.append([meth,score])
        if not applicable_methods:
            return self.no_applicable_methods_call(call_key)
        applicable_methods.reverse()
        applicable_methods.sort(key=lambda (meth,score): score) #rellies on Python's stable sorts
        return self.build_method_combination(meth for meth,score in applicable_methods)

    def no_applicable_methods_call(self, call_key):
        call_sig = self.signature.perform_call(call_key, CallSignature.from_call)
        error = NoSuchMethod(self, call_sig)
        def wrapper(*args, **kwds):
            raise error
        return wrapper

    def build_method_combination(self, methods):
        last_func = None
        for method in reversed(list(methods)):
            try:
                compiler = combination_compilers[method.combination]
            except KeyError:
                raise RuntimeError("unhandled combination %s" % method.combination)
            else:
                last_func = compiler(self, method, last_func)
        #last_func.func_name = self.name
        #last_func.func_doc = self.doc
        return last_func


def defmethod(mm, sig, combination=None, ns=None):
    if combination is None:
        combination = mm.default_combination
    if combination is None:
        combination = only
    def wrapper(func):
        xsig = sig
        if isinstance(xsig, str):
            f = sys._getframe(1)
            xsig = TypeSignature.from_sig_string(sig, f.f_globals if ns is None else ns, f.f_locals)
        elif isinstance(xsig, (list,tuple)):
            xsig = TypeSignature(xsig, {})
        assert isinstance(xsig, TypeSignature), 'bad typesig %s' % (xsig,)
        mm.register_method(xsig, func, combination)
        return func
    return wrapper

def defboth_wrapper(mm, sig, stack_depth=1, combination=None):
    '''Many two element method definitions are agnostic to the order of the
       arguments; only the type semantic matter.  This defines both types of
       combinations of two arguments (when they are different) to handle such
       cases easily.
    '''
    if isinstance(sig, str):
        f = sys._getframe(stack_depth)
        args,kwds = parse_sig(sig, f.f_globals, f.f_locals)
        assert not kwds
    else:
        args = sig
        kwds = {}
    assert len(args)==2
    if combination is None:
        combination = mm.default_combination
    if combination is None:
        combination = only
    def wrapper(func):
        mm.register_method(TypeSignature(args, kwds), func, combination)
        if args[0] != args[1]:
            mm.register_method(TypeSignature(args[::-1], kwds), lambda a,b: func(b,a), combination)
        return func
    return wrapper

def current_method():
    f = sys._getframe()
    while f:
        if f.f_code.co_name == '__call__' and 'self' in f.f_locals:
            self = f.f_locals['self']
            if isinstance(self, MultiMethod):
                return self
        f = f.f_back
    raise MultiMethodError("MultiMethod instance not found in call stack")

