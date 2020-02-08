import re


def replace(*subs):
    def repl(m):
        groups = len(m.groups())
        assert(groups == len(subs))
        s = m[0]
        splits = []
        k = 0
        for g in range(groups):
            i, j = m.span(g+1)
            splits.append(s[k:i])
            splits.append(subs[g])
            k = j
        return ''.join(splits)
    return repl


def repfile(filename):
    with open(filename, 'r') as fi, open(filename+'(1)', 'w') as fo:
        s = fi.read()
        s = re.sub(r'(\{).*:.*(\})', replace('with ', ':'), s)
        s = re.sub(r'(\{).*(\{)', replace('function ', ':'), s)
        fo.write(s)


for fn in ('tests', *map(lambda s: 'examples/'+s,
                         ('fold', 'lambda_list', 'merge_sort', 'perms', 'tree')),
           *map(lambda s: 'modules/'+s, ('la', 'util'))):
    repfile(fn)