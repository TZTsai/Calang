from _builtins import binary_ops, unary_l_ops, unary_r_ops, builtins
from _funcs import Symbol
from _obj import Env, config, stack, Op, Attr


Global = Env(name='_Global_')
Global._ans = []
Global.update(builtins)


subs_rules = {
    'ANS': ANS,         'SYM': SYM,         'EMPTY': EMPTY, 
    'NUM': NUM,         'SEQ': SEQtoTREE,   'BOP': get_op(binary_ops),
    'LOP': get_op(unary_l_ops),             'ROP': get_op(unary_r_ops),
    'VAL_LST': LIST,    'FORM': FORM,       'BODY': eval_tree,
    'ATTR': ATTR,       
}

eval_rules = {
    'FIELD': FIELD,     'NAME': NAME,       'PRINT': PRINT
}

def tag(tr): return tr[0].split(':')[0]

def eval_tree(tr, env=None):
    '''
    >>> eval_tree(['SEQ', ['NUM:REAL', '1'], ['BOP', '+'], ['NUM:REAL', '2'], ['BOP', '*'], ['NUM:REAL', '3']])
    7
    '''
    for i in range(1, len(tr)):
        tr[i] = eval_tree(tr[i], env)
    type_ = tag(tr)
    if type_ in subs_rules:
        tr = subs_rules[type_](tr)
    elif type_ in eval_rules:
        tr = eval_rules[type_](tr, env)
    return tr


def get_op(ops):
    def get(name): return ops[name]
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
    type_ = tag(tr)
    if type_ == 'COMPLEX':
        re, pm, im = tr[1:]
        re, im = NUM(re), NUM(im)
        if pm == '+':   return re + im*1j
        else:           return re - im*1j
    elif type_ == 'REAL' and len(tr) == 3:
        return eval(tr[1]+'e'+tr[2])
    else:
        return eval(tr[1])

def is_tree(tr): return type(tr) is list

def SEQtoTREE(tr):
    stk = stack()
    ops = stack()
    
    def pop_val():
        v = stk.pop()
        if isinstance(v, Op): raise SyntaxError('op sequence in disorder')
        return v

    def pop_op():
        op = stk.pop()
        if op != ops.pop(): raise SyntaxError('op sequence in disorder')
        return op

    def shrink():
        # try to evaluate or shrink several previous trees into a bigger tree
        op = ops.peek()
        tag = op.type
        if tag == 'BOP':
            n2 = pop_val()
            op = pop_op()
            n1 = pop_val()
            if is_tree(n1) or is_tree(n2): n = [tag, op, n1, n2]
            else: n = op(n1, n2)
        else:
            if tag == 'LOP':
                n1 = pop_val()
                op = pop_op()
            else:
                op = pop_op()
                n1 = pop_val()
            if is_tree(n1): n = [tag, op, n1]
            else: n = op(n1)
        stk.push(n)

    def push(x):
        if isinstance(x, Op):
            while ops:
                op = ops.peek()
                if x.prior <= op.priority: shrink()
                else: break
            ops.push(x)
        stk.push(x)

    for x in tr[1:]: push(x)
    while ops: shrink()
    return pop_val()

def LIST(tr):
    ""

def SYMLIST(tr):
    pass

def FORM(tr): return tr

def ATTR(tr): return Attr(tr[1])


def NAME(tr, env):
    name = tr[1]
    try: return getattr(env, name)
    except KeyError:
        if config.symbolic: return Symbol(name)
        else: raise NameError(f'unbound symbol \'{tr}\'')

def FIELD(tr, env):
    subfields = [t[1] for t in tr]
    while subfields:
        env = getattr(env, subfields.pop(0))
    return env

def PRINT(tr, env):
    if config.debug: exec('print(f"%s")' % tr[1], locals=env)
