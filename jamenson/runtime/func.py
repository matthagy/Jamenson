
__all__ = '''
          identity noop compose
'''.split()

def identity(x): return x
def noop(x): return None

def compose(*funcs):
    if not funcs:
        return noop
    if len(funcs)==1:
        return funcs[0]
    funcs = funcs[::-1]
    def wrapper(op):
        for fun in funcs:
            op = fun(op)
        return op
    return wrapper

