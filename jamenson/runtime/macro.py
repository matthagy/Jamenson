
class MacroFunction(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwds):
        raise RuntimeError("can't call macro's directly")

    def macro_expand(self, form):
        return self.func(form)

