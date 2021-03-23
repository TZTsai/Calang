from functools import wraps
from copy import deepcopy
import re

from parse import calc_parse, is_name, is_tree, tree_tag
from builtin import operators, builtins
from funcs import Symbol, Array, is_list, is_function
from objects import Env, stack, Op, Attr, Function, Map, UnboundName, OperationError
from utils import debug
import config


def GlobalEnv():
    Global = Env(name='_global_', parent=Builtins)
    Global._ans = []
    return Global

Builtins = Env(name='_builtins_', binds=builtins)
Global = GlobalEnv()


def calc_eval(exp, env=None):
    # suppress output (and recording) if the last character is ';'
    suppress = exp[-1] == ';'
    if suppress: exp = exp[:-1]
    
    # parse the expression into a syntax tree
    tree, rest = calc_parse(exp)
    if rest: raise SyntaxError(f'syntax error in "{rest}"')
    
    if env is None: env = Global 
    
    try:  # evaluate the syntax tree
        result = eval_tree(tree, Global)
    except UnboundName:  # there is an unbound name in exp
        if config.symbolic:
            # force unbound names to be evaluated to symbols
            NAME.force_symbol = True
            result = eval_tree(tree, Global)  # retry
            NAME.force_symbol = False
        else: raise
    
    if result is not None and not suppress:
        # record and return the result
        Global._ans.append(result)
        return result


# substitution rules

def EMPTY(tr): return None

def EXPS(tr): return tr[-1]

def op_getter(op_type):
    ops = operators[op_type]
    return lambda tr: ops[tr[1]]

OPERATORS = {op_type: op_getter(op_type)
             for op_type, op_dict in operators.items()}

def COMPLEX(tr):
    re, pm, im = tr[1:]
    return re + im*1j if pm == '+' else re - im*1j

def REAL(tr):
    if len(tr) > 2: return eval(tr[1]+'e'+tr[2])
    else: return eval(tr[1])

def BIN(tr): return eval(tr[1])

def HEX(tr): return eval(tr[1])

def ATTR(tr): return Attr(tr[1])

def ANS(tr):
    s = tr[1]
    if all(c == '$' for c in s):
        id = -len(s)
    else:
        try: id = int(s[1:])
        except: raise SyntaxError('invalid history index!')
    return Global._ans[id]

def DIR(tr):
    if len(tr) == 1:
        field = Global
    else:
        field = tr[1]
        print(f"(dir): {field.dir()}")
    for name, val in field.items():
        print(f"{name}: {debug.log.format(val)}")
        
def INFO(tr):
    print(tr[1].__doc__)
        

def hold_tree(f):
    "A decorator that makes a substitution rule to hold the tree form."
    @wraps(f)
    def _f(tr): return tr if any(is_tree(t) for t in tr) else f(tr)
    return _f

@hold_tree
def PHRASE(tr):
    ops = stack()
    vals = stack()
    
    BOP = operators['BOP']
    adjoin = BOP['(adj)']
    apply = BOP['(app)']
    dot = BOP['.']
    
    def reduce():
        op = ops.pop()
        if op.type == 'BOP':
            args = vals.pop(-2), vals.pop(-1)
        else:
            args = vals.pop(),
        
        try:
            result = apply(op, args)
        except OperationError:
            if op is adjoin:  # adjoin failed, change to dot product
                push.prev = None
                push(args[0])
                push(dot)
                push(args[1])
                return
            else: raise
            
        vals.push(result)
                
    def push(x):
        if isinstance(x, Op):
            while ops:
                op = ops.peek()
                if x.priority <= op.priority:
                    reduce()
                else: break
            ops.push(x)
        else:
            if not (push.prev is None or isinstance(push.prev, Op)):
                if is_function(push.prev):
                    ops.push(apply)
                else:
                    push(adjoin)
            vals.push(x)
        push.prev = x

    push.prev = None
    for x in tr[1:]: push(x)
    while ops: reduce()
    val = vals.pop()
    assert not vals, 'sequence evaluation failed'
    return val

@hold_tree
def VAR(tr):
    field = tr[1]
    for attr in tr[2:]:
        field = attr.getFrom(field)
    return field

@hold_tree
def LIST(tr):
    lst = []
    for it in tr[1:]:
        if is_list(it) and it[0] == '(unpack)':
            lst.extend(it[1])
        else:
            lst.append(it)
    return tuple(lst)

@hold_tree
def ARRAY(tr):
    return Array(tr[1:])

SUBARR = LIST

# @hold_tree
# def SYM_LST(tr): return tuple(tr[1:])

# @hold_tree
# def SLICE(tr): return slice(*tr[1:])


## eval rules which require environment
special_names = {'super'}

def NAME(tr, env):
    name = format_string(tr[1], env)
    try:
        if name == 'super':
            if env is Global:
                raise EnvironmentError('no parent environment')
            else:
                return env.parent
        else:
            return env[name]
    except KeyError:
        if NAME.force_symbol:
            return Symbol(name)
        else:
            raise UnboundName(f"unbound symbol '{name}'")
        
def STR(tr, env):
    return format_string(tr[1], env)

def QUOTE(tr, env):
    return Symbol(format_string(tr[1], env))

def format_string(s, env, char='.'):
    # TODO: use the builtin evaluation of f-string
    def subs(match):
        s = match[1].strip()
        if s[-1] == '=':
            s = s[:-1]
            eq = 1
        else:
            eq = 0
        val = calc_eval(s, env)
        ss = debug.log.format(val)
        if eq: ss = '%s = %s' % (s, ss)
        return ss

    brace_pattern = '{(%s+?)}' % char
    return re.sub(brace_pattern, subs, s)

# def IF_ELSE(tr, env):
#     _, t_case, pred, f_case = tr
#     case = t_case if eval_tree(pred, env) else f_case
#     return eval_tree(case, env)

# def WHEN(tr, env):
#     *cases, default = tr[1:]
#     for _, cond, exp in cases:
#         if eval_tree(cond, env):
#             return eval_tree(exp, env)
#     return eval_tree(default, env)

def GENER(tr, env):
    def generate(exp, constraints):
        if constraints:
            constr = constraints[0]
            _, form, ran, *rest = constr
            binds, cond = [], None
            if rest and tree_tag(rest[0]) == 'WITH':
                binds = rest.pop(0)[1]
                binds = binds[1:] if tree_tag(binds) == 'ENV' else [binds]
            if rest: cond = rest[0]
            for val in eval_tree(ran, local, False):
                match(form, val, local)
                for bind in binds: BIND(deepcopy(bind), local)
                if not cond or eval_tree(cond, local, False):
                    yield from generate(exp, constraints[1:])
        else:
            yield eval_tree(exp, local, False)
    _, exp, *constraints = tr
    local = env.child()
    return tuple(generate(exp, constraints))

def ENV(tr, env):
    local = env.child()
    for t in tr[1:]: BIND(t, local)
    return local

MAP = Map  # the MAP evaluation rule is the same as Map constructor
Map.builtins = Builtins

def AT(tr, env):
    _, local, body = tr
    try:
        return eval_tree(body, env=local)
    except UnboundName:
        return eval_tree(body, env=env)

def BIND(tr, env):
    var, exp = tr[1:3]
    try: doc = tr[3][1][1:-1]
    except: doc = None
    define(var, exp, env, doc)
    
# def MATCH(tr, env):
#     _, form, val = tr
#     local = env.child()
#     match(form, val, local)
#     return local

def match(form, val, local: Env):
    try:
        _, pars, opt_pars, ext_par = form
        pars, opt_pars = pars[1:], opt_pars[1:]
        # remove the tags & make copies
        vals = list(val) if is_list(val) else [val]
    except:  # a single parameter
        if tree_tag(form) == 'PAR':
            par = form[1]
            local[par] = val
            return
        else: raise
    
    if len(pars) > len(vals):
        raise TypeError(f'not enough arguments in {vals}')
    
    for par in pars:
        val = vals.pop(0)
        if is_name(par): 
            local[par] = val
        else:
            match(par, val, local)
            
    while opt_pars and vals:
        define(opt_pars.pop(0)[0], vals.pop(0), local)
    for opt_par, default in opt_pars:
        define(opt_par, default, local)
        
    if ext_par is not None:
        local[ext_par] = tuple(vals)
    elif vals:
        raise TypeError(f'too many arguments in {vals}')
        

