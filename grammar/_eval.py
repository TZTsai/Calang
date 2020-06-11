from _parser import calc_parse
from _builtins import binary_ops, unary_l_ops, unary_r_ops, builtins
from _funcs import Symbol, is_list
from _obj import Env, config, stack, Op, Attr, Map


Global = Env(name='_global_')
Global._ans = []
Global.update(builtins)


def calc_eval(exp):
    '''
    >>> calc_eval('2+4')
    6
    >>> calc_eval('x->2 x')
    ['PAR', 'x'] -> ['SEQ', 2, BOP(\u22c5, 16), ['NAME', 'x']]
    >>> calc_eval('[2,3]->[a,b]->a+b->x->2*x')
    '''
    tree, rem = calc_parse(exp)
    assert not rem
    return eval_tree(tree)


def tag(tr): return tr[0].split(':')[0]

def drop_tag(tr):
    tag = tr[0]
    try: dropped, tag = tag.split(':', 1)
    except: raise AssertionError
    tr[0] = tag
    return dropped

def is_tree(tr): return type(tr) is list

def is_str(tr): return type(tr) is str

def get_op(ops):
    def get(tr): return ops[tr[1]]
    return get

def SYM(tr): return Symbol(tr[1])

def EMPTY(tr): return None

def ANS(tr):
    '''
    >>> Global._ans = [1, 0, 'dd', 2.3]
    >>> ANS(['ANS'])
    2.3
    >>> ANS(['ANS', '0'])
    1
    >>> ANS(['ANS', '_'])
    'dd'
    >>> ANS(['ANS', '__'])
    0
    '''
    if len(tr) == 1:
        id = -1
    else:
        s = tr[1]
        if '_' in s: 
            id = -1-len(s)
        else:
            try: id = int(s)
            except: raise SyntaxError('invalid history index!')
    return Global._ans[id]

def NUM(tr):
    '''
    >>> NUM(['NUM:REAL', '2.4', '-18'])
    2.4e-18
    >>> NUM(['NUM:COMPLEX', ['REAL', '2.4'], '-', ['REAL', '1', '-10']])
    (2.4-1e-10j)
    '''
    type_ = tr[0].split(':')[-1]
    if type_ == 'COMPLEX':
        re, pm, im = tr[1:]
        re, im = NUM(re), NUM(im)
        if pm == '+':   return re + im*1j
        else:           return re - im*1j
    elif type_ == 'REAL' and len(tr) == 3:
        return eval(tr[1]+'e'+tr[2])
    else:
        return eval(tr[1])

def SEQtoTREE(tr):
    stk = stack()
    ops = stack()
    default_op = binary_ops['⋅']
    
    def pop_val():
        v = stk.pop()
        if isinstance(v, Op): raise SyntaxError('op sequence in disorder')
        return v

    def pop_op():
        op = stk.pop()
        if op != ops.pop(): raise SyntaxError('op sequence in disorder')
        return op
    
    def apply(op, *vals):
        if any(type(v) is c for v in vals for c in (list, str)):
            raise AssertionError
        return op(*vals)

    def shrink():
        # try to evaluate or shrink several previous trees into a bigger tree
        op = ops.peek()
        tag = op.type
        if tag == 'BOP':
            n2 = pop_val()
            op = pop_op()
            n1 = pop_val()
            try: n = apply(op, n1, n2)
            except: n = ['SEQ', n1, op, n2]
        else:
            if tag == 'LOP':
                n1 = pop_val()
                op = pop_op()
                try: n = apply(op, n1)
                except: n = ['SEQ', op, n1]
            else:
                op = pop_op()
                n1 = pop_val()
                try: n = apply(op, n1)
                except: n = ['SEQ', n1, op]
        stk.push(n)

    def push(x):
        if isinstance(x, Op):
            while ops:
                op = ops.peek()
                if x.prior <= op.prior: shrink()
                else: break
            ops.push(x)
        elif stk and not isinstance(stk.peek(), Op):
            push(default_op)
        stk.push(x)

    for x in tr[1:]: push(x)
    while ops: shrink()
    assert len(stk) == 1
    return pop_val()

def LIST(tr):
    lst = []
    for it in tr[1:]:
        if is_tree(it) and tag(it) == 'UNPACK':
            lst.extend(it)  # TODO unpack an env
        else:
            lst.append(it)
    return tuple(lst)

def SYMLIST(tr): return tr[1:]

def GENLIST(tr):
    pass
 
def ATTR(tr): return Attr(tr[1])

def MAP(tr):
    _, form, body = tr
    assert drop_tag(body) == 'BODY'
    return Map(form, body)

def LET(tr): return eval_tree(tr[2], env=tr[1])


## these requires environment

def NAME(tr, env):
    name = tr[1]
    try: return getattr(env, name)
    except AttributeError:
        if config.symbolic: return Symbol(name)
        else: raise NameError(f'unbound symbol \'{tr}\'')

def FIELD(tr, env):
    subfields = [t[1] for t in tr]
    while subfields:
        env = getattr(env, subfields.pop(0))
    return env

def PRINT(tr, env):
    if config.debug: exec('print(f"%s")' % tr[1], locals=env)

