
from types import NoneTypes

delete_op = MultiMethod('delete_op',
                        doc='Generic state clearing of a single object')
seq_yield = MultiMethod('seq_yield',
                        doc='Visit all members of a sequence for deletion')

@seq_yield.defmethod('(int,long,float,complex,bool,str,NoneType)')
def atomic(op):
    '''objects that have no members
    '''
    pass

def meth(op):
    '''by default, objects 
    '''

@delete_seq.defmethod('object')
def meth(op):
    """by default, objects are not sequences
    """
    pass

@delete_seq.defmethod('(list,tuple)')
def meth(seq):
    for el in seq:
        delete

@delete.defmethod('(tuple,str,int,float,complex,long), recursive=object')
def meth(op, recursive=False):
    """things that can't be deleted
    """
    pass

@delete.defmethod('list, recursive=object')
def meth(op, recursive=False):
    """things that can't be deleted
    """
    if recursive:
        delete_rec_seq(op)
    del op[::]

@delete.defmethod('dict, recursive=object')
def meth(op, recursive=False):
    if recursive:
        delete_rec_seq(op.iterkeys())
        delete_rec_seq(op.itervalues())

