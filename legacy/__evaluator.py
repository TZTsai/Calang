from __parser import get_list, get_params, get_name, get_token, split
from __builtins import *
from __classes import CalcMachine


history = []
CM = CalcMachine()
my_globals = {}


def eval_list(exp, env):

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


def eval_when(exp, env):
    "Support short circuit."
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


def eval_ans_id(token):
    if all(c == '_' for c in token):
        return -len(token)
    else:
        try:
            return int(token[1:])
        except:
            raise SyntaxError('invalid history expression!')


def make_closure(bindings, env, delim='='):
    sub_env = env.make_subEnv()
    for pair in bindings:
        _var, _exp = split(pair, delim, 2)
        add_bindings(_var, _exp, sub_env)
    return sub_env


def eval_closure(bindings, exp, env, delim='='):
    return calc_eval(exp, make_closure(bindings, env, delim))


def eval_singlevar_closure(token, exp, env):
    try:
        valexp, exp = split(exp, '->', 2)
    except ValueError:
        raise SyntaxError('invalid use of colon')
    binding = token + valexp
    return eval_closure([binding], exp, env, delim=':')


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


def calc_eval(exp, env):
    """ a pure function that evaluates exp in env """
    if exp == '': return

    # if-else: support short-circuit
    split_if = split(exp, 'if', 2)
    if len(split_if) > 1:
        try: if_exp, cond_exp, else_exp = split_if[0], *split(split_if[1], 'else', 2)
        except ValueError: raise SyntaxError('"else" not found to match "if"!')
        if calc_eval(cond_exp, env): return calc_eval(if_exp, env)        
        else: return calc_eval(else_exp, env)

    CM.begin()
    prev_type = None
    next_type, next_token, next_exp = get_token(exp)

    while exp:
        type_, token, exp = next_type, next_token, next_exp
        if exp: next_type, next_token, next_exp = get_token(exp)
        else: next_type = next_token = next_exp = None
        prev_val = CM.vals.peek()

        if is_applying(prev_val, prev_type, type_):  # apply a function
            func, args = CM.vals.pop(), eval_list(token, env)
            CM.push_val(func(*args))
            continue

        if all(is_replacable(t, 'number', 'symbol') for t in (type_, prev_type)):
            CM.push_op(binary_ops['.*'])

        if type_ == 'ans':
            try:
                id = eval_ans_id(token)
                CM.push_val(history[id])
            except IndexError:
                raise ValueError(f'Answer No.{id} not found!')
        elif type_ == 'number':
            try:
                CM.push_val(eval(token))
            except Exception:
                raise SyntaxError(f'invalid number: {token}')
        elif type_ == 'name':
            if next_token == ':':  # single variable closure
                CM.push_val(eval_singlevar_closure(token, exp, env))
                break
            if next_token == '->':
                CM.push_val(function([token], next_exp, env))
                break
            value = eval_name(token, env)
            CM.push_val(value)
        elif type_ == 'attribute':
            names = token.split('.')
            result = eval_name(names.pop(0), env)
            while names: result = getattr(result, names.pop(0))
            CM.push_val(result)
        elif type_ == 'symbol':
            CM.push_val(Symbol(token[1:]))
        elif type_ == 'op':
            if (prev_type in (None, 'op')) and token in unitary_l_ops:
                CM.push_op(unitary_l_ops[token])
            elif exp and token in binary_ops:
                CM.push_op(binary_ops[token])
            else:
                CM.push_op(unitary_r_ops[token])
                type_ = prev_type
        elif type_ == 'when':
            type_, token, exp = get_token(exp)
            if type_ != 'paren':
                raise SyntaxError('invalid when expression')
            CM.push_val(eval_when(token, env))
        elif type_ == 'paren':
            lst = get_list(token)
            if next_type == 'arrow':
                if lst and ':' in lst[0]:  # local variables
                    CM.push_val(eval_closure(lst, next_exp, env, delim=':'))
                else: # a function
                    CM.push_val(function(lst, next_exp, env))
                break
            if len(lst) != 1:
                raise SyntaxError('invalid syntax in parentheses')
            CM.push_val(calc_eval(lst[0], env))
        elif type_ == 'bracket':
            if exp and get_token(exp)[1] == ':':  # closure with unpacking
                CM.push_val(eval_singlevar_closure(token, exp, env))
                break
            elif is_iterable(prev_val) and is_replacable(prev_type, 'bracket'):
                CM.push_val(eval_subscription(CM.vals.pop(), token, env))
            else:
                CM.push_val(eval_list(token, env))
        elif type_ == 'brace':  # eval the token in python
            my_locals = env.all_bindings()
            my_locals['log'] = log_macro(env)
            result = eval(token[1:-1], my_globals, my_locals)
            if result: exp = str(result) + exp
            continue
        elif type_ in ('with', 'lambda'):
            i = first(lambda c: c.isspace(), token)
            lst = split(token[i:-1], ',')  # the last char is ':'
            if type_ == 'lambda':  # lst is the binding list
                CM.push_val(function(lst, exp, env))
            else:  # lst is the parameter list
                CM.push_val(eval_closure(lst, exp, env))
            break
        else:
            raise SyntaxError('invalid token: %s' % token)

        prev_type = type_

    return CM.calc()


function.evaluator = calc_eval