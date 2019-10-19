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

    def empty(self):
        return self.s == []

    def clear(self):
        self.s = []


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
valStack = Stack()
opStack = Stack()

binary_ops = {'+':(add, 1), '-':(sub, 1), '*':(mul, 2), '/':(truediv, 2),
'//':(floordiv, 2), '^':(pow, 3), '%':(mod, 2), '&':(and_, -1), '|':(or_, -2),
'=':(eq, 0), '!=':(ne, 0), '<':(lt, 0), '>':(gt, 0), '<=':(le, 0), '>=':(ge, 0)}
unitary_ops = {'-':(neg, 4), '!':(not_, 4)}

op_list = list(binary_ops) + list(unitary_ops)

special_words = set(['if', 'else'])

builtins = {'sin':math.sin, 'cos':math.cos, 'tan':math.tan, 
'asin':math.asin, 'acos':math.acos, 'atan':math.atan,
'abs':abs, 'sqrt':math.sqrt, 'floor':math.floor, 'ceil':math.ceil,
'log':math.log, 'E':math.e, 'Pi':math.pi,}


def get_token(exp):
    exp = exp.strip()
    track_parens = 0
    first_char = exp[0]

    if exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif first_char in op_list:
        return 'op', first_char, exp[1:]
    elif first_char == "'":
        close_pos = exp[1:].find("'")
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


def eval_pure(exp, env=global_env):
    # inner evaluation, without assignment
    def calc(op):
        if op[1] >= 4:  # unitary op
            valStack.push(op[0](valStack.pop()))
        else:
            n2 = valStack.pop()
            n1 = valStack.pop()
            valStack.push(op[0](n1, n2))
    def complete_calc():
        # calc until meets a stop_mark in opStack and remove it
        while not opStack.empty():
            op = opStack.pop()
            if op[0]: calc(op)
            else: return
    def push_op(op):
        while not opStack.empty():
            last_op = opStack.pop()
            if op[0] is None or op[1] > last_op[1]:
                opStack.push(last_op)
                break
            else:
                try: calc(last_op)
                except AssertionError:
                    raise SyntaxError
        opStack.push(op)
    
    valStack.clear()
    opStack.clear()
    prev_type = None
    set_stop_mark = lambda : push_op((None, -10))  # set a mark to stop calc
    set_stop_mark()  # mark the beginning of evaluation
    while exp:
        type, token, exp = get_token(exp)
        if type in ('number', 'name') and \
        prev_type in ('number', 'name', 'paren'):
            push_op(binary_ops['*'])
        if type == 'number':
            valStack.push(py_eval(token))
        elif type == 'name':
            if token in builtins:
                valStack.push(builtins[token])
            valStack.push(env[token])
        elif type == 'op':
            if (prev_type in (None, 'op')) and token in unitary_ops:
                push_op(unitary_ops[token])
            else: push_op(binary_ops[token])
        elif type == 'paren':
            if prev_type in ('name', 'lambda'):  # applying a function
                args = [eval_pure(arg) for arg in token[1:-1].split(',')]
                f = valStack.pop()
                valStack.push(f(*args))
            else:
                if prev_type in ('number', 'paren'):
                    push_op(binary_ops['*'])
                valStack.push(eval_pure(token[1:-1], env))
        elif type == 'if':
            push_op((lambda x, y: x if y else None, -5))
        elif type == 'else':
            push_op((lambda x, y: y if x is None else x, -5))
        elif type == 'lambda':  # eg: ('x, y' x^2-3*y)
            if prev_type is not None:
                raise SyntaxError('invalid lambda expression!')
            args = [get_name(seg) for seg in token[1:-1].split(',')]
            valStack.push(Function(args, exp, env))
            break
        else:
            pass  # perhaps add more functionality here
        prev_type = type
    complete_calc()
    result = valStack.pop()
    return result


def eval(exp):
    # outer evaluation
    # two cases: assignment and evaluation
    assign_mark = exp.find(':=')
    if assign_mark < 0:
        return eval_pure(exp)
    else:
        name, rest = get_name(exp[:assign_mark], False)
        if name in special_words or name in builtins:
            raise SyntaxError('word %s protected!'%name)
        r_exp = exp[assign_mark+2:]
        if not rest:  # assignment of a variable
            value = eval_pure(r_exp)
        else:  # assignment of a function
            rest = rest.strip()
            if rest[0] != '(' or rest[-1] != ')':
                raise SyntaxError('invalid variable name!')
            args = [get_name(seg) for seg in rest[1:-1].split(',')]
            value = Function(args, r_exp, global_env)
        global_env[name] = value


def repl():
    while True:
        exp = input('> ')
        try:
            val = eval(exp)
            if val is not None: print(val)
        except KeyboardInterrupt:
            return
        except Exception as err:
            print(err)


repl()
