from __classes import *
from __parser import *
from __builtins import builtins

py_eval = eval

global_env = Env({'ans':[]})
CM = calcMachine()
ans_records = []


def map_list(proc, list_str):
    content = list_str[1:-1]
    l = []
    while content:
        item = ''
        while content:
            type, token, content = get_token(content)
            if type == 'comma': break
            item += token
        l.append(item)
    return [proc(arg) for arg in l]

def get_params(list_str):
    return map_list(get_name, list_str)

def eval_list(list_str, env):
    return map_list(lambda exp: eval_pure(exp, env), list_str)

def eval_list_comprehension(list_str, env):
    def gen_range(param, ran, conds):
        for val in eval_pure(ran, local_env):
            local_env[param] = val
            for test in (eval_pure(c, local_env) for c in conds):
                if test: yield val
    def gen_vals(params, ranges):
        if len(ranges) == 0: yield ()
        else:
            segs = ranges[0].split('if')
            head_range = gen_range(params[0], segs[0], segs[1:])
            for v in head_range:
                for rest_vals in gen_vals(params[1:], ranges[1:]):
                    yield (v,)+rest_vals
    segs = list_str[1:-1].split('for')
    exp, param_ranges = segs[0], segs[1:]
    params, ranges = zip(*[pr.split('in') for pr in param_ranges])
    local_env = env.make_subEnv()
    return [function(params, exp, env)(*args)
        for args in gen_vals(params, ranges)]


def eval_number(exp):
    if 'e' in exp:
        num, power = exp.split('e')
        return py_eval(num) * 10**py_eval(power)
    else:
        return py_eval(exp)

def eval_cases(exp, env):
    def error():
        raise SyntaxError('invalid cases expression!')
    if exp[0] != ':': error()
    cases = [case.split(',') for case in exp[1:].split(';')]
    try:
        for val_exp, cond_exp in cases[:-1]:
            if eval_pure(cond_exp, env):
                CM.push_val(eval_pure(val_exp, env))
                return
    except ValueError: error()
    else_case = cases[-1]
    if len(else_case) != 1: error()
    CM.push_val(eval_pure(else_case[0], env))

def function(params, body, env=global_env):
    def apply(*args):
        return eval_pure(body, env.make_subEnv(params, args))
    return apply


def eval_pure(exp, env):
    # inner evaluation, without assignment
    prev_type = None
    CM.set_out()
    while exp:
        type, token, exp = get_token(exp)
        prev_val = None if CM.vals.empty() else CM.vals.peek()
        if callable(prev_val):  # applying a function
            if type != 'paren' and prev_type is not None:
                raise SyntaxError('invalid function application!')
            CM.push_val(CM.vals.pop()(*(eval_list(token, env))))
            continue
        if all(t in ('number', 'name', 'paren') for t in (type, prev_type)):
            CM.push_op(binary_ops['*'])
        if type == 'ans':
            if len(global_env['ans']) > 0:
                if exp and exp[0] == '.':
                    _, index, exp = get_token(exp[1:])
                    index = eval_pure(index, env)
                else: index = -1
                CM.push_val(global_env['ans'][index])
            else: raise ValueError('No previous result!')
        elif type == 'number':
            CM.push_val(eval_number(token))
        elif type == 'name':
            CM.push_val(builtins[token] if token in builtins else env[token])
        elif type == 'op':
            if (prev_type in (None, 'op')) and token in unitary_ops:
                CM.push_op(unitary_ops[token])
            else:
                CM.push_op(binary_ops[token])
        elif type == 'paren':
            CM.push_val(eval_pure(token[1:-1], env))
        elif type == 'if':
            CM.push_op((lambda x, y: x if y else 'false', -5))
        elif type == 'else':
            CM.push_op((lambda x, y: y, -5))
            if CM.vals.peek() != 'false':
                CM.ops.pop()
                break  # short circuit
        elif type == 'lambda':  # eg: ({x, y} x^2-3*y)
            if prev_type is not None:
                raise SyntaxError('invalid lambda expression!')
            CM.push_val(function(get_params(token), exp, env))
            break
        elif type == 'cases':  # eg: cases: 1, x>0; 0, x=0; -1
            eval_cases(exp, env)
            break
        elif type == 'list':
            if token.find('for') > 0:
                CM.push_val(eval_list_comprehension(token, env))
            else:
                CM.push_val(eval_list(token, env))
        else:
            pass  # perhaps add more functionality here
        prev_type = type
    return CM.calc()


def eval(exp):
    # outer evaluation
    # two cases: assignment and evaluation
    assign_mark = exp.find(':=')
    if assign_mark < 0:
        result = eval_pure(exp, global_env)
    else:
        name, rest = get_name(exp[:assign_mark], False)
        if name in special_words or name in builtins:
            raise SyntaxError('word "%s" is protected!'%name)
        right_exp = exp[assign_mark+2:]
        if not rest:  # assignment of a variable
            value = eval_pure(right_exp, global_env)
        else:  # assignment of a function
            type, para_str, rest = get_token(rest)
            if type != 'paren' or rest != '':
                raise SyntaxError('invalid variable name!')
            value = function(get_params(para_str), right_exp)
            # a function is regarded as a special value
        global_env[name] = value
        result = None
    global_env['ans'].append(result)
    return result

def loop():
    while True: yield None

def repl(test=False, cases=loop()):
    count = 0
    for case in cases:
        try:
            prompt = '[{n}]> '.format(n=count)
            # test below
            if test:
                if case.find('#') > 0:
                    exp, ans = case.split('#')
                else:
                    exp, ans = case, None
                print(prompt+exp)
            # test above
            else: exp = input(prompt)
            val = eval(exp)
            if val is not None:
                print(val)
            # test below
            if test and ans is not None:
                if val == py_eval(ans):
                    print('OK!')
                else:
                    print('Fail! Expect %s' % ans)
                    return
            # test above
            count += 1
        except KeyboardInterrupt: return
        except (ValueError, SyntaxError, ArithmeticError,
        KeyError, IndexError, TypeError) as err:
            print(err)
            if test: return
            CM.reset()
    print('\nCongratulations, tests all passed!')


### TEST ###
tests = """s := 1
[1, 2, 3] #[1,2,3]
ans #[1,2,3]
ans@2 #3
ans.2 #[1,2,3]
s #1
f(x) := x+1
f(s) #2
f := {x, y} x*(1+y)
f(s, 2*(1+s)) #5
l := [1,max(1,2),3]
l = ans.1 #True
sum({i} i^2, l) #14
[i for i in range(3)] # [0,1,2]
[i for i in range(4) if i%2] #[1,3]
[[i,j] for i in range(3) if i%2 for j in range(5) if j%2==0 if j <3] #[[1, 0], [1,2]]
""".splitlines()
### TEST ###


from sys import argv
if len(argv) > 1 and argv[1] == '-t':
    repl(True, tests)
else:
    repl()
