from _builtins import *
from _funcs import *
from _obj import CalcStack, Env


Global = Env()
Global._ans = []
history = []

eval_rules = {
    'ANS'
}



def eval_list(tr, env):
    assert tr[0] == 'LST'
    

    comprehension = get_list(exp, '|')
    if len(comprehension) > 1:
        return eval_comprehension(comprehension, env)

    def eval_inner(s):
        exps = split(s, ',')
        result = []
        for exp in exps:
            if not exp: raise SyntaxError('invalid list syntax')
            if exp[0] == function.vararg_char: 
                result.extend(calc_eval(exp[1:], env))
            else:
                result.append(calc_eval(exp, env))
        return result

    # new feature: ';' can be used for a depth-2 list
    lst = get_list(exp, ';')
    if len(lst) == 1:
        return tuple(eval_inner(lst[0]))
    else:
        return tuple(eval_inner(_exp) for _exp in lst)


def eval_subscription(lst, subscript_exp, env):
    def eval_index(index_exp):
        slice_args = [calc_eval(exp, env) for exp in split(index_exp, ':')]
        if len(slice_args) > 1:
            return slice(*slice_args)
        else:
            return slice_args[0]
    subscript_exps = get_list(subscript_exp)
    if not subscript_exps:
        raise SyntaxError('invalid subscript')
    if len(subscript_exps) == 1:
        return index(lst, eval_index(subscript_exps[0]))
    return subscript(lst, tuple(map(eval_index, subscript_exps)))


def eval_comprehension(comprehension, env):
    def gen_vals(exp, constraints):
        if constraints:
            constr = constraints[0]
            try:
                param, range_, spec = *split(constr[0], 'in'), constr[1:]
            except ValueError:
                raise SyntaxError('no range provided, use \'in\'')
            param = get_name(param)
            for val in calc_eval(range_, local_env):
                local_env[param] = val
                if not spec or calc_eval(spec[0], local_env):
                    yield from gen_vals(exp, constraints[1:])
        else:
            yield calc_eval(exp, local_env)

    if len(comprehension) != 2:
        raise SyntaxError('Bad comprehension syntax!')
    exp, constraint = comprehension
    constraints = [split(constr, 'and', 2) for constr in split(constraint, ',')]
    local_env = env.make_subEnv()
    return tuple(gen_vals(exp, constraints))


    cases = [split(case, ',', 2) for case in get_list(exp, ';')]
    def value(exp): return calc_eval(exp, env)
    try:
        for val in (value(exp) for cond, exp in cases if value(cond)):
            return val
    except ValueError:
        return value(cases[-1][0])


def eval_name(token, env):
    try:
        val = env[token]
    except KeyError:
        if token in builtins:
            val = builtins[token]
        elif config.all_symbol:
            val = Symbol(token)
        else:
            raise NameError(f'unbound symbol \'{token}\'')
    return val


def eval_ans(exp):
    try: 
        id = -len(exp) if same(exp) else int(exp[1:])
        return Global._ans[id]
    except: 
        raise SyntaxError('invalid history index!')


def make_closure(bindings, env, delim='='):
    sub_env = env.make_subEnv()
    for pair in bindings:
        _var, _exp = split(pair, delim, 2)
        add_bindings(_var, _exp, sub_env)
    return sub_env


def eval_closure(bindings, exp, env, delim='='):
    return calc_eval(exp, make_closure(bindings, env, delim))


def add_bindings(lexp, rexp, env):
    if  '[' in lexp:  # need unpacking
        lexp = lexp.strip()
        lst = get_list(lexp)
        value = calc_eval(rexp, env) if type(rexp) is str else rexp
        if len(lst) != len(value):
            raise ValueError("incorrect number of variables for unpacking")
        for _lexp, _rexp in zip(lst, value):
            add_bindings(_lexp, _rexp, env)

    else:
        name, rest = get_name(lexp, no_rest=False)
        if any(name in names for names in (special_words, builtins, op_list)):
            raise SyntaxError('word "%s" is protected!' % name)

        if '(' in lexp:  # bind to a function
            type_, params, rest = get_token(rest)
            if type_ != 'paren' or rest != '':
                raise SyntaxError('invalid variable name!')
            value = function(get_list(params), rexp, env, name)
            value._env[name] = value  # enable recursion
        elif not rest:  # a single variable
            value = calc_eval(rexp, env) if type(rexp) is str else rexp
        else:
            raise SyntaxError('invalid variable name!')
        
        if value is None: raise ValueError(f'assigning {name} to None!')
        env[name] = value

    return value


def eval_object(parent, exp, env):
    pass


def is_replacable(type_, *replaced_types):
    return type_ in replaced_types + ('name', 'paren', 'ans')


def is_applying(prev_val, prev_type, type_):
    return type_ == 'paren' and is_function(prev_val)


def log_macro(env):
    def value(arg):
        try: return env[arg]
        except: return '??'
    def log(*args):
        if config.debug:
            print(env.frame*'  ' + ', '.join(f'{arg}={value(arg)}' for arg in args))
    return log
