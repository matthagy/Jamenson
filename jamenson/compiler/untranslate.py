'''define as_string methods for providing an sexp based repressentation
   for ir nodes.
   attempts to be as close to cannonical print form as possible
'''

from __future__ import absolute_import

if __name__ == '__main__':
    import jamenson.compiler.untranslate
    exit()

from ..runtime.multimethod import MultiMethod, defmethod
from ..runtime.as_string import as_string
from ..runtime.atypes import as_optimized_type, union, typep, anytype, Seq
from ..runtime.atypes.ptypes import typep, function_type
from ..runtime.symbol import get_sys_symbol, make_keyword
from ..runtime.cons import clist, nil, Cons


from . import ir as I
from . import bind
from .pkg import get_compiler_symbol


as_sexp = MultiMethod(name='as_sexp',
                      signature='NodeBase',
                      doc="""
                      convert node to an sexpression that `should` translate
                      to this node
                      """)

@defmethod(as_string, [I.node])
def meth(op):
    return as_string(as_sexp(op))

@defmethod(as_sexp, [I.node])
def meth(n):
    return get_compiler_symbol(n.__class__.__name__)

no_quote_constants = as_optimized_type((int,long,float,str,True))

@defmethod(as_sexp, [I.constant])
def meth(op):
    if type(op.value) is not type and (
        typep(op.value, no_quote_constants) or op.value is nil):
        return op.value
    return clist(get_sys_symbol('quote'), op.value)

binding_names = {
    bind.BND_GLOBAL: 'global',
    bind.BND_LOCAL:  'local',
    bind.BND_CELL:   'cell',
    bind.BND_FREE:   'free'}

def hexkey(i):
    return make_keyword(hex(i))

def binding_as_sexp(bnd):
    args = [get_compiler_symbol(binding_names[bind.get_binding_use_type(bnd)]),
            bnd.symbol,
            hexkey(id(bnd.binding))]
    return clist(*args)

@defmethod(as_sexp, [type(None)])
def meth(n):
    return get_sys_symbol('None')

@defmethod(as_sexp, [I.read_binding])
def meth(rb):
    return clist(get_compiler_symbol('read_binding'),
                 binding_as_sexp(rb.binding))

@defmethod(as_sexp, [I.write_binding])
def meth(wb):
    return clist(get_compiler_symbol('write_binding'),
                 binding_as_sexp(wb.binding),
                 as_sexp(wb.value))

@defmethod(as_sexp, [I.delete_binding])
def meth(db):
    return clist(get_compiler_symbol('delete_binding'),
                 binding_as_sexp(db.binding))

@defmethod(as_sexp, [I.unary_base])
def meth(op):
    return clist(get_compiler_symbol(op.__class__.__name__),
                 as_sexp(op.op))

@defmethod(as_sexp, [I.binary_base])
def meth(op):
    return clist(get_compiler_symbol(op.__class__.__name__),
                 as_sexp(op.lop), as_sexp(op.rop))

@defmethod(as_sexp, [I.attrget])
def meth(aget):
    return clist(get_compiler_symbol('attrget'),
                 aget.name, as_sexp(aget.obj))

@defmethod(as_sexp, [I.attrset])
def meth(aset):
    return clist(get_compiler_symbol('attrset'),
                 aset.name, as_sexp(aset.obj), as_sexp(aset.value))

@defmethod(as_sexp, [I.attrdel])
def meth(adel):
    return clist(get_compiler_symbol('attrdel'),
                 adel.name, as_sexp(adel.obj))

@defmethod(as_sexp, [I.getitem])
def meth(gi):
    return clist(get_compiler_symbol('getitem'),
                 as_sexp(gi.op), as_sexp(gi.item))

@defmethod(as_sexp, [I.setitem])
def meth(si):
    return clist(get_compiler_symbol('setitem'),
                 as_sexp(si.op), as_sexp(si.item),
                 as_sexp(si.value))

@defmethod(as_sexp, [I.delitem])
def meth(di):
    return clist(get_compiler_symbol('delitem'),
                 as_sexp(di.op), as_sexp(di.item))

@defmethod(as_sexp, [I.buildslice])
def meth(bs):
    return clist(get_compiler_symbol('buildslice'),
                 as_sexp(bs.start), as_sexp(bs.stop), as_sexp(bs.step))


@defmethod(as_sexp, [I.progn])
def meth(p):
    return clist(get_compiler_symbol('progn'),
                 *map(as_sexp, p.exprs))

