from __classes import *
from __parser import *
from __builtins import *
from __formatter import *

py_eval = eval

global_env = Env()
history = []
CM = calcMachine()


config = lambda: None
config.prec = 4
config.latex = False
config.all_symbol = True


def eval_list(list_str, env):
    lst = get_list(list_str)
    if len(lst) == 1:
        comprehension = get_list(list_str, 'for')
        if len(comprehension) > 1:
            return eval_comprehension(comprehension, env)
    value = lambda exp: calc_eval(exp, env)
    result = []
    for exp in lst:
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
    if not subscript_exps: raise SyntaxError('invalid subscript')
    if len(subscript_exps) == 1:
        return index(lst, eval_index(subscript_exps[0]))
    return subscript(lst, tuple(map(eval_index, subscript_exps)))


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
    cases = [split(case, ':') for case in split(exp, ',')]
    value = lambda exp: calc_eval(exp, env)
    for val in (value(exp) for cond, exp in cases[:-1] if value(cond)):
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
        params_str = ', '.join(self.params) + ('' if self.fixed_argc else ' ... ')
        return f"function of {params_str}: {self.body}"


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


def is_replacable(type, *replaced_types):
    return type in replaced_types + ('name', 'paren', 'ans')


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
            func, args = CM.vals.pop(), eval_list(token, env)
            CM.push_val(func(*args))
            continue
        if all(is_replacable(t, 'number', 'symbol') for t in (type, prev_type)):
            CM.push_op(binary_ops['*'])
        if type == 'ans':
            id = -1 if len(token) == 1 else int(token[1:])
            try:
                CM.push_val(history[id])
            except IndexError:
                if id < 0:
                    id = len(history) + id
                raise ValueError(f'Answer No.{id} not found!')
        elif type == 'number':
            try:
                CM.push_val(py_eval(token))
            except Exception:
                raise SyntaxError(f'invalid number: {token}')
        elif type == 'name':
            try:
                val = env[token]
            except KeyError:
                if token in builtins:
                    val = builtins[token]
                elif config.all_symbol:
                    val = Symbol(token)
                else:
                    raise NameError(f'unbound symbol \'{token}\'')
            CM.push_val(val)
        elif type == 'symbol':
            CM.push_val(Symbol(token[1:]))
        elif type == 'op':
            if (prev_type in (None, 'op')) and token in unitary_l_ops:
                CM.push_op(unitary_l_ops[token])
            elif exp and token in binary_ops:
                CM.push_op(binary_ops[token])
            else:
                CM.push_op(unitary_r_ops[token])
        elif type == 'if':
            CM.push_op(Op('bin', standardize('if', 
                lambda x, y: x if y else None), -5))
        elif type == 'else':
            CM.push_op(Op('bin', standardize('else', lambda x, y: y), -5))
            if CM.vals.peek() is not None:
                CM.ops.pop()
                break  # short circuit
        elif type == 'cases':
            CM.push_val(eval_cases(exp, env))
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
    result = CM.calc()
    return result


def calc_exec(exp, record=True):
    exps = exp.split(';')
    if not exps: return
    if len(exps) > 1:
        for exp in exps[:-1]:
            calc_exec(exp, False)
        return calc_exec(exps[-1])
    exp = exps[0]
    words = exp.split()
    if words[0] == 'ENV':
        for name in global_env.bindings:
            print(f"{name}: {global_env[name]}")
    elif words[0] == 'load':
        current_history = history.copy()
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
        history.clear()
        history.extend(current_history)
    elif words[0] == 'import':
        verbose = True
        try: words.remove('-v')
        except: verbose = False
        definitions = {}
        for modules in words[1:]:
            locals = {}
            exec('from pymodules.%s import definitions' % modules, globals(), locals)
            definitions.update(locals['definitions'])
        global_env.define(definitions)
        if verbose: return set(definitions)
    elif words[0] == 'set':
        if len(words) < 3:
            raise SyntaxError("invalid format setting")
        if words[1] == 'prec':
            prec = py_eval(words[2])
            config.prec = prec
        elif words[1] == 'latex':
            config.latex = True if words[2] in ('on', '1') else False
        elif words[1] == 'all-symbol':
            config.all_symbol = True if words[2] in ('on', '1') else False
        else:
            raise SyntaxError('invalid format setting')
    elif words[0] == 'del':
        for name in words[1:]:
            global_env.remove(name)
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
        if result is not None and record:
            history.append(result)
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
        def equal(x, y):
            if is_number(x) and is_number(y):
                return abs(x-y) < 0.001
            if all(is_iterable(t) for t in (x, y)):
                return len(x) == len(y) and all(equal(xi, yi) 
                    for xi, yi in zip(x, y))
            return x == y
        if equal(result, py_eval(answer)):
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
            if verbose and show: 
                if type(result) == set:  # imported definitions
                    print('imported:', ', '.join(result))
                else:
                    print(format(result, config))

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