def define(var, exp, env, doc=None):

    def def_(name, val, env):
        if name == '_':
            return  # ignore assignments of '_'
        if name in special_names:
            raise NameError('"%s" cannot be bound' % name)

        if isinstance(val, Map):
            val.__name__ = name
        elif isinstance(val, Env):
            val.name = name
                
        if doc:  # add __doc__
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
    
    var_tag = tree_tag(var)

    # evaluate the exp
    if var_tag == 'FUNC':
        form = eval_tree(var[2], env)  # eval the opt_pars
        val = Map(['MAP', form, exp], env)
    else:
        val = eval_tree(exp, env)

    # bind the variable(s)
    if var_tag == 'VARS':
        def_all(var, val, env)
    else:
        name = var[1] if var_tag == 'VAR' else var[1][1]
        def_(name, val, env)
        
def split_field(tr, env):
    if is_name(tr[1]):
        parent, attr = env, tr[1]
    else:
        parent, attr = tr[:-1], tr[-1][1]
        parent = eval_tree(parent, env) if len(parent) > 1 else env
    return parent, attr


# these rules are commands in the calc

def DEF(tr):
    _, field, body = tr
    upper, field_name = split_field(field, Global)
    field = upper[field_name]
    if not isinstance(field, Env):
        # if field is not Env instance, convert it into one
        field = upper.child(field, field_name)
        upper[field_name] = field
    BIND(body, field)
    
def DEL(tr):
    for t in tr[1:]:
        field, attr = split_field(t, Global)
        field.delete(attr)

def LOAD(tr):
    test = '-t' in tr
    verbose = '-v' in tr
    overwrite = '-w' in tr
    path = '%s.cal' % '/'.join(tr[1].split('.'))

    global Global
    current_global = Global
    Global = GlobalEnv()  # a new global env
    debug.log.indent += 2
    LOAD.run(path, test, start=0, verbose=verbose)
    debug.log.indent -= 2
    
    if overwrite:
        current_global.update(Global)
    else:
        for name in Global:
            if name not in current_global:
                current_global[name] = Global[name]
            else:
                print(f'name "{name}" not loaded because it is already bound')
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
            if verbose:
                print(f'imported: {name}')
            if callable(val):
                val = Function(val)
            Global[name] = val

def CONF(tr):
    conf = tr[1]
    if conf in ('prec', 'precision'):
        if len(tr) == 2:
            return config.precision
        else:
            config.precision = max(1, tr[2])
    elif conf == 'tolerance':
        if len(tr) == 2:
            return config.tolerance
        else:
            val = eval_tree(tr[2])
            config.tolerance = float(val)
    elif hasattr(config, conf):
        if len(tr) == 2:
            return getattr(config, conf)
        else:
            val = eval_tree(tr[2])
            if val == 'off': val = False
            setattr(config, conf, val)
    else:
        raise ValueError('no such field in the config')
    
def EXIT(tr): raise KeyboardInterrupt
    

def eval_tree(tree, env=None, mutable=True):
    if not is_tree(tree):
        return tree
    if not mutable:
        tree = deepcopy(tree)
    tag = tree_tag(tree)
    
    if tag not in dont_eval and env:
        unb_flag = False
        for i, t in enumerate(tree):
            try: tree[i] = eval_tree(t, env)
            except UnboundName: unb_flag = True
        if unb_flag: raise UnboundName
        
    if tag in subs_rules:
        return subs_rules[tag](tree)
    elif tag in eval_rules and env:
        return eval_rules[tag](tree, env)
    elif tag in exec_rules:
        return exec_rules[tag](tree)
    else:
        return tree


NAME.force_symbol = False
# assign LOAD.run in 'calc.py'
LOAD.run  = NotImplemented
Map.match = match
Map.eval  = eval_tree


delay_types = {
    'MAP',      'GENER',    'BIND',     'AT' 
    'ENV',      'PHRASE'
}

subs_types = {
    'EXPS',     'EMPTY',    'DIR',      'ANS',
    'REAL',     'COMPLEX',  'BIN',      'HEX',
    'INFO',     'LIST',     'ARRAY'
}
subs_rules = {name: eval(name) for name in subs_types}
subs_rules.update(OPERATORS)

eval_types = {
    'NAME',     'MAP',      'ENV',      'AT',
    'QUOTE',    'BIND',     'GENER',    'PHRASE',
    'STR'
}
eval_rules = {name: eval(name) for name in eval_types}

exec_types = {
    'DEL',      'DEF',      'LOAD',     'IMPORT',
    'CONF',     'EXIT'
}
exec_rules = {name: eval(name) for name in exec_types}

dont_eval = delay_types | exec_types
# trees of these types are not recursively evaluated


if __name__ == "__main__":
    import doctest
    doctest.testmod()
