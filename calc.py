from __classes import *
from __parser import *
from __builtins import *


py_eval = eval

global_env = Env({'ans':[]})
CM = calcMachine()


def eval_list(list_str, env):
    lst = get_list(list_str)
    if len(lst) == 1:
        comprehension = get_list(list_str, 'for')
        if len(comprehension) > 1:
            return toList(eval_comprehension(comprehension, env))
    value = lambda exp: eval_pure(exp, env)
    if lst and lst[-1][0] == '*':
        return list(map(value, lst[:-1])) + list(value(lst[-1][1:]))
    else:
        return list(map(value, lst))

def eval_subscription(lst, subscript_exp, env):
    def eval_listSubscript(lst, indices):
        if indices == []: return lst
        items = subscript(lst, indices[0])
        if isIterable(indices[0]):
            return [eval_listSubscript(item, indices[1:]) for item in items]
        else:
            return eval_listSubscript(items, indices[1:])
    slice_exps = get_list(subscript_exp, ':')
    if len(slice_exps) > 1:  # slice subscript
        slice_args = [eval_pure(exp, env) for exp in slice_exps]
        return lst[slice(*slice_args)]
    else:
        return eval_listSubscript(lst, eval_list(subscript_exp, env))

def eval_comprehension(comprehension, env):
    def gen_vals(exp, params, ranges):
        if params:
            segs = split(ranges[0], 'if')
            ran, conds = segs[0], segs[1:]
            for parvalue in eval_pure(ran, local_env):
                local_env[params[0]] = parvalue
                if all(eval_pure(cond, local_env) for cond in conds):
                     yield from gen_vals(exp, params[1:], ranges[1:])
        else:
            yield eval_pure(exp, local_env)
    exp, param_ranges = comprehension[0], comprehension[1:]
    params, ranges = zip(*[split(pr, 'in') for pr in param_ranges])
    params = [get_name(par) for par in params]
    local_env = env.make_subEnv()
    return gen_vals(exp, params, ranges)

def eval_cases(exp, env):
    cases = [split(case, ',') for case in split(exp, ';')]
    value = lambda exp: eval_pure(exp, env)
    for val in (value(exp) for exp, cond in cases[:-1] if value(cond)):
        return val
    else_case = cases[-1]
    if len(else_case) != 1:
        raise SyntaxError('invalid cases expression!')
    return value(else_case[0])

class function:
    def __init__(self, params, body, env=global_env):
        if params and params[-1][0] == '*':
            params[-1] = params[-1][1:]
            self.least_argc = len(params)-1
            self.fixed_argc = False
        else:
            self.least_argc = len(params)
            self.fixed_argc = True
        self.params = [get_name(s) for s in params]
        self.body = body.strip()
        self.env = env
    
    def __call__(self, *args):
        if not self.fixed_argc:
            if len(args) < self.least_argc:
                raise TypeError('inconsistent number of arguments!')
            args = list(args[:self.least_argc]) + [args[self.least_argc:]]
        elif len(args) != self.least_argc:
            raise TypeError('inconsistent number of arguments!')
        bindings = dict(zip(self.params, args))
        return eval_pure(self.body, self.env.make_subEnv(bindings))

    def __str__(self):
        return f"function of {'' if self.fixed_argc else '*'}{', '.join(self.params)}: {self.body}"


def get_binding(lexp, rexp, env=global_env):
    name, rest = get_name(lexp, False)
    if not rest:
        return name, eval_pure(rexp, env)
    else:
        type, params, rest = get_token(rest)
        if type != 'paren' or rest != '':
            raise SyntaxError('invalid variable name!')
        func = function(get_list(params), rexp, env.make_subEnv())
        func.env[name] = func  # enable recursion
        return name, func


def is_replacable(type, src_type):
    return type == src_type or type in ['name','paren','ans']

def is_applying(prev_val, prev_type, type):
    return type == 'paren' and isFunction(prev_val) \
        and is_replacable(prev_type, 'name')

def eval_pure(exp, env):
    # inner evaluation, without assignment
    if exp == '': return
    CM.begin()
    prev_type = None
    while exp:
        type, token, exp = get_token(exp)
        prev_val = None if CM.vals.empty() else CM.vals.peek()
        if is_applying(prev_val, prev_type, type):  # apply a function
            CM.push_val(CM.vals.pop()(*eval_list(token, env)))
            continue
        if all(is_replacable(t, 'number') for t in (type, prev_type)):
            CM.push_op(binary_ops['*'])
        if type == 'ans':
            id = -1 if len(token) == 1 else int(token[1:])
            try:
                CM.push_val(global_env['ans'][id])
            except IndexError:
                if id < 0:
                    id = len(global_env['ans']) + id
                raise ValueError(f'Answer No.{id} not found!')
        elif type == 'number':
            try:
                CM.push_val(py_eval(token))
            except Exception:
                raise SyntaxError(f'invalid number: {token}')
        elif type == 'name':
            CM.push_val(builtins[token] if token in builtins else env[token])
        elif type == 'op':
            if (prev_type in (None, 'op')) and token in unitary_l_ops:
                CM.push_op(unitary_l_ops[token])
            elif exp and token in binary_ops:
                CM.push_op(binary_ops[token])
            else:
                CM.push_op(unitary_r_ops[token])
        elif type == 'if':
            CM.push_op(Op('if', 'bin', lambda x, y: x if y else 'false', -5))
        elif type == 'else':
            CM.push_op(Op('else', 'bin', lambda x, y: y, -5))
            if CM.vals.peek() != 'false':
                CM.ops.pop(); break  # short circuit
        elif type == 'cases':
            CM.push_val(eval_cases(exp, env)); break
        elif type == 'paren':
            CM.push_val(eval_pure(token[1:-1], env))
        elif type == 'bracket':
            if isIterable(prev_val) and is_replacable(prev_type, 'bracket'):
                CM.push_val(eval_subscription(CM.vals.pop(), token, env))
            else: 
                CM.push_val(eval_list(token, env))
        elif type == 'brace':
            segs = get_list(token)
            if not segs or len(split(segs[0], ':')) == 1:  # lambda expression
                CM.push_val(function(segs, exp, env))
            else:  # local environment
                bindings = [get_binding(l, r, env) for l, r in \
                    [split(seg, ':') for seg in segs]]
                CM.push_val(eval_pure(exp, env.make_subEnv(dict(bindings))))
            break
        elif type == 'config':
            _, key, rest = get_token(exp)
            if key == 'frac': 
                binary_ops['/'].function = fractal_div
            elif key == 'deci': 
                binary_ops['/'].function = decimal_div
            elif key == 'prec': 
                getcontext().prec = py_eval(rest)
            elif key == 'matdisp':
                mode = rest.strip()
                if mode == 'normal':
                    matrix_format = normal_mat
                elif mode == 'latex':
                    matrix_format = latex_mat
                elif mode == 'table':
                    matrix_format = latex_table
                else: raise SyntaxError('invalid config!')
            else: raise SyntaxError('invalid config!')
            break
        else:
            raise SyntaxError('invalid token: %s' % token)
        prev_type = type
    return CM.calc()


def eval(exp):
    if exp == '': return
    assign_mark = exp.find(':=')
    words = exp.split()
    if words[0] == 'ENV':
        for name in global_env.bindings:
            if name == 'ans': continue
            print(f"{name}: {global_env[name]}")
        return
    elif words[0] == 'load':
        current_ans = global_env['ans'].copy()
        test = words[-1] == '-t'
        for filename in words[1:-1] if test else words[1:]:
            run(filename, test)
        global_env['ans'] = current_ans
        return
    elif assign_mark < 0:
        result = eval_pure(exp, global_env)
    else:  # an assignment
        lexp, rexp = exp[:assign_mark], exp[assign_mark+2:]
        name, value = get_binding(lexp, rexp)
        if any([name in lst for lst in (special_words, builtins, op_list)]):
            raise SyntaxError('word "%s" is protected!'%name)
        global_env[name] = value
        result = value

    if not (CM.vals.empty() and CM.ops.empty()):
        raise SyntaxError('invalid expression!')
    if result is not None:
        global_env['ans'].append(result)
    return result


def display(val):
    def pos_scinum_str(x):
        e = floor(log10(x))
        b = x/10**e
        return f'{b}10^{e}'
    if isNumber(val):
        if type(val) is Fraction: print(val)
        elif type(val) is complex:
            re, im = val.real, val.imag
            print(f"{re}{'' if im<0 else '+'}{im}i")
        elif abs(val) <= 0.001 or abs(val) >= 10000:
            if val == 0: print('0')
            elif val > 0: print(pos_scinum_str(val))
            else: print('-'+pos_scinum_str(-val))
        else: print(val)
    elif type(val) is list:
        if len(val) > 1 and type(val[0]) is list and all(
            [type(it) is list and len(it) == len(val[0])
            for it in val[1:]]):  # regarded as a matrix
            print(matrix_format(val))
        else:
            print('['+', '.join(map(str, val))+']')
    else:
        print(val)


def run(filename=None, test=False, start=0):
    def get_lines(filename):
        if filename:
            file = open(filename, 'r')
            return file.readlines()
        else:
            return iter(lambda: 0, 1)  # an infinite loop
    def split_exp_comment(line):
        comment_at = line.find('#')
        if comment_at < 0:
            return line, ''
        else:
            return line[:comment_at], line[comment_at+1:]
    def verify_answer(result, answer):
        if result == py_eval(answer):
            print('--- OK! ---')
        else:
            raise Warning('--- Fail! Expect %s ---' % answer)

    buffer, count = '', 0
    for line in get_lines(filename):
        if test and count < start:
            count += 1; continue
        try:
            print(f'({count})▶ ', end='')  # prompt
            line = line.strip() if filename else input()
            if filename: print(line)

            if line and line[-1] == '\\':
                buffer += line[:-1]
                continue  # join multiple lines
            elif buffer:
                line, buffer = buffer+line, ''
            if line and line[-1] == ';':
                line = line[:-1]
                show = False
            else: show = True

            exp, comment = split_exp_comment(line)
            result = eval(exp)
            if result is None: continue
            if show: display(result)

            ### test ###
            if test and comment:
                verify_answer(result, comment)

            count += 1

        except KeyboardInterrupt:
            return
        except (Warning if test else Exception) as err:
            if test:
                print(err)
                raise Warning
            print('Error:', err)
            CM.reset()
            
    if test:
        print('\nCongratulations, tests all passed in "%s"!\n'%filename)


### RUN ###
from sys import argv
if len(argv) > 1:
    if argv[1] == '-t':
        run("tests", True)
    else:
        run(argv[1])
else:
    run()
