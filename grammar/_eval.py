from _builtins import *
from _funcs import *
from _obj import CalcStack, Env, config, stack, Op


Global = Env()
Global._ans = []
Global.update(builtins)


subs_rules = {
    'ANS': ans, 'SYM': symbol, 'EMPTY': empty, 
    'NUM': number, 'SEQ': op_tree
}

def subs_tree(tr):
    if type(tr) is str:
        return tr
    elif tr[0] in subs_rules:
        return subs_rules[tr[0]](tr)
    else:
        return tuple(subs_tree(t) for t in tr)

def symbol(tr): return Symbol(tr[1])

def empty(tr): return

def ans(tr):
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

def number(tr):
    _, type_ = tr[0].split(':')
    if type_ == 'COMPLEX':
        re, pm, im = tr[1:]
        re, im = number(re), number(im)
        if pm == '+': return re + im*1j
        else: return re - im*1j
    elif type_ == 'REAL' and len(tr) == 3:
        return eval(tr[1]+'e'+tr[2])
    else:
        return eval(tr[1])

def op_tree(tr):
    
    stk = stack()
    ops = stack()
    
    def pop_val():
        v = stk.pop()
        if isinstance(v, Op):
            raise SyntaxError('op sequence in disorder')
        return v

    def pop_op():
        op = stk.pop()
        if op != ops.pop():
            raise SyntaxError('op sequence in disorder')
        return op

    def can_simp(n):
        return not (n and isinstance(n, tuple) and isinstance(n[1], str))
        
    def shrink():
        # try to evaluate or shrink several previous trees into a bigger tree
        tag, op = ops.peek()
        if tag == 'BOP':
            n2 = pop_val()
            op = pop_op()
            n1 = pop_val()
            try:
                assert can_simp(n1) and can_simp(n2)
                n = op(n1, n2)
            except:
                n = (tag, op, n1, n2)
        else:
            if tag == 'LOP':
                n1 = pop_val()
                op = pop_op()
            else:
                op = pop_op()
                n1 = pop_val()
            try:
                assert can_simp(n1)
                n = op(n1)
            except:
                n = (tag, op, n1)
        stk.push(n)

    def push(x):
        tag, sym = x
        if tag == 'BOP':
            x[1] = binary_ops[sym]
        elif tag == 'LOP':
            x[1] = unary_l_ops[sym]
        elif tag == 'ROP':
            x[1] = unary_r_ops[sym]
        if isinstance(x[1], Op):
            while ops:
                op = ops.peek()
                if x[1].prior <= op.priority: shrink()
                else: break
            ops.push(x)
        else:
            x = subs_tree(x)
        stk.push(x)

    for x in tr[1:]: push(x)
    while ops: shrink
    return pop_val()


eval_rules = {
    'LST': eval_list, 'FORMAL': eval_formal
}



def eval_name(tr, env):
    s = tr[1]
    try:
        val = env[tr]
    except KeyError:
        if config.symbolic: val = Symbol(tr)
        else: raise NameError(f'unbound symbol \'{tr}\'')
    return val

def eval_list(tr, env):
    pass

def eval_formal(tr, env):
    optpar_only = False
    def simp(t):
        nonlocal optpar_only
        if 'BIND' in t[0]:
            _, formal, exp = t
            optpar_only = True
            return eval_formal(formal, env), eval_exp(exp, env)
        elif 'EXT_PAR' in t[0]:
            return t[1]
        elif t[0] == 'FORMAL':
            return eval_formal(t, env)
        elif not optpar_only:  # NAME
            return t[1]
        raise SyntaxError('optional parameter before necessary parameter')
    return tuple(simp(t) for t in tr[1:])


def eval_exp(tr, env):
    pass


def log_macro(env):
    def value(arg):
        try: return env[arg]
        except: return '??'
    def log(*args):
        if config.debug:
            print(env.frame*'  ' + ', '.join(f'{arg}={value(arg)}' for arg in args))
    return log