def IF_ELSE(tr, env):
    _, t_case, cond, f_case = tr
    if is_tree(cond): return tr
    elif cond:  return eval_tree(t_case, env)
    else:       return eval_tree(f_case, env)

def ENV(tr, env):
    local = env()
    for t in tr[1:]:
        if t[0] == 'BIND':
            _, form, val = t
        elif t[0] == 'MATCH':
            _, val, form = t
        else:
            raise SyntaxError('unknown tag: '+t[0])
        match(val, form, local)
    
def MATCH(tr, env):
    _, val, form = tr
    local = env()
    match(val, form, local)

def match(val, form, local):
    '''
    >>> L = Env()
    >>> match([1, 2, 3], ['PAR_LST', ['PAR', 'a'], ['EXTPAR', 'ex']], L)
    >>> print(L)
    (value: <env: (local)>, a: 1, ex: (2, 3))
    >>> match([-1], ['PAR_LST', ['PAR', 'w'], ['OPTPAR', ['PAR', 'p'], 5]], L)
    >>> print(L)
    (value: <env: (local)>, a: 1, ex: (2, 3), w: -1, p: 5)
    '''
    def split_pars(form):
        pars, opt_pars = [], []
        ext_par = None
        for t in form:
            if t[0] in ['PAR', 'PAR_LST']:
                pars.append(t)
            elif t[0] == 'OPTPAR':
                opt_pars.append(t)
            else:
                ext_par = t
        return pars, opt_pars, ext_par

    if form[0] == 'PAR_LST':
        assert is_list(val)
        form = form[1:]
        if val or form:
            if not val or not form:
                raise AssertionError
            pars, opt_pars, ext_par = split_pars(form)
            if len(pars) > len(val):
                raise ValueError(f'not enough items in {val} to match')
            for i, par in enumerate(pars):
                match(val[i], par, local)
            val = val[i+1:]
            while val and opt_pars:
                item = val.pop(0)
                opt_par = opt_pars.pop(0)[1]
                match(item, opt_par, local)
            for _, opt_par, default in opt_pars:
                match(default, opt_par, local)
            if ext_par:
                setattr(local, ext_par[1], tuple(val))
    elif form[0] == 'PAR':
        setattr(local, form[1], val)
    else:
        raise SyntaxError



def eval_tree(tr, env=Global):
    '''
    >>> eval_tree(['SEQ', ['NUM:REAL', '1'], ['BOP', '+'], ['NUM:REAL', '2'], ['BOP', '*'], ['NUM:REAL', '3']])
    7
    >>> eval_tree(["SEQ", ["NUM:REAL", "3"], ["ROP", "!"], ["BOP", "+"], ["NUM:REAL", "4"]])
    10
    >>> eval_tree(["VAL_LST", ["NUM:REAL", "2"]])
    (2,)
    >>> eval_tree(["VAL_LST", ["NUM:REAL", "3"], ["NUM:REAL", "4"], ["NUM:REAL", "6"]])
    (3, 4, 6)
    >>> eval_tree(['MAP', ['PAR', 'a'], ['BODY:SEQ', ['NUM:REAL', '2'], ['BOP', '*'], ['NAME', 'a']]])
    ['PAR', 'a'] -> ['SEQ', 2, BOP(*, 8), ['NAME', 'a']]
    >>> eval_tree(['MAP', ['PAR', 'x'], ['BODY:SEQ', ['SEQ', ['NUM:REAL', '2'], ['BOP', '+'], ['NUM:REAL', '3']], ['BOP', '*'], ['SEQ', ['NUM:REAL', '6'], ['BOP', '+'], ['NAME', 'x']]]])
    ['PAR', 'x'] -> ['SEQ', 5, BOP(*, 8), ['SEQ', 6, BOP(+, 6), ['NAME', 'x']]]
    '''
    if not is_tree(tr): return tr
    type_ = tag(tr)
    if type_ == 'BODY': env = None
    for i in range(1, len(tr)):
        tr[i] = eval_tree(tr[i], env)
    if type_ in subs_rules:
        tr = subs_rules[type_](tr)
    elif type_ in eval_rules and env:
        tr = eval_rules[type_](tr, env)
    return tr


Map.match = match
Map.eval  = eval_tree


subs_rules = {
    'ANS': ANS,                 'SYM': SYM,         
    'EMPTY': EMPTY,             'NUM': NUM,
    'SEQ': SEQtoTREE,           'BOP': get_op(binary_ops),
    'LOP': get_op(unary_l_ops), 'ROP': get_op(unary_r_ops),
    'VAL_LST': LIST,            'SYM_LST': SYMLIST, 
    'GEN_LST': GENLIST,         
    'ATTR': ATTR,               'MAP': MAP,
    'LET': LET,                 
}

eval_rules = {
    'FIELD': FIELD,             'NAME': NAME,       
    'PRINT': PRINT,             'EXP': eval_tree,
    'ENV': ENV,                 'MATCH': MATCH,
    'IF_ELSE': IF_ELSE,
}


if __name__ == "__main__":
    import doctest
    doctest.testmod()