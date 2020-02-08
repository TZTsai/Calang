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
    return re.sub(r'(\{)[^\{]*:[^\{]*(\})', replace('with ', ':'), s)

def sub_func(s):
    return re.sub(r'(\{)[^\{]*(\})', replace('function ', ':'), s)

def repfile(filename):
    with open(filename, 'r') as fi, open(filename+'(1)', 'w') as fo:
        s = fi.read()
        s = sub_func(s)
        s = sub_with(s)
        fo.write(s)

def copyfile(filename):
    with open(filename, 'w') as fo, open(filename+'(1)', 'r') as fi:
        s = fi.read()
        fo.write(s)


print(sub_func('f := {x, y} x*(1+y)'))
print(sub_func('compose := {f, g} {x} f(g(x))'))
print(sub_with('{x:1} x+3'))

for fn in ('tests', *map(lambda s: 'examples/'+s,
                         ('fold', 'lambda_list', 'merge_sort', 'perms', 'tree')),
           *map(lambda s: 'modules/'+s, ('la', 'util'))):
    repfile(fn)
    # copyfile(fn)