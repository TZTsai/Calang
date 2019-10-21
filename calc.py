from operator import *
import math


class Stack:
    def __init__(self):
        self.s = []

    def push(self, obj):
        self.s.append(obj)
    
    def pop(self):
        assert(not self.empty())
        return self.s.pop()

    def peek(self):
        assert(not self.empty())
        top = self.s.pop()
        self.s.append(top)
        return top

    def empty(self):
        return self.s == []

    def clear(self):
        self.s = []


class calcMachine:
    def __init__(self):
        self.vals = Stack()
        self.ops = Stack()

    def __calc(self, op):  # carry out a single operation
        if op[1] >= 4:  # unitary op
            self.vals.push(op[0](self.vals.pop()))
        else:
            n2 = self.vals.pop()
            n1 = self.vals.pop()
            self.vals.push(op[0](n1, n2))

    def set_out(self):  # mark the beginning of calculation
        self.ops.push((None, -10))  # add a stop_mark in op_stack

    def reset(self):
        self.ops.clear()
        self.vals.clear()

    def calc(self): # calculate the whole stack and return the result
        while not self.ops.empty():
            op = self.ops.pop()
            if op[0]: self.__calc(op)
            else: break
        return self.vals.pop()

    def push_val(self, val):
        self.vals.push(val)

    def push_op(self, op):
        while not self.ops.empty():
            last_op = self.ops.pop()
            if op[0] is None or op[1] > last_op[1]:
                break
            else:
                try: self.__calc(last_op)
                except AssertionError:
                    raise SyntaxError
        self.ops.push(op)


class Env:
    def __init__(self, bindings={}, parent=None):
        self.bindings = bindings
        self.parent = parent

    def __setitem__(self, name, val):
        self.bindings[name] = val

    def __getitem__(self, name):
        try:
            return self.bindings[name]
        except KeyError:
            if self.parent:
                return self.parent[name]
            else:
                raise KeyError('unbound symbol')


class Function:
    def __init__(self, args, body, env):
        self.args = args
        self.body = body
        self.parent_env = env

    def __call__(self, *args):
        new_env = Env(dict(zip(self.args, args)), self.parent_env)
        return eval_pure(self.body, new_env)


py_eval = eval

global_env = Env()
CM = calcMachine()

binary_ops = {'+':(add, 1), '-':(sub, 1), '*':(mul, 2), '/':(truediv, 2),
'//':(floordiv, 2), '^':(pow, 3), '%':(mod, 2), '&':(and_, -1), '|':(or_, -2),
'=':(eq, 0), '!=':(ne, 0), '<':(lt, 0), '>':(gt, 0), '<=':(le, 0), '>=':(ge, 0)}
unitary_ops = {'-':(neg, 4), '!':(not_, 4)}

op_list = list(binary_ops) + list(unitary_ops)

special_words = set(['if', 'else', 'cases'])

builtins = {'sin':math.sin, 'cos':math.cos, 'tan':math.tan, 
'asin':math.asin, 'acos':math.acos, 'atan':math.atan,
'abs':abs, 'sqrt':math.sqrt, 'floor':math.floor, 'ceil':math.ceil,
'log':math.log, 'E':math.e, 'Pi':math.pi}


def get_token(exp):
    exp = exp.strip()
    track_parens = 0
    first_char = exp[0]

    if exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif first_char in op_list:
        return 'op', first_char, exp[1:]
    elif first_char == "'":
        close_pos = exp[1:].find("'") + 1
        return 'lambda', exp[:close_pos+1], exp[close_pos+1:]
    elif first_char.isdigit():
        type = 'number'
    elif first_char.isalpha() or first_char == '_':
        type = 'name'
    elif first_char == '(':
        type = 'paren'
        track_parens += 1
    else:
        raise SyntaxError('unknown symbol!')

    for i in range(1, len(exp)):
        char = exp[i]
        if type == 'paren' and track_parens == 0:
            return type, token, exp[i:]
        elif char.isspace() or \
        (type == 'number' and char not in '1234567890.') or \
        (type == 'name' and not (char.isalnum() or char in '_?')):
            token, rest = exp[:i], exp[i:]
            if token in special_words:
                return token, token, rest
            return type, token, rest
        if char == '(': track_parens += 1
        elif char == ')': track_parens -= 1
    return type, exp, ''


def get_name(exp, no_rest=True):  
    type, name, rest = get_token(exp)
    if not type == 'name' or (no_rest and rest):
        raise SyntaxError('invalid variable name!')
    if no_rest: return name
    return name, rest


def map_args(f, argstr):
    return (f(arg) for arg in argstr[1:-1].split(','))


def get_params(argstr):
    return map_args(get_name, argstr)


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


def eval_pure(exp, env):
    # inner evaluation, without assignment
    prev_type = None
    CM.set_out()
    while exp:
        type, token, exp = get_token(exp)
        prev_val = None if CM.vals.empty() else CM.vals.peek()
        if callable(prev_val):  # applying a function
            if type != 'paren':
                raise SyntaxError('invalid function application!')
            args = map_args(lambda arg: eval_pure(arg, env), token)
            CM.push_val(CM.vals.pop()(*args))
            continue
        if all(t in ('number', 'name', 'paren') for t in (type, prev_type)):
            CM.push_op(binary_ops['*'])
        if type == 'number':
            CM.push_val(py_eval(token))
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
            # push a temporary mark 'false' if the condition is false
        elif type == 'else':
            if prev_val == 'false': CM.push_op((lambda x, y: y, -5))
            else: break  # short circuit
        elif type == 'lambda':  # eg: ('x, y' x^2-3*y)
            if prev_type is not None:
                raise SyntaxError('invalid lambda expression!')
            CM.push_val(Function(get_params(token), exp, env))
            break
        elif type == 'cases':  # eg: cases: 1, x>0; 0, x=0; -1
            eval_cases(exp, env)
            break
        else:
            pass  # perhaps add more functionality here
        prev_type = type
    return CM.calc()


def eval(exp):
    # outer evaluation
    # two cases: assignment and evaluation
    assign_mark = exp.find(':=')
    if assign_mark < 0:
        return eval_pure(exp, global_env)
    else:
        name, rest = get_name(exp[:assign_mark], False)
        if name in special_words or name in builtins:
            raise SyntaxError('word %s is protected!'%name)
        right_exp = exp[assign_mark+2:]
        if not rest:  # assignment of a variable
            value = eval_pure(right_exp, global_env)
        else:  # assignment of a function
            type, para_str, rest = get_token(rest)
            if type != 'paren' or rest != '':
                raise SyntaxError('invalid variable name!')
            value = Function(get_params(para_str), right_exp, global_env)
            # a function is regarded as a special value
        global_env[name] = value


def repl():
    while True:
        exp = input('> ')
        try:
            val = eval(exp)
            if val is not None: print(val)
        except KeyboardInterrupt:
            return
        except (ValueError, SyntaxError, ArithmeticError, KeyError) as err:
            CM.reset()
            print(err)


repl()
