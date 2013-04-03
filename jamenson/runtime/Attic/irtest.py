

from jamenson.support.slots import Slot,SlotList,connect,disconnect,getcell,getcells
from jamenson.runtime import Cons, clist, get_sys_symbol


class NodeBase(object):

    def __init__(self):
        self.continuation = Slot(self)

    def __str__(self):
        return str(self.as_sexp())

    def get_children_slots(self):
        return ()

    def get_children(self):
        acc = []
        for slot in self.get_children_slots():
            acc.extend(getcells(slot))
        return acc

    def is_constant(self):
        return all(c.is_constant() for c in self.get_children())

class Constant(NodeBase):

    def __init__(self, value):
        super(Constant,self).__init__()
        self.value = value

    def as_sexp(self):
        return clist(get_sys_symbol('quote'),
                     self.value)

    def is_constant(self):
        return True

    def eval(self):
        return self.value

class Add(NodeBase):

    def __init__(self, lop, rop):
        super(Add,self).__init__()
        self.lop = Slot(self)
        self.rop = Slot(self)
        connect(self.lop, lop.continuation)
        connect(self.rop, rop.continuation)

    def as_sexp(self):
        return clist(get_sys_symbol('+'),
                     getcell(self.lop).as_sexp(),
                     getcell(self.rop).as_sexp())

    def get_children_slots(self):
        return self.lop, self.rop

    def eval(self):
        return getcell(self.lop).eval() + getcell(self.rop).eval()

class Progn(NodeBase):

    def __init__(self, nodes=()):
        super(Progn,self).__init__()
        self.nodes = SlotList(self)
        for node in nodes:
            connect(self.nodes, node.continuation)

    def as_sexp(self):
        return clist(get_sys_symbol('progn'),
                     *(node.as_sexp() for node in getcells(self.nodes)))

    def get_children_slots(self):
        return self.nodes,

    def eval(self):
        for child in self.get_children():
            x = child.eval()
        return x

print Progn([Add(Constant(3), Constant(10)),
             Add(Add(Constant(10), Constant(20)),
                 Constant(20))]).eval()
