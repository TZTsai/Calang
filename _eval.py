from _parser import calc_parse
from _builtins import binary_ops, unary_l_ops, unary_r_ops, builtins
from _funcs import Symbol
from _obj import Env, stack, Op, Attr, Map, split_pars
import config


Builtins = Env(name='_builtins_', binds=builtins)

def GlobalEnv():
    Global = Env(name='_global_', parent=Builtins)
    Global._ans = []
    return Global

Global = GlobalEnv()


def calc_eval(exp):  # only for testing; calc_exec will use eval_tree
    suppress = exp[-1] == ';'
    if suppress: exp = exp[:-1]
    tree, rest = calc_parse(exp)
    if rest: raise SyntaxError(f'syntax error in "{rest}"')
    result = eval_tree(tree, Global)
    if result is not None and not suppress:
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

def is_list(tr): return type(tr) in (tuple, list)
def is_tree(tr): return type(tr) is list and tr and is_str(tr[0])
def is_str(tr): return type(tr) is str

def get_op(ops):
    def get(tr): return ops[tr[1]]
    return get


# substitution rules

def SYM(tr): return Symbol(tr[1])

def EMPTY(tr): return None

def ANS(tr):
    s = tr[1]
    if all(c == '_' for c in s):
        id = -len(s)
    else:
        try: id = int(s[1:])
        except: raise SyntaxError('invalid history index!')
    return Global._ans[id]

def NUM(tr):
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
    
    def apply(op, *vals):
        if any(type(v) is c for v in vals for c in (list, str)):
            raise RuntimeError
        return op(*vals)

    def reduce():
        # try to evaluate or reduce several previous trees to a bigger tree
        op = ops.peek()
        tag = op.type
        if tag == 'BOP':
            n2 = pop_val()
            op = pop_op()
            n1 = pop_val()
            try:
                n = apply(op, n1, n2)
            except RuntimeError:
                n = ['SEQ', n1, op, n2]
        else:
            if tag == 'LOP':
                n1 = pop_val()
                op = pop_op()
                try: 
                    n = apply(op, n1)
                except RuntimeError:
                    n = ['SEQ', op, n1]
            else:
                op = pop_op()
                n1 = pop_val()
                try:
                    n = apply(op, n1)
                except RuntimeError:
                    n = ['SEQ', n1, op]
        stk.push(n)

    def push(x):
        if isinstance(x, Op):
            while ops:
                op = ops.peek()
                if x.priority <= op.priority: reduce()
                else: break
            ops.push(x)
        elif stk and not isinstance(stk.peek(), Op):
            push(binary_ops[''])
        if isinstance(x, Env):
            if hasattr(x, 'val'):
                x = x.val
        stk.push(x)

    for x in tr[1:]: push(x)
    while ops: reduce()
    assert len(stk) == 1
    return pop_val()

def FIELD(tr):
    if is_tree(tr[1]):
        return tr
    field = tr[1]
    for attr in tr[2:]:
        field = attr.getFrom(field)
    return field

def LIST(tr):
    lst = []
    for it in tr[1:]:
        if is_tree(it):
            if tag(it) == 'UNPACK':
                lst.extend(it[1])
            else:
                return tr
        else:
            lst.append(it)
    return tuple(lst)

def SYMLIST(tr): return tr[1:]

def SLICE(tr): return slice(*tr[1:])
 
def ATTR(tr): return Attr(tr[1])

def AT(tr):
    if len(tr) == 2:  # single variable
        return FIELD(tr)
    else:  # function
        return SEQtoTREE(tr)
    
def LINE(tr):
    return tr[-1]

def VAL(tr):
    # a VAL tree will only occur when it has a PRINT in the end
    return tr[1]


## eval rules which require environment

def NAME(tr, env):
    name = tr[1]
    if name == 'this': return env
    try: return env[name]
    except KeyError:
        if env is Global:
            if config.symbolic:
                return Symbol(name)
            else:
                raise NameError(f'unbound symbol \'{tr}\'')
        else:
            return tr

def PRINT(tr, env):
    exec('print(f"%s")' % tr[1][1:-1], env.all())
    return 'PRINTED'

