from __classes import *
from __parser import *
from __builtins import *

py_eval = eval

global_env = Env({'ans':[]})
CM = calcMachine()
ans_records = []


def eval_list(list_str, env):
    lst, comprehension = get_list(list_str, True)
    if comprehension:
        if len(lst) > 1:
            raise SyntaxError('invalid list comprehension syntax!')
        result = toList(eval_comprehension(lst[0], env))
    else:
        result = [eval_pure(exp, env) for exp in lst]
    return result

def eval_subscription(lst, indices):
    if indices == []: return lst
    items = subscript(lst, indices[0])
    if isIterable(indices[0]):
        return [eval_subscription(item, indices[1:]) for item in items]
    else:
        return eval_subscription(items, indices[1:])

def eval_comprehension(exp, env):
    def gen_vals(exp, params, ranges):
        if params:
            segs = ranges[0].split('if')
            ran, conds = segs[0], segs[1:]
            for parvalue in eval_pure(ran, local_env):
                local_env[params[0]] = parvalue
                if all(eval_pure(cond, local_env) for cond in conds):
                     yield from gen_vals(exp, params[1:], ranges[1:])
        else:
            yield eval_pure(exp, local_env)
    segs = exp.split('for')
    exp, param_ranges = segs[0], segs[1:]
    params, ranges = zip(*[pr.split('in') for pr in param_ranges])
    params = [get_name(par) for par in params]
    local_env = env.make_subEnv()
    return gen_vals(exp, params, ranges)

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
    cases = [get_list('(%s)'%case) for case in exp[1:].split(';')]
    try:
        for val_exp, cond_exp in cases[:-1]:
            if eval_pure(cond_exp, env):
                CM.push_val(eval_pure(val_exp, env))
                return
    except ValueError: error()
    else_case = cases[-1]
    if len(else_case) != 1: error()
    CM.push_val(eval_pure(else_case[0], env))

def eval_ans(exp, env):
    if len(global_env['ans']) > 0:
        if exp and exp[0] == '.':
            _, index, exp = get_token(exp[1:])
            index = eval_pure(index, env)
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


def function(params, body, env=global_env):
    def apply(*args):
        bindings = dict(zip(params, args))
        return eval_pure(body, env.make_subEnv(bindings))
    return apply


def eval_pure(exp, env):
    # inner evaluation, without assignment
    prev_type = None
    CM.begin()
    while exp:
        type, token, exp = get_token(exp)
        prev_val = None if CM.vals.empty() else CM.vals.peek()
        if isFunction(prev_val):  # applying a function
            if type != 'paren' and prev_type is not None:
                raise SyntaxError('invalid function application!')
            CM.push_val(CM.vals.pop()(*(eval_list(token, env))))
            continue
        if all(t in ('number', 'name', 'paren') for t in (type, prev_type)):
            CM.push_op(binary_ops['*'])
        if type == 'ans':
            exp = eval_ans(exp, env)
        elif type == 'number':
            CM.push_val(eval_number(token))
        elif type == 'name':
            CM.push_val(builtins[token] if token in builtins else env[token])
        elif type == 'op':
            if (prev_type in (None, 'op')) and token in unitary_l_ops:
                CM.push_op(unitary_l_ops[token])
            elif token in unitary_r_ops:
                CM.push_op(unitary_r_ops[token])
            else:
                CM.push_op(binary_ops[token])
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
                raise SyntaxError('invalid lambda expression!')
            CM.push_val(function(get_params(token), exp, env))
            break
        elif type == 'let':  # eg: let {x=1, y=2} x+y
            CM.push_val(eval_let(exp, env))
            break
        elif type == 'cases':  # eg: cases: 1, x>0; 0, x=0; -1
            eval_cases(exp, env); break
        elif type == 'list':
            val = eval_list(token, env)
            if prev_type == 'list':
                CM.push_val(eval_subscription(CM.vals.pop(), val))
            else: CM.push_val(val)
        elif type == 'ENV':
            if exp: raise SyntaxError
            return str(global_env.bindings)[1:-1]
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
        if name in special_words or name in builtins or name in op_list:
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
    if not CM.vals.empty() or not CM.ops.empty():
        raise SyntaxError
    global_env['ans'].append(result)
    return result


