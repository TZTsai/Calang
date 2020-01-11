from __classes import *
from __parser import *
from __builtins import *
from __formatter import *

py_eval = eval

global_env = Env({'ans': []})
CM = calcMachine()


def eval_list(list_str, env):
    lst = get_list(list_str)
    if len(lst) == 1:
        comprehension = get_list(list_str, 'for')
        if len(comprehension) > 1:
            return eval_comprehension(comprehension, env)
    value = lambda exp: calc_eval(exp, env)
    if lst and lst[-1][0] == '*':
        return tuple(map(value, lst[:-1])) + tuple(value(lst[-1][1:]))
    else:
        return tuple(map(value, lst))


def eval_subscription(lst, subscript_exp, env):
    def eval_listSubscript(lst, indices):
        if not indices: return lst
        items = subscript(lst, indices[0])
        if is_iterable(indices[0]):
            return tuple(eval_listSubscript(item, indices[1:]) for item in items)
        else:
            return eval_listSubscript(items, indices[1:])

    slice_exps = get_list(subscript_exp, ':')
    if len(slice_exps) > 1:  # slice subscript
        slice_args = [calc_eval(exp, env) for exp in slice_exps]
        return lst[slice(*slice_args)]
    else:
        return eval_listSubscript(lst, eval_list(subscript_exp, env))


def eval_comprehension(comprehension, env):
    def gen_vals(exp, params, ranges):
        if params:
            segs = split(ranges[0], 'if')
            ran, conds = segs[0], segs[1:]
            for parvalue in calc_eval(ran, local_env):
                local_env[params[0]] = parvalue
                if all(calc_eval(cond, local_env) for cond in conds):
                    yield from gen_vals(exp, params[1:], ranges[1:])
        else:
            yield calc_eval(exp, local_env)

    exp, param_ranges = comprehension[0], comprehension[1:]
    params, ranges = zip(*[split(pr, 'in') for pr in param_ranges])
    params = [get_name(par) for par in params]
    local_env = env.make_subEnv()
    return tuple(gen_vals(exp, params, ranges))


def eval_cases(exp, env):
    cases = [split(case, ',') for case in split(exp, ';')]
    value = lambda exp: calc_eval(exp, env)
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
            self.least_argc = len(params) - 1
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
            args = args[:self.least_argc] + (args[self.least_argc:],)
        elif len(args) != self.least_argc:
            raise TypeError('inconsistent number of arguments!')
        bindings = dict(zip(self.params, args))
        return calc_eval(self.body, self.env.make_subEnv(bindings))

    def __str__(self):
        return f"function of {'' if self.fixed_argc else '*'}{', '.join(self.params)}: {self.body}"


def get_binding(lexp, rexp, env=global_env):
    name, rest = get_name(lexp, False)
    if not rest:
        return name, calc_eval(rexp, env)
    else:
        type, params, rest = get_token(rest)
        if type != 'paren' or rest != '':
            raise SyntaxError('invalid variable name!')
        func = function(get_list(params), rexp, env.make_subEnv())
        func.env[name] = func  # enable recursion
        return name, func


def is_replacable(type, src_type):
    return type == src_type or type in ['name', 'paren', 'ans']


def is_applying(prev_val, prev_type, type):
    return type == 'paren' and is_function(prev_val) \
           and is_replacable(prev_type, 'name')


def calc_eval(exp, env):
    # inner evaluation
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
        elif type == 'symbol':
            CM.push_val(sympy.Symbol(token[1:]))
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
                CM.ops.pop();
                break  # short circuit
        elif type == 'cases':
            CM.push_val(eval_cases(exp, env));
            break
        elif type == 'paren':
            CM.push_val(calc_eval(token[1:-1], env))
        elif type == 'bracket':
            if is_iterable(prev_val) and is_replacable(prev_type, 'bracket'):
                CM.push_val(eval_subscription(CM.vals.pop(), token, env))
            else:
                CM.push_val(eval_list(token, env))
        elif type == 'brace':
            segs = get_list(token)
            if not segs or len(split(segs[0], ':')) == 1:  # lambda expression
                CM.push_val(function(segs, exp, env))
            else:  # local environment
                bindings = (get_binding(l, r, env) for l, r in
                            [split(seg, ':') for seg in segs])
                CM.push_val(calc_eval(exp, env.make_subEnv(dict(bindings))))
            break
        else:
            raise SyntaxError('invalid token: %s' % token)
        prev_type = type
    return CM.calc()