@defmethod(as_sexp, [I.call])
def meth(c):
    acc = map(as_sexp, c.args)
    for k,v in zip(c.kwd_names, c.kwd_values):
        acc.append(make_keyword(k))
        acc.append(as_sexp(v))
    if c.star_args:
        acc.append(get_sys_symbol('&rest'))
        acc.append(as_sexp(c.star_args))
    if c.star_kwds:
        acc.append(get_sys_symbol('&remaining_keys'))
        acc.append(as_sexp(c.star_kwds))
    return clist(get_compiler_symbol('call'), as_sexp(c.callee), *acc)

@defmethod(as_sexp, [I.if_])
def meth(i):
    return clist(get_compiler_symbol('if'),
                 as_sexp(i.condition),
                 as_sexp(i.then),
                 as_sexp(i.else_))

@defmethod(as_sexp, [I.return_])
def meth(r):
    return clist(get_compiler_symbol('return'), as_sexp(r.value))

@defmethod(as_sexp, [I.yield_])
def meth(y):
    return clist(get_compiler_symbol('yield'), as_sexp(y.value))

@defmethod(as_sexp, [I.raise0])
def meth(r):
    return clist(get_compiler_symbol('raise0'))

@defmethod(as_sexp, [I.raise1])
def meth(r):
    return clist(get_compiler_symbol('raise1'), as_sexp(r.value))

@defmethod(as_sexp, [I.raise3])
def meth(r):
    return clist(get_compiler_symbol('raise3'),
                 as_sexp(r.type), as_sexp(r.value),
                 as_sexp(r.traceback))

def binding_or_none_as_sexp(op):
    return None if op is None else Cons(get_sys_symbol('binding'),
                                        binding_as_sexp(op))

@defmethod(as_sexp, [I.trycatch])
def meth(tc):
    return clist(get_compiler_symbol('trycatch'),
                 as_sexp(tc.body),
                 clist(binding_or_none_as_sexp(tc.exc_type_binding),
                       binding_or_none_as_sexp(tc.exc_value_binding),
                       binding_or_none_as_sexp(tc.exc_tb_binding)),
                 as_sexp(tc.catch))

@defmethod(as_sexp, [I.tryfinally])
def meth(tf):
    return clist(get_compiler_symbol('tryfinally'),
                 as_sexp(tf.body),
                 as_sexp(tf.finally_))

def idtag(tag):
    return clist(tag.symbol, hexkey(tag.tagid))

@defmethod(as_sexp, [I.tagbody])
def meth(tb):
    acc = [get_compiler_symbol('tagbody')]
    for tag in tb.tags:
        acc.append(clist(idtag(tag),
                         as_sexp(tag.body)))
    return clist(*acc)

@defmethod(as_sexp, [I.go])
def meth(go):
    return clist(get_compiler_symbol('go'), idtag(go.tag))

@defmethod(as_sexp, [I.foriter])
def meth(fi):
    return clist(get_compiler_symbol('foriter'),
                 idtag(fi.tag),
                 binding_as_sexp(fi.binding),
                 as_sexp(fi.iter))


@defmethod(as_sexp, [I.function])
def meth(f):
    return clist(get_compiler_symbol('function'),
                 as_sexp(f.body),
                 f.name, f.doc,
                 clist(map(binding_as_sexp, f.args)),
                 clist(map(clist, zip(map(binding_as_sexp, f.kwds),
                                      map(as_sexp, f.defaults)))),
                 binding_or_none_as_sexp(f.star_args),
                 binding_or_none_as_sexp(f.star_kwds))

when_names = {
    I.W_COMPILE_TOPLEVEL: 'compile-toplevel',
    I.W_LOAD_TOPLEVEL: 'load-toplevel',
    I.W_EXECUTE: 'execute'}

@defmethod(as_sexp, [I.evalwhen])
def meth(ew):
    return clist(get_compiler_symbol('evalwhen'),
                 clist(*(make_keyword(when_names[when])
                         for when in ew.when)),
                 as_sexp(ew.expression))

@defmethod(as_sexp, [I.load_time_value])
def meth(ltv):
    return clist(get_compiler_symbol('load-time-value'),
                 as_sexp(ltv.expression))


@defmethod(as_sexp, [I.toplevel])
def meth(top):
    return clist(get_compiler_symbol('toplevel'),
                 as_sexp(top.expression))
