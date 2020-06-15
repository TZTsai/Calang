from _parser import calc_parse
from _builtins import binary_ops, unary_l_ops, unary_r_ops, builtins
from _funcs import Symbol, is_list, same, reduce
from _obj import Env, config, stack, Op, Attr, Map


def GlobalEnv():
    Global = Env(name='_global_')
    Global._ans = []
    Global.update(builtins)
    return Global

Global = GlobalEnv()


def calc_eval(exp):  # only for testing; calc_exec will use eval_tree
    '''
    >>> eval = calc_eval
    >>> calc_eval('2+4')
    6
    >>> calc_eval('x->2 x')
    ['PAR', 'x'] -> ['SEQ', 2, BOP((adj), 20), ['NAME', 'x']]
    >>> calc_eval('[2,3]->[a,b]->a+b->x->2*x')
    10
    >>> eval('(a: 1, b: a+1) -> b')
    2
    >>> eval('(a: 2, b: 4) -> (b: a+4) -> [a, b] "{a=} {b=}"')
    a=2 b=6
    (2, 6)
    >>> eval('[1, *[2, 3]]')
    (1, 2, 3)
    >>> eval('__')
    (2, 6)
    >>> eval('_0')
    6
    >>> Global['e'] = eval('(a: 1, b: a*3)')
    >>> eval('e.b')
    3
    >>> print(eval('(a:8, a.b:9)')['a'])
    (VAL: 8, b: 9)
    >>> try: print(eval('(v.x:0)'))
    ... except Exception as e: print(e)
    field not in current env
    '''
    tree, rest = calc_parse(exp)
    if rest: raise SyntaxError('parsing failed, the unparsed part: ' + rest)
    result = eval_tree(tree)
    if result is not None:
        Global._ans.append(result)
        return result


# some utils

def tag(tr): 
    return tr[0].split(':')[0]

def drop_tag(tr, expected):
    if not is_list(tr): return tr
    tag = tr[0]
    try: dropped, tag = tag.split(':', 1)
    except: raise AssertionError
    assert dropped == expected
    tr[0] = tag

def remove_delay(tr): drop_tag(tr, 'DELAY')

def is_tree(tr): return type(tr) is list

def is_str(tr): return type(tr) is str

def get_op(ops):
    def get(tr): return ops[tr[1]]
    return get


# substitution rules

def SYM(tr): return Symbol(tr[1])

def EMPTY(tr): return None

def ANS(tr):
    s = tr[1]
    if same(*s): id = -len(s)
    else:
        try: id = int(s[1:])
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
    default_op = binary_ops['(adj)']
    
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

    def reduce():
        # try to evaluate or reduce several previous trees to a bigger tree
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
                if x.prior <= op.prior: reduce()
                else: break
            ops.push(x)
        elif stk and not isinstance(stk.peek(), Op):
            push(default_op)
        stk.push(x)

    for x in tr[1:]:
        if x != 'PRINT': push(x)
    while ops: reduce()
    assert len(stk) == 1
    return pop_val()

def FIELD(tr): return reduce(Attr.adjoin, tr[1:])

def LIST(tr):
    lst = []
    for it in tr[1:]:
        if is_tree(it) and tag(it) == 'UNPACK':
            lst.extend(it[1:])  # TODO unpack an env
        elif is_tree(it):
            return tr
        else:
            lst.append(it)
    return tuple(lst)

def SYMLIST(tr): return tr[1:]

def SLICE(tr): return slice(*tr[1:])

def GENLIST(tr):
    pass
 
def ATTR(tr): return Attr(tr[1])

def MAP(tr):
    _, form, body = tr
    remove_delay(body)
    return Map(form, body)

def LET(tr):
    _, local, body = tr
    remove_delay(body)
    result = eval_tree(body, env=local)
    if isinstance(result, Env):
        result._parent = local
    return result

def split_field(tr, env=Global):
    if tr[0] == 'NAME':
        attr = tr[1]
        field = env
    elif tr[0] == 'FIELD':
        top = tr[1][1]
        if top not in env:
            raise AssertionError('field not in current env')
        attr = tr.pop()[1]
        field = eval_tree(tr, env) if len(tr) > 1 else env
    else:
        raise TypeError('wrong type for split_field')
    return field, attr


## eval rules which require environment

def NAME(tr, env):
    name = tr[1]
    try: return getattr(env, name)
    except AttributeError:
        if config.symbolic: return Symbol(name)
        else: raise NameError(f'unbound symbol \'{tr}\'')

def PRINT(tr, env):
    exec('print(f%s)' % tr[1], env.all())
    return 'PRINT'

def IF_ELSE(tr, env):
    _, t_case, cond, f_case = tr
    if is_tree(cond): return tr
    elif cond:  return eval_tree(t_case, env)
    else:       return eval_tree(f_case, env)

def ENV(tr, env):
    local = env.child()
    if isinstance(tr[1], Env): return tr[1]
    for t in tr[1:]:
        _, to_def, exp = t
        define(to_def, exp, local)
    return local
    
def MATCH(tr, env):
    _, val, form = tr
    local = env.child()
    match(val, form, local)
    return local