def calc_exec(exp):
    if exp == '': return
    words = exp.split()
    if words[0] == 'ENV':
        for name in global_env.bindings:
            if name == 'ans': continue
            print(f"{name}: {global_env[name]}")
        return
    elif words[0] == 'load':
        current_ans = global_env['ans'].copy()
        test = verbose = True
        try:
            words.remove('-t')
        except:
            test = False
        try:
            words.remove('-v')
        except:
            verbose = False
        for filename in words[1:]:  # default folder: ./modules
            run('modules/' + filename, test, 0, verbose)
        global_env['ans'] = current_ans
        return
    elif words[0] == 'import':
        for modules in words[1:]:
            locals = {}
            exec('from pymodules.%s import definitions' % modules, globals(), locals)
            definitions = locals['definitions']
            global_env.define(definitions)
            return set(definitions)
    elif words[0] == 'format':
        if len(words) < 3:
            raise SyntaxError("invalid format setting")
        if words[1] == 'prec':
            prec = py_eval(words[2])
            format_config.prec = prec
        elif words[1] == 'matrix':
            mode = words[2]
            if mode == 'normal':
                format_config.matrix = matrix
            elif mode == 'tex_mat':
                format_config.matrix = latex_matrix
            elif mode == 'tex_table':
                format_config.matrix = latex_table
            else:
                raise SyntaxError('invalid matrix format setting')
        else:
            raise SyntaxError('invalid format setting')
        return
    else:
        assign_mark = exp.find(':=')
        if assign_mark < 0:
            result = calc_eval(exp, global_env)
        else:  # an assignment
            lexp, rexp = exp[:assign_mark], exp[assign_mark + 2:]
            name, value = get_binding(lexp, rexp)
            if any(name in lst for lst in (special_words, builtins, op_list)):
                raise SyntaxError('word "%s" is protected!' % name)
            global_env[name] = value
            result = value

    if not (CM.vals.empty() and CM.ops.empty()):
        raise SyntaxError('invalid expression!')
    if result is not None:
        global_env['ans'].append(result)
    return result


def run(filename=None, test=False, start=0, verbose=True):
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
            return line[:comment_at], line[comment_at + 1:]

    def verify_answer(exp, result, answer, verbose):
        if result == py_eval(answer):
            if verbose: print('--- OK! ---')
        else:
            raise Warning('--- Fail! expected answer of %s is %s, but actual result is %s ---'
                          % (exp, answer, str(result)))

    buffer, count = '', 0
    for line in get_lines(filename):
        if test and count < start:
            count += 1
            continue
        try:
            if verbose: print(f'({count})▶ ', end='')  # prompt
            line = line.strip() if filename else input()
            if filename and verbose: print(line)

            if line and line[-1] == '\\':
                buffer += line[:-1]
                continue  # join multiple lines
            elif buffer:
                line, buffer = buffer + line, ''
            if line and line[-1] == ';':
                line = line[:-1]
                show = False
            else:
                show = True

            exp, comment = split_exp_comment(line)
            if exp:
                result = calc_exec(exp)
            else:  # a comment line
                if comment.strip() == 'TEST' and not test:
                    return  # if not testing, omit lines below #TEST
                continue
            if result is None: continue
            if verbose and show: print(format(result))

            # test
            if test and comment:
                verify_answer(exp, result, comment, verbose)

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
        print('\nCongratulations, tests all passed in "%s"!\n' % filename)


### RUN ###
from sys import argv

if len(argv) > 1:
    if argv[1] == '-t':
        run("tests", True, 0)
    else:
        run(argv[1])
else:
    run()
