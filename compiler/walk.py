'''IR code walker
'''

from __future__ import absolute_import

import itertools

from . import ir as I


class IRWalker(object):
    '''depth first (by default) code walker
    '''

    def __init__(self):
        self.dispatch_table = {}

    def visit(self, node):
        if node is not None:
            return self.get_dispatcher(node.__class__)(node)

    def visit_children(self, node):
        for child in I.iter_children(node):
            self.visit(child)
        return node

    def get_dispatcher(self, cls):
        try:
            return self.dispatch_table[cls]
        except KeyError:
            #dispatch over first handled subclasses in method resolution order
            for c in cls.mro():
                try:
                    meth = getattr(self, 'visit_' + c.__name__)
                except AttributeError:
                    pass
                else:
                    #can shadow base visitors with None
                    if meth is not None:
                        break
            else:
                raise RuntimeError("%s can't visit %s" %
                                   (self.__class__.__name__,
                                    cls.__name__))
            self.dispatch_table[cls] = meth
            return meth

    #default visitor
    def visit_node(self, node):
        return self.visit_children(node)

    #rarely do we ever want to descend_into_functions
    descend_into_functions = False

    def visit_function(self, node):
        if self.descend_into_functions:
            return self.visit_node(node)


class Flagger(IRWalker):

    def __init__(self, attr, value, descend_into_functions=False):
        IRWalker.__init__(self)
        self.attr = attr
        self.value = value
        self.descend_into_functions = descend_into_functions

    def visit_node(self, node):
        setattr(node, self.attr, self.value)
        self.visit_children(node)

def flag_tree(ir, attr, value=True, descend_into_functions=False):
    Flagger(attr, value, descend_into_functions).visit(ir)


class ReducingWalker(IRWalker):

    def __init__(self, reducer):
        super(ReducingWalker, self).__init__()
        self.reducer = reducer

    def visit_children(self, node):
        #use imap for early exit
        return self.reducer(itertools.imap(self.visit, I.iter_children(node)))


class LogicWalker(ReducingWalker):

    def __init__(self, predicate, logic, descend_into_functions=False):
        assert logic is any or logic is all
        super(LogicWalker, self).__init__(logic)
        self.predicate = predicate
        self.descend_into_functions = descend_into_functions

    def visit_node(self, node):
        if self.predicate(node):
            if self.reducer is any:
                return True
        elif self.reducer is all:
            return False
        return self.visit_children(node)

def any_node(predicate, node, descend_into_functions=False):
    return LogicWalker(predicate, any, descend_into_functions).visit(node)

def all_nodes(predicate, node, descend_into_functions=False):
    return LogicWalker(predicate, all, descend_into_functions).visit(node)

def contains(obj, node, descend_into_functions=False, test=None):
    return any_node((lambda node: test(node, obj))
                    if test else
                    (lambda node: node==obj), node, descend_into_functions)

def contains_type(tp, node, descend_into_functions=False):
    return any_node(lambda node: isinstance(node, tp), node, descend_into_functions)


class LocationPropigator(IRWalker):

    descend_into_functions = True

    def __init__(self, original_node, skips=[]):
        IRWalker.__init__(self)
        self.original_node = original_node
        self.skips = set(skips)

    def visit_node(self, node):
        if node in self.skips:
            return
        I.copy_loc(node, self.original_node)
        self.visit_children(node)

def propigate_location(original, new, skips=[]):
    LocationPropigator(original, skips).visit(new)
    return new

