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
    lst = [eval_pure(exp, env) for exp in lst]
    if any(x is None for x in lst):
        if len(lst) == 1: return []
        raise SyntaxError('invalid list syntax!')
    return lst

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

def eval_ans(exp):
    if len(global_env['ans']) > 0:
        if exp and exp[0] == '.':
            _, index, exp = get_token(exp[1:])
            index = py_eval(index)
        else: index = -1
        CM.push_val(global_env['ans'][index])
        return exp
    else: raise ValueError('No previous result!')

def eval_let(exp, env):
    type, bindings, body = get_token(exp)
    if type != 'lambda':
        raise SyntaxError('invalid let expression!')
    def parse_pair(s):
        eq = s.find('=')
        return s[:eq], s[eq+1:]
    bindings = [parse_pair(s) for s in get_list(bindings)]
    bindings = [(get_name(s1), eval_pure(s2, env)) for s1, s2 in bindings]
    new_env = env.make_subEnv(dict(bindings))
    return eval_pure(body, new_env)


class function:
    def __init__(self, params, body, env=global_env):
        self.params = params
        self.body = body.strip()
        self.env = env
    
    def __call__(self, *args):
        bindings = dict(zip(self.params, args))
        return eval_pure(self.body, self.env.make_subEnv(bindings))

    def __str__(self):
        return 'function of {}: {}'.format(', '.join(self.params), self.body)


def eval_pure(exp, env):
    # inner evaluation, without assignment
    if exp == '': return
    prev_type = None
    CM.begin()
    is_replacable = lambda t, t_src: t == t_src or t in ['name','paren','ans']
    while exp:
        type, token, exp = get_token(exp)
        prev_val = None if CM.vals.empty() else CM.vals.peek()
        if isFunction(prev_val):  # applying a function
            if type != 'paren' and prev_type is not None:
                raise SyntaxError('invalid function application!')
            CM.push_val(CM.vals.pop()(*eval_list(token, env)))
            continue
        if all(is_replacable(t, 'number') for t in (type, prev_type)):
            CM.push_op(binary_ops['*'])
        if type == 'ans':
            exp = eval_ans(exp)
        elif type == 'number':
            try:
                CM.push_val(py_eval(token))
            except Exception:
                raise SyntaxError('invalid number!')
        elif type == 'name':
            CM.push_val(builtins[token] if token in builtins else env[token])
        elif type == 'op':
            if (prev_type in (None, 'op')) and token in unitary_l_ops:
                CM.push_op(unitary_l_ops[token])
            elif exp and token in binary_ops:
                CM.push_op(binary_ops[token])
            else:
                CM.push_op(unitary_r_ops[token])
        elif type == 'paren':
            CM.push_val(eval_pure(token[1:-1], env))
        elif type == 'if':
            CM.push_op(Op('bin', lambda x, y: x if y else 'false', -5))
        elif type == 'else':
            CM.push_op(Op('bin', lambda x, y: y, -5))
            if CM.vals.peek() != 'false':
                CM.ops.pop(); break  # short circuit
        elif type == 'lambda':  # eg: {x, y} x^2-3*y
            if prev_type is not None:
                raise SyntaxError('%s must be at the beginning!'%type)
            CM.push_val(function(get_params(token), exp, env))
            break
        elif type == 'let':  # eg: let {x=1, y=2} x+y
            CM.push_val(eval_let(exp, env))
            break
        elif type == 'cases':  # eg: cases: 1, x>0; 0, x=0; -1
            CM.push_val(eval_cases(exp, env)); break
        elif type == 'list':
            if isIterable(prev_val) and is_replacable(prev_type, 'list'):
                CM.push_val(eval_subscription(CM.vals.pop(), token, env))
            else: 
                CM.push_val(eval_list(token, env))
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
            print("{}: {}".format(name, global_env[name]))
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
        name, rest = get_name(exp[:assign_mark], False)
        if name in special_words or name in builtins or name in op_list:
            raise SyntaxError('word "%s" is protected!'%name)
        right_exp = exp[assign_mark+2:]
        if not rest:  # assignment of a variable
            value = eval_pure(right_exp, global_env)
        else:  # assignment of a function
            type, param_str, rest = get_token(rest)
            if type != 'paren' or rest != '':
                raise SyntaxError('invalid variable name!')
            value = function(get_params(param_str), right_exp)
        global_env[name] = value
        result = value

    if not (CM.vals.empty() and CM.ops.empty()):
        raise SyntaxError('invalid expression!')
    global_env['ans'].append(result)
    return result


def display(val):
    def sci_repr(x):
        if x == 0: return 0
        e = floor(log10(x))
        b = x/10**e
        return '{} E {}'.format(b, e)
    if isNumber(val) and (abs(val) <= 0.001 or abs(val) >= 10000):
        print(sci_repr(val))
    else: print(val)


def run(filename=None, test=False):
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
            print('--- Fail! Expect %s ---' % answer)

    buffer = ''
    count = 0
    for line in get_lines(filename):
        try:
            print('[{}]> '.format(count), end='')
            line = line.strip() if filename else input()
            if filename: print(line)

            if line and line[-1] == '\\':
                buffer += line[:-1]
                continue  # join multiple lines
            elif buffer:
                line, buffer = buffer+line, ''

            exp, comment = split_exp_comment(line)
            result = eval(exp)
            if result is None: continue
            display(result)

            ### test ###
            if test and comment:
                verify_answer(result, comment)

            count += 1

        except KeyboardInterrupt:
            return
        except (Warning if test else Exception) as err:
            # actually no warning is raised,
            # I just don't want to catch errors when testing
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
