import doctest
import re


def replace(*subs):
    def repl(m):
        groups = len(m.groups())
        assert(groups == len(subs))
        s = m[0]
        splits = []
        k = 0
        for g in range(groups):
            i, j = [x - m.start() for x in m.span(g+1)]
            splits.append(s[k:i])
            splits.append(subs[g])
            k = j
        return ''.join(splits)
    return repl


def sub_with(s):
    """
    >>> sub_with('{x:1} x+3')
    'with x:1: x+3'
    """
    return re.sub(r'(\{)[^\{]*:[^\{]*(\})', replace('with ', ':'), s)


def sub_func(s):
    """
    >>> sub_func('f := {x, y} x*(1+y)')
    'f := function x, y: x*(1+y)'
    >>> sub_func('compose := {f, g} {x} f(g(x))')
    'compose := function f, g: function x: f(g(x))'
    """
    return re.sub(r'(\{)[^\{]*(\})', replace('function ', ':'), s)


# substitute readme
def sub_vars(s):
    return re.sub(r'(\\<)[^\s]*(>)', replace('`', '`'), s)


def subfile(filename, *sub_funcs):
    """ Create a new file which is the result of `sub_funcs` applied to the original file. """
    with open(filename, 'r', errors='ignore') as fi, \
            open(filename+'(1)', 'w+', errors='ignore') as fo:
        s = fi.read()
        for func in sub_funcs:
            s = func(s)
        fo.write(s)


def writefile(filename):
    """ Overwrite the original file. """
    with open(filename, 'w') as fo, open(filename+'(1)', 'r') as fi:
        s = fi.read()
        fo.write(s)


# for f in ('README.md',):
#     subfile(f, sub_vars)

if __name__ == "__main__":
    doctest.testmod()