def IF_ELSE(tr, env):
    _, t_case, cond, f_case = tr
    return eval_tree(t_case if eval_tree(cond, env)
                     else f_case, env)

def WHEN(tr, env):
    *cases, default = tr[1:]
    for _, cond, exp in cases:
        if eval_tree(cond, env):
            return eval_tree(exp, env)
    return eval_tree(default, env)

def GEN_LST(tr, env):
    def generate(exp, constraints):
        if constraints:
            constr = constraints.pop(0)
            _, par, ran, *spec = constr
            par = par[1]  # remove the tag
            if spec: spec = spec[0]
            for val in eval_tree(ran, local):
                local[par] = val
                if not spec or eval_tree(spec, local):
                    yield from generate(exp, constraints)
        else:
            yield eval_tree(exp, local)
    _, exp, *constraints = tr
    local = env.child()
    return tuple(generate(exp, constraints))

def ENV(tr, env):
    local = env.child()
    if len(tr) == 2 and isinstance(tr[1], Env):
        return tr[1]
    for t in tr[1:]:
        _, var, exp = t
        define(var, exp, local)
    return local

def MAP(tr, env):
    drop_tag(tr[2], 'DELAY')
    return Map(tr, env)

def LET(tr, env):
    _, local, body = tr
    if not isinstance(local, Env):
        return tr
    drop_tag(body, 'DELAY')
    result = eval_tree(body, env=local)
    if isinstance(result, Env):
        result._parent = local
    elif is_tree(result):
        result = eval_tree(result, env=env)
    return result
    
def MATCH(tr, env):
    _, form, val = tr
    local = env.child()
    match(form, val, local)
    return local

def match(form, val, local: Env):
    vals = list(val) if is_list(val) else [val]

    if form[0] != 'FORM': split_pars(form, local)
    _, pars, opt_pars, ext_par = form

    if len(pars) > len(vals):
        raise ValueError(f'not enough items in {vals} to match')

    for par in pars:
        val = vals.pop(0)
        if is_str(par): local[par] = val
        else: match(par, val, local)
    opt_pars = opt_pars[:]  # the original opt_pars must not be mutated
    while opt_pars and vals:
        define(opt_pars.pop(0)[0], vals.pop(0), local)
    for opt_par, default in opt_pars:
        define(opt_par, default, local)
    if ext_par:
        local[ext_par] = tuple(vals)


# these rules are commands in the calc

def DIR(tr):
    if len(tr) == 1:
        field = Global
    else:
        field = tr[1]
        print(f"(dir): {field.dir()}")
    for name, val in field.items():
        print(f"{name}: {val}")

def LOAD(tr):
    script_path = 'scripts/' + '/'.join(tr[1].split('.')) + '.cal'
    test = '-t' in tr
    verbose = '-v' in tr
    overwrite = '-w' in tr

    global Global
    current_global = Global
    Global = GlobalEnv()  # a new global env
    LOAD.run(script_path, test, start=0, verbose=verbose)
    
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
    if conf in ('prec', 'precision'):
        if len(tr) == 2:
            print(config.precision)
        else:
            config.precision = max(1, int(tr[2]))
    elif conf == 'tolerance':
        if len(tr) == 2:
            print(config.tolerance)
        else:
            config.tolerance = float(tr[2])
    elif hasattr(config, conf):
        if len(tr) == 2:
            print(getattr(config, conf))
        else:
            setattr(config, conf, tr[2] in ('on', '1'))
    else:
        raise ValueError('no such field in the config')

def DEL(tr):
    for t in tr[1:]:
        field, attr = split_field(t)
        field.delete(attr)

def DEF(tr):
    i = 1
    to_def = tr[i]; i+=1
    if tag(tr[i]) == 'AT':
        at = tr[i]; i+=1
    else:
        at = None
    exp = tr[i]; i+=1
    try:
        assert tag(tr[i]) == 'DOC'
        doc = tr[i][1][1:-1]
    except:
        doc = None
    define(to_def, exp, Global, at, doc)


