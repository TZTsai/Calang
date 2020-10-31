from parse import tag, is_tree, drop_tag

def decompile(tree):
    "Reconstruct a readable string from the syntax tree."
    
    def rec(tr, in_seq=False):
        "$in_seq: whether it is in a sequence"
        
        if not is_tree(tr): return str(tr)
        
        def group(s): return '(%s)' if in_seq else s
        # if in an operation sequence, add a pair of parentheses
        
        tr = tr.copy()
        type = tag(tr)
        if type in ('NAME', 'SYM', 'PAR'):
            return tr[1]
        elif type == 'FIELD':
            return ''.join(map(rec, tr[1:]))
        elif type == 'ATTR':
            return '.' + tr[1]
        elif type == 'SEQ':
            return ''.join(rec(t, True) for t in tr[1:])
        elif type[-2:] == 'OP':
            op = tr[1]
            return (' %s ' if op.priority < 4 else '%s') % str(tr[1])
        elif type == 'NUM':
            return str(tr[1])
        elif type == 'FORM':
            _, pars, optpars, extpar = tr
            pars = [rec(par) for par in pars]
            optpars = [f'{rec(optpar)}: {default}' for optpar, default in optpars]
            extpar = [extpar+'~'] if extpar else []
            return "[%s]" % ', '.join(pars + optpars + extpar)
        elif type == 'IF_ELSE':
            return group("%s if %s else %s" % tuple(map(rec, tr[1:])))
        elif type[-3:] == 'LST':
            return '[%s]' % ', '.join(map(rec, tr[1:]))
        elif type == 'MAP':
            _, form, exp = tr
            return group('%s => %s' % (rec(form), rec(exp)))
        elif type == 'DICT':
            return '(%s)' % ', '.join(map(rec, tr[1:]))
        elif type == 'BIND':
            if tag(tr[-1]) == 'DOC': tr = tr[1:]
            tup = tuple(rec(t) for t in tr[1:])
            if tag(tr[2]) == 'AT':
                return '%s %s = %s' % tup
            else:
                return '%s = %s' % tup
        elif type == 'MATCH':
            _, form, exp = tr[1]
            return group('%s::%s' % (rec(form), rec(exp)))
        elif type == 'CLOSURE':
            _, local, exp = tr
            return '%s %s' % (rec(local), rec(exp))
        elif type == 'FUNC':
            _, name, form = tr
            return '%s%s' % (rec(name), rec(form))
        elif type == 'WHEN':
            return 'when(%s)' % ', '.join(': '.join(map(rec, case[1:]))
                                          for case in tr[1:])
        elif type == 'AT':
            return '@' + rec(tr[1])
        elif type == 'DELAY':
            drop_tag(tr)
            return rec(tr, in_seq)
        elif type in ('PRINT', 'DOC'):
            return ''
        else:
            return str(list(map(rec, tr)))
    return rec(tree)
