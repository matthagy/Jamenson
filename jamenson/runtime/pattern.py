
import string
import sre_parse

__all__ = ['get_chars']

categories = dict(category_digit=string.digits,
                  category_space=string.whitespace,
                  category_linebreak='\n')


def get_chars(pattern):
    acc = []
    def rec(x):
        op,value = x
        if op=='literal':
            acc.append(chr(value))
        elif op=='category':
            acc.extend(categories[value])
        elif op=='in':
            for x in value:
                rec(x)
        elif op=='range':
            start,end = value
            acc.extend(chr(i) for i in xrange(start,end+1))
        else:
            raise RuntimeError('[%s %s] not handled' % (op,value))
    if not (pattern.startswith('[') and pattern.endswith(']')):
        pattern = '[%s]' % pattern
    for x in sre_parse.parse(pattern):
        rec(x)
    return acc