def loop():
    while True: yield

def display(val):
    def sci_repr(x):
        if x == 0: return 0
        e = floor(log10(x))
        b = x/10**e
        return '{} E {}'.format(b, e)
    if isNumber(val) and (abs(val) <= 0.001 or abs(val) >= 10000):
        print(sci_repr(val))
    else: print(val)

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
                display(val)
            # test below
            if test and ans is not None:
                if val == py_eval(ans):
                    print('--- OK! ---')
                else:
                    print('--- Fail! Expect %s ---' % ans)
                    return
            # test above
            count += 1
        except KeyboardInterrupt: return
        except Exception as err:
            print(err)
            if test: return
            CM.reset()
    print('\nCongratulations, tests all passed!')


### TEST ###
tests = """s := 1
5*2/(10-9) #10
.5*2^2 + log10(100+10*90) #5
5!/3! #20
[1, 2, 3] #[1,2,3]
ans #[1,2,3]
ans@2 #3
ans.2 #5
s #1
f(x) := x+1
f(s) #2
1 if s=2 else 3 #3
f := {x, y} x*(1+y)
f(s, 2*(1+s)) #5
l := [1,max(1,2),3]
l = ans.5 #1
sum([i^2 for i in l]) #14
[i for i in range(3)] # [0,1,2]
[i for i in range(4) if i%2] #[1,3]
2 in range(3) #1
3 in 2~3 #1
l@(1~:) #[2,3]
l@(:~1) #[1,2]
l@(:~1)++[4,5]@(1~:) #[1,2,5]
list(l@(1~2)) #[2,3]
m := [[1,2,3],[3,4,5],[5,6,7]]
m[2,1] #6
mm := m[range(2),[i for i in range(3) if i%2]]
list(mm) #[[2],[4]]
2*.4 #0.8
1e2 #100.0
1+3e-2 #1.03
2e3*7e-2 #140.0
-2^4 #-16
-.5+3 #2.5
not 3+3 = 3 #1
[i if i%2 else 0 for i in range(10) if i%3] #[1,0,0,5,7,0]
compose := {f, g} {x} f(g(x))
inc(x) := x+1
sqr(x) := x^2
compose(inc, sqr)(3) #10
compose(sqr, inc)(3) #16
max3(x, y, z) := cases: x, x > y and x > z; y, y > z; z
max3(3, 4, 2) #4
max3(1, 2, 2) #2
[1,2]++[3,4] #[1,2,3,4]
1+I #1+1j
(1-I)(1+I) #2
11062274001.181583
let {x=1} x+3 #4
tail([1,2,3]) #[2,3]
tail([1,2,3],2) #[3]
merge(l1, l2) := cases: l1, empty?(l2); l2, empty?(l1); [l1@0]++merge(tail(l1),l2), l1@0 < l2@0; [l2@0]++merge(l1, tail(l2))
merge([1,3,5],[1,2,3,4]) #[1,1,2,3,3,4,5]
sort(l) := l if len(l)<2 else let {halflen = len(l)//2} merge(sort(l@range(halflen)), sort(tail(l, halflen)))
sort([1,4,3,7,5,2,6]) #[1,2,3,4,5,6,7]
sin_approx(n) := {x} sum([(-1)^(i // 2)*x^i/fact(i) for i in 1~n if i%2])
my_sin := sin_approx(10)
abs(sin(PI/3)-my_sin(PI/3)) < 0.0001 #1
""".splitlines()
### TEST ###


from sys import argv
if len(argv) > 1 and argv[1] == '-t':
    repl(True, tests)
else:
    repl()
