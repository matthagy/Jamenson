

class CachingBase(object):

    class __metaclass__(type):
        def __new__(cls, name, bases, dct):
            dct = dict(dct)
            dct['_cache'] = dict()
            return type.__new__(cls, name, bases, dct)

    def __new__(cls, *args):
        key = cls.get_key(*args)
        try:
            return cls._cache[key]
        except KeyError:
            self = cls._cache[key] = object.__new__(cls)
            self._init_cached(*key)
            return self

