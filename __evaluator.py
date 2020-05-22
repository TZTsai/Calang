from __parser import get_list, get_params, get_name, get_token, split
from __builtins import *
from __classes import CalcMachine


history = []
CM = CalcMachine()


def eval_list(exp, env):
    comprehension = get_list(exp, '|')
    if len(comprehension) > 1:
        return eval_comprehension(comprehension, env)

    def value(exp): return calc_eval(exp, env)

    lst = get_list(exp)
    result = []
    for exp in lst:
        if not exp:
            raise SyntaxError('invalid list syntax')
        if exp[0] == '*':
            result.extend(value(exp[1:]))
        else:
            result.append(value(exp))
    return tuple(result)


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


# def eval_set(exp, env):
#     try:
#         varstr, constr = get_list(exp, '|')
#     except ValueError:
#         return set(eval_list(exp, env))
#     def getvar(s):
#         if len(t := split(s, 'in')) == 2:
#             return t[0], calc_eval(t[1], env)
#         else:
#             return s, None
#     vars_ = [getvar(s) for s in split(varstr, ',')]
#     constr = function(list(zip(*vars_))[0], constr, env)
#     return GeneralSet(vars_, constr)


def eval_cases(exp, env):
    cases = [split(case, ':', 2) for case in get_list(exp)]
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
        return int(token[1:])


def eval_closure(bindings, exp, env, delim='='):
    sub_env = env.make_subEnv()
    for pair in bindings:
        _var, _exp = split(pair, delim, 2)
        add_bindings(_var, _exp, sub_env)
    return calc_eval(exp, sub_env)


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
            value = function(get_list(params), rexp, env.make_subEnv())
            value._env[name] = value  # enable recursion
        elif not rest:  # a single variable
            value = calc_eval(rexp, env) if type(rexp) is str else rexp
        else:
            raise SyntaxError('invalid variable name!')
        
        if value is None: raise ValueError(f'assigning {name} to None!')
        env[name] = value

    return value


def is_replacable(type_, *replaced_types):
    return type_ in replaced_types + ('name', 'paren', 'ans')


def is_applying(prev_val, prev_type, type_):
    return type_ == 'paren' and is_function(prev_val) \
        and is_replacable(prev_type, 'name')


def calc_eval(exp, env):
    """ a pure function that evaluates exp in env """
    # inner evaluation
    if exp == '': return
    CM.begin()
    prev_type = None
    while exp:
        type_, token, exp = get_token(exp)
        prev_val = None if CM.vals.empty() else CM.vals.peek()
        if is_applying(prev_val, prev_type, type_):  # apply a function
            func, args = CM.vals.pop(), eval_list(token, env)
            CM.push_val(func(*args))
            continue
        if all(is_replacable(t, 'number', 'symbol') for t in (type_, prev_type)):
            CM.push_op(binary_ops['*'])
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
            if exp: 
                next_type, _, rest = get_token(exp)
                if next_type == 'colon':  # single variable closure
                    CM.push_val(eval_singlevar_closure(token, exp, env))
                    break
                if next_type == 'arrow':
                    CM.push_val(function([token], rest, env))
                    break
            CM.push_val(eval_name(token, env))
        elif type_ == 'symbol':
            CM.push_val(Symbol(token[1:]))
        elif type_ == 'op':
            if (prev_type in (None, 'op')) and token in unitary_l_ops:
                CM.push_op(unitary_l_ops[token])
            elif exp and token in binary_ops:
                CM.push_op(binary_ops[token])
            else:
                CM.push_op(unitary_r_ops[token])
        elif type_ == 'if':
            CM.push_op(Op('bin', priority=-5,
                          function=standardize('if', lambda x, y: x if y else None)))
        elif type_ == 'else':
            CM.push_op(Op('bin', standardize('else', lambda x, y: y), -5))
            if CM.vals.peek() is not None:
                CM.ops.pop()
                break  # short circuit
        elif type_ == 'cases':
            type_, token, exp = get_token(exp)
            if type_ != 'paren':
                raise SyntaxError('invalid cases expression')
            CM.push_val(eval_cases(token, env))
        elif type_ == 'paren':
            lst = get_list(token)
            if exp: 
                next_type, _, body = get_token(exp)
                if next_type == 'arrow':
                    if lst and ':' in lst[0]:  # local variables
                        CM.push_val(eval_closure(lst, body, env, delim=':'))
                    else: # a function
                        CM.push_val(function(lst, body, env))
                    break
            if len(lst) != 1:
                raise SyntaxError('invalid syntax in parentheses')
            CM.push_val(calc_eval(lst[0], env))
        elif type_ == 'bracket':
            if exp and get_token(exp)[0] == 'colon':  # closure with unpacking
                CM.push_val(eval_singlevar_closure(token, exp, env))
                break
            elif is_iterable(prev_val) and is_replacable(prev_type, 'bracket'):
                CM.push_val(eval_subscription(CM.vals.pop(), token, env))
            else:
                CM.push_val(eval_list(token, env))
        # elif type_ == 'brace':
        #     # experiment feature
        #     CM.push_val(eval_set(token, env))
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
    result = CM.calc()
    return result


function._eval = calc_eval