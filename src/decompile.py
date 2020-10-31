from parse import tag as tree_tag, is_tree, drop_tag
from builtin import operators

def decompile(tree):
    "Reconstruct a readable string from the syntax tree."
    
    def rec(tr, in_seq=False):
        "$in_seq: whether it is in a sequence"
        
        if not is_tree(tr): return str(tr)
        
        def group(s): return '(%s)' if in_seq else s
        # if in an operation sequence, add a pair of parentheses
        
        tr = tr.copy()
        tag = tree_tag(tr)
        if tag in ('NAME', 'SYM', 'PAR'):
            return tr[1]
        elif tag == 'FIELD':
            return ''.join(map(rec, tr[1:]))
        elif tag == 'ATTR':
            return '.' + tr[1]
        elif tag == 'SEQ':
            return ''.join(rec(t, True) for t in tr[1:])
        elif tag[-2:] == 'OP':
            op = tr[1]
            if type(op) is str:
                op = operators[tag][op]
            template = ' %s ' if op.priority < 4 else '%s'
            return template % str(tr[1])
        elif tag == 'NUM':
            return str(tr[1])
        elif tag == 'FORM':
            _, pars, optpars, extpar = tr
            pars = [rec(par) for par in pars[1:]]
            optpars = [f'{rec(optpar)}: {default}' for optpar, default in optpars[1:]]
            extpar = [extpar+'~'] if extpar else []
            return "[%s]" % ', '.join(pars + optpars + extpar)
        elif tag == 'IF_ELSE':
            return group("%s if %s else %s" % tuple(map(rec, tr[1:])))
        elif tag[-3:] == 'LST':
            return '[%s]' % ', '.join(map(rec, tr[1:]))
        elif tag == 'MAP':
            _, form, exp = tr
            return group('%s => %s' % (rec(form), rec(exp)))
        elif tag == 'DICT':
            return '(%s)' % ', '.join(map(rec, tr[1:]))
        elif tag == 'BIND':
            if tree_tag(tr[-1]) == 'DOC': tr = tr[1:]
            tup = tuple(rec(t) for t in tr[1:])
            if tree_tag(tr[2]) == 'AT':
                return '%s %s = %s' % tup
            else:
                return '%s = %s' % tup
        elif tag == 'MATCH':
            _, form, exp = tr[1]
            return group('%s::%s' % (rec(form), rec(exp)))
        elif tag == 'CLOSURE':
            _, local, exp = tr
            return '%s %s' % (rec(local), rec(exp))
        elif tag == 'FUNC':
            _, name, form = tr
            return '%s%s' % (rec(name), rec(form))
        elif tag == 'WHEN':
            return 'when(%s)' % ', '.join(': '.join(map(rec, case[1:]))
                                          for case in tr[1:])
        elif tag == 'AT':
            return '@' + rec(tr[1])
        elif tag == 'DELAY':
            drop_tag(tr)
            return rec(tr, in_seq)
        elif tag in ('PRINT', 'DOC'):
            return ''
        else:
            return str(list(map(rec, tr)))
    return rec(tree)