def match(val, form, local):
    '''
    >>> L = Env()
    >>> match([1, 2, 3], ['PAR_LST', ['PAR', 'a'], ['EXTPAR', 'ex']], L)
    >>> print(L)
    (VAL: <env: (local)>, a: 1, ex: (2, 3))
    >>> match([-1], ['PAR_LST', ['PAR', 'w'], ['OPTPAR', ['PAR', 'p'], 5]], L)
    >>> print(L)
    (VAL: <env: (local)>, a: 1, ex: (2, 3), w: -1, p: 5)
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
                raise AssertionError('match failed')
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


# these rules are commands in the calc

def DIR(tr):
    field = Global if len(tr) == 1 else tr[1]
    for name, val in field.items(): print(f"{name}: {val}")

def LOAD(tr):
    modname = tr[1]
    test = '-t' in tr
    verbose = '-v' in tr
    overwrite = '-w' in tr

    global Global
    current_global = Global
    Global = GlobalEnv()  # a new global env
    
    LOAD.run('scripts/' + modname + '.cal', test, start=0, verbose=verbose)
    if overwrite:
        current_global.update(Global)
    else:
        for name in Global:
            if name not in current_global:
                current_global[name] = Global[name]
            else:
                print(f'name {name} not loaded because it is bounded')
    Global = current_global

def IMPORT(tr):
    modname = tr[1]
    verbose = '-v' in tr
    overwrite = '-w' in tr
    env = definitions = {}
    try:
        exec('from modules.%s import export'%modname, env)
        definitions = env['export']
    except ModuleNotFoundError:
        exec('from sympy import %s'%modname, definitions)
    
    for name, val in definitions.items():
        if name not in Global or overwrite:
            if verbose: print(f'imported: {name}')
            Global[name] = val

def CONF(tr):
    conf = tr[1]
    if conf == 'prec':
        if len(tr) == 2:
            print(config.precision)
        else:
            config.precision = min(1, int(tr[2]))
    elif conf == 'tolerance':
        if len(tr) == 2:
            print(config.tolerance)
        else:
            config.tolerance = float(tr[2])
    else:
        if len(tr) == 2:
            print(getattr(config, conf))
        else:
            setattr(config, conf, True if tr[2] in ('on', '1') else False)

def DEL(tr):
    for t in tr[1:]:
        field, attr = split_field(t)
        field.delete(attr)

def DEF(tr):
    _, to_def, exp = tr
    define(to_def, exp)

def define(to_def, exp, env=Global):
    
    def def_(field, val):
        superfield = field[:-1]
        parent, attr = split_field(field, env)
        if not isinstance(parent, Env):
            parent = env.child(parent)
            def_(superfield, parent)  # if parent is not an env, redefine it as an env
        setattr(parent, attr, val)
        if isinstance(val, Map):
            val.__name__ = attr

    def def_all(fields, val):
        if tag(fields) == 'FIELDS':
            assert is_list(val) and len(fields) == len(val)
            for field, item in zip(fields, val):
                def_all(field, item)
        else:
            def_(fields, val)

    if tag(to_def) == 'FUNC':
        _, field, form = to_def
        val = Map(form, exp)
        def_(field, val)
    else:
        val = eval_tree(exp, env)
        def_all(to_def, val)
    


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
    >>> eval_tree(['MAP', ['PAR', 'a'], ['DELAY:SEQ', ['NUM:REAL', '2'], ['BOP', '*'], ['NAME', 'a']]])
    ['PAR', 'a'] -> ['SEQ', 2, BOP(*, 8), ['NAME', 'a']]
    >>> eval_tree(['MAP', ['PAR', 'x'], ['DELAY:SEQ', ['SEQ', ['NUM:REAL', '2'], ['BOP', '+'], ['NUM:REAL', '3']], ['BOP', '*'], ['SEQ', ['NUM:REAL', '6'], ['BOP', '+'], ['NAME', 'x']]]])
    ['PAR', 'x'] -> ['SEQ', 5, BOP(*, 8), ['SEQ', 6, BOP(+, 6), ['NAME', 'x']]]
    '''
    if not is_tree(tr): return tr
    type_ = tag(tr)
    Map.env = env
    if type_ not in delay_types:
        for i in range(1, len(tr)):
            tr[i] = eval_tree(tr[i], env)
    if type_ in subs_rules:
        tr = subs_rules[type_](tr)
    elif type_ in eval_rules and env:
        tr = eval_rules[type_](tr, env)
    elif type_ in exec_rules:
        exec_rules[type_](tr)
        return
    return tr


Map.match = match
Map.eval  = eval_tree
LOAD.run  = NotImplemented  # assign this in calc.py

delay_types = {'DELAY', 'DEF', 'FORM', 'BIND'}

subs_rules = {
    'ANS': ANS,                 'SYM': SYM,
    'EMPTY': EMPTY,             'NUM': NUM,
    'SEQ': SEQtoTREE,           'BOP': get_op(binary_ops),
    'LOP': get_op(unary_l_ops), 'ROP': get_op(unary_r_ops),
    'VAL_LST': LIST,            'SYM_LST': SYMLIST, 
    'GEN_LST': GENLIST,         'FIELD': FIELD,
    'ATTR': ATTR,               'MAP': MAP,
    'LET': LET,                 'SLICE': SLICE
}

eval_rules = {
    'NAME': NAME,               
    'PRINT': PRINT,             'EXP': eval_tree,
    'ENV': ENV,                 'MATCH': MATCH,
    'IF_ELSE': IF_ELSE,
}

exec_rules = {
    'DIR': DIR,                 'CONF': CONF,
    'LOAD': LOAD,               'IMPORT': IMPORT,
    'DEL': DEL,                 'DEF': DEF
}


if __name__ == "__main__":
    import doctest
    doctest.testmod()