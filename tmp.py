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
parens = {'(':(False, -10), ')':(True, -10)}
unitary_ops = {'-':(neg, 4), '!':(not_, 4)}
op_list = list(binary_ops) + list(unitary_ops)

py_eval = eval

global_env = {}


def get_token(exp):
    exp = exp.strip()
    first_char = exp[0]

    if first_char in parens:
        return 'paren', first_char, exp[1:]
    elif first_char == ',':
        return 'comma', first_char, exp[1:]
    elif exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif first_char in op_list:
        return 'op', first_char, exp[1:]
    elif first_char.isdigit():
        type = 'number'
    elif first_char.isalpha() or first_char == '_':
        type = 'name'
    else:
        raise SyntaxError('unknown symbol!')

    for i in range(1, len(exp)):
        char = exp[i]
        if char.isspace() or \
        (type == 'number' and not char in '1234567890.') or \
        (type == 'name' and not (char.isalnum() or char == '_')):
             return type, exp[:i], exp[i:]
    return type, exp, ''


def check_valid_name(exp):
    type, _, rest = get_token(exp)
    if not(type == 'name' and rest == ''):
        raise SyntaxError('invalid variable name!')


valStack = stack()
symStack = stack()


def eval_pure(exp, env=global_env):
    def calc(op):
        if op[1] >= 4:  # unitary op
            valStack.push(op[0](valStack.pop()))
        else:
            n2 = valStack.pop()
            n1 = valStack.pop()
            valStack.push(op[0](n1, n2))
    def push_sym(sym):
        is_paren = lambda sym: sym[1] == -10
        while not symStack.empty():
            last_sym = symStack.pop()
            if is_paren(last_sym) and is_paren(sym):
                return  # eliminate parens
            elif not sym[0] or sym[1] > last_sym[1]:
                symStack.push(last_sym)
                break
            else:
                try: calc(last_sym)
                except AssertionError:
                    raise SyntaxError('invalid syntax')
        symStack.push(sym)
    prev_type = None
    symStack.push(parens['('])
    while exp:
        type, token, exp = get_token(exp)
        if type == 'number': valStack.push(py_eval(token))
        elif type == 'name':
            if token in env: valStack.push(env[token])
            else: raise ValueError('unbound variable!')
        elif type == 'op':
            if (prev_type in (None, 'op')) and token in unitary_ops:
                push_sym(unitary_ops[token])
            else: push_sym(binary_ops[token])
        elif type == 'paren':
            if prev_type == 'name':
                pass
            else: push_sym(parens[token])
        elif type == 'comma':
            
        else: pass  # perhaps add more functionality here
        prev_type = type
    push_sym(parens[')'])  # force to complete calculation
    result = valStack.pop()
    return result


def eval(exp):
    # outer evaluation
    # two cases: assignment and evaluation
    assign_mark = exp.find(':=')
    if assign_mark < 0:
        return eval_pure(exp)
    else:
        name = exp[:assign_mark].strip()
        check_valid_name(name)
        value = eval_pure(exp[assign_mark+2:])
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
            print(err)


repl()