def define(to_def, exp, env, at=None, doc=None):
    
    def def_(name, val, env):
        if isinstance(val, Map):
            val.__name__ = name
        elif isinstance(val, Env):
            val.name = name
            if env is not Global:
                val.env = env
                
        if doc:
            if not isinstance(val, Env):
                val = Env(val, name=name)
            try: val.__doc__ += '\n' + doc
            except: val.__doc__ = doc
            
        env[name] = val

    def def_all(vars, val, env):
        t, vars = vars[0], vars[1:]
        if t == 'VARS':
            assert is_list(val), 'vars assigned to non-list'
            assert len(vars) == len(val), 'list lengths mismatch'
            for var, item in zip(vars, val):
                def_all(var, item, env)
        else:
            def_(vars[0], val, env)
    
    # evaluate the env
    if tag(to_def) == 'TO_DEF':
        assert env is Global    # attributes can only be defined in Global
        grandparent, parent_name = split_field(to_def[:-1])
        env = to_env_if_not(grandparent, parent_name)
        # if parent is not Env, convert it to Env
        to_def = to_def[-1]
    
    tag_ = tag(to_def)

    # evaluate the exp
    if tag_ == 'FUNC':
        form = to_def[2]
        val = Map(['MAP', form, exp], env, at)
    else:
        assert at is None, 'invalid use of @'
        val = eval_tree(exp, env)

    # bind the variable(s)
    if tag_ == 'VARS':
        def_all(to_def, val, env)
    else:
        name = to_def[1] if tag_ == 'NAME' else to_def[1][1]
        def_(name, val, env)
        
def split_field(tr):
    if tr[0] == 'NAME':
        attr = tr[1]
        parent = Global
    elif tr[0] == 'FIELD':
        attr = tr.pop()[1]
        parent = eval_tree(tr, Global) if len(tr) > 1 else Global
    else:
        raise TypeError('wrong type for split_field')
    return parent, attr

def to_env_if_not(parent, attr):
    val = parent[attr]
    if isinstance(val, Env):
        return val  # already Env
    val = parent.child(val, attr)
    parent[attr] = val
    return val



def eval_tree(tree, env):
    if not is_tree(tree): return tree
    type_ = tag(tree)
    tr = tree[:]  # make a copy so that `tree` is not modified
    if type_ not in delay_types:
        for i in range(1, len(tr)):
            tr[i] = eval_tree(tr[i], env)
    if type_ in subs_rules:
        tr = subs_rules[type_](tr)
    elif type_ in eval_rules and env is not None:
        tr = eval_rules[type_](tr, env)
    elif type_ in exec_rules:
        exec_rules[type_](tr)
        return
    return tr


Map.match = match
Map.eval  = eval_tree


LOAD.run  = None  # set this in calc.py

delay_types = {
    'DELAY',    'DEF',      'BIND',     'IF_ELSE',
    'DEL',      'WHEN',     'GEN_LST',  'PAR_LST',
    'FORM'
}

subs_rules = {
    'ANS': ANS,                 'SYM': SYM,
    'EMPTY': EMPTY,             'NUM': NUM,
    'SEQ': SEQtoTREE,           'BOP': get_op(binary_ops),
    'LOP': get_op(unary_l_ops), 'ROP': get_op(unary_r_ops),
    'VAL_LST': LIST,            'SYM_LST': SYMLIST, 
    'IDC_LST': LIST,            'LINE': LINE,
    'FIELD': FIELD,             'ATTR': ATTR,
    'SLICE': SLICE,             'AT': AT,
    'VAL': VAL
}

eval_rules = {
    'NAME': NAME,               'MAP': MAP,
    'PRINT': PRINT,             'EXP': eval_tree,
    'ENV': ENV,                 'MATCH': MATCH,
    'IF_ELSE': IF_ELSE,         'GEN_LST': GEN_LST,
    'WHEN': WHEN,               'LET': LET,
}

exec_rules = {
    'DIR': DIR,                 'CONF': CONF,
    'LOAD': LOAD,               'IMPORT': IMPORT,
    'DEL': DEL,                 'DEF': DEF
}


if __name__ == "__main__":
    import doctest
    doctest.testmod()
