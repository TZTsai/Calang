from operator import *
from queue import LifoQueue

class stack:
    def __init__(self):
        self.s = LifoQueue()

    def push(self, obj):
        self.s.put(obj)
    
    def pop(self):
        assert(not self.s.empty())
        return self.s.get()

    def empty(self):
        return self.s.empty()

binary_ops = {'+':(add, 1), '-':(sub, 1), '*':(mul, 2), '/':(truediv, 2), '//':(floordiv, 2),
'^':(pow, 3), '%':(mod, 2), '&':(and_, -1), '|':(or_, -2), '=':(eq, 0), '!=':(ne, 0),
'<':(lt, 0), '>':(gt, 0), '<=':(le, 0), '>=':(ge, 0)}
parens = {'(':(_, -10), ')':(_, -10)}
unitary_ops = {'-':(neg, 4), '!':(not_, 4)}

py_eval = eval

global_env = {}


def get_token(exp):
    first_char = exp[0]
    track_parens = 0
    ops = list(binary_ops) + list(unitary_ops) + list(parens)

    if first_char.isspace():
        return get_token(exp[1:])
    elif exp[:2] in ops:
        return 'op', exp[:2], exp[2:]
    elif first_char in ops:
        return 'op', first_char, exp[1:]
    elif first_char.isdigit():
        type = 'number'
    elif first_char.isalpha() or first_char == '_':
        type = 'name'
    elif first_char == '(':
        type = 'paren'
        track_parens = 1
    else:
        raise SyntaxError('unknown symbol!')

    i = 1
    for i in range(1, len(exp)):
        char = exp[i]
        if char.isspace() or \
        (type == 'number' and not char.isdigit()) or \
        (type == 'name' and not (char.isalnum() or char == '_')) or \
        (type == 'paren' and track_parens == 0):
            return type, exp[:i], exp[i:]
        if char == '(': track_parens += 1
        elif char == ')': track_parens -= 1

    if track_parens != 0: raise SyntaxError('unpaired parenthesis!')
    return type, exp[:i], exp[i:]


def check_valid_name(exp):
    type, _, rest = get_token(exp.strip())
    if not(type == 'name' and rest == ''):
        raise SyntaxError('invalid variable name')


numStack = stack()
opStack = stack()


def eval_pure(exp, env=global_env):
    def calc(op):
        if op[1] >= 4:  # unitary op
            numStack.push(op[0](numStack.pop()))
        else:
            n2 = numStack.pop()
            n1 = numStack.pop()
            numStack.push(op[0](n1, n2))
    def push_op(op):
        while not opStack.empty():
            last_op = opStack.pop()
            if op[1] > last_op[1]:
                opStack.push(last_op)
                break
            elif op[1] == last_op[1] == -10:
                return
            else:
                try: calc(last_op)
                except AssertionError:
                    raise SyntaxError('invalid syntax')
        opStack.push(op)
    prev_type = None
    opStack.push(('begin', -10))
    while exp:
        type, token, exp = get_token(exp)
        if type == 'number': numStack.push(py_eval(token))
        elif type == 'name': numStack.push(env[token])
        elif type == 'op':
            if (prev_type in (None, 'op')):
                if token in unitary_ops: 
                    push_op(unitary_ops[token])
                else: raise SyntaxError('invalid syntax')
            else: push_op(binary_ops[token])
        elif type == 'paren': numStack.push(eval_pure(token[1:-1], env))
        else: pass  # perhaps add more functionality here
        prev_type = type
    push_op(('end', -10))
    result = numStack.pop()
    return result


def eval(exp):
    # outer evaluation
    # two cases: assignment and evaluation
    assign_mark = exp.find(':=')
    if assign_mark < 0:
        return eval_pure(exp)
    else:
        name = exp[:assign_mark]
        check_valid_name(name)
        value = eval_pure(exp[assign_mark+2:])
        global_env[name] = value


def repl():
    while True:
        exp = input('> ')
        try:
            print(eval(exp))
        except KeyboardInterrupt:
            return
        except (ValueError, SyntaxError, ArithmeticError, KeyError) as err:
            print(err)


repl()
