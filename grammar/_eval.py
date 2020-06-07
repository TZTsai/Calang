from _builtins import *
from _funcs import *
from _obj import CalcStack, Env, config


Global = Env()
Global._ans = []
Global.update(builtins)


subs_rules = {
    'ANS': ans, 'SYM': symbol, 'EMPTY': empty, 'NUM': number,
}

def symbol(tr): return Symbol(tr[1])

def empty(tr): return

def ans(tr):
    id = -1
    if len(tr) > 1:
        s = tr[1]
        if '_' in s: 
            id -= len(s)
        else:
            try: id = -1-len(s) if '_' in s else int(s)
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


eval_rules = {
    'OP_SEQ': eval_seq, 'LST': eval_list,
    'FORMAL': eval_formal
}



def eval_seq(tr, env):
    pass

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
