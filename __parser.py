from operator import *

binary_ops = {'+':(add, 1), '-':(sub, 1), '*':(mul, 2), '/':(truediv, 2),
'//':(floordiv, 2), '^':(pow, 3), '%':(mod, 2), '&':(and_, -1), '|':(or_, -2),
'=':(eq, 0), '!=':(ne, 0), '<':(lt, 0), '>':(gt, 0), '<=':(le, 0), '>=':(ge, 0),
'@':(lambda l, i: l[i], 5)}
unitary_ops = {'-':(neg, 4), '!':(not_, 4)}

op_list = list(binary_ops) + list(unitary_ops)

special_words = set(['ans', 'if', 'else', 'cases'])


def get_token(exp):
    exp = exp.strip()
    pbtrack = lambda p, b: p == 0 and b == 0
    pbtrack.parens, pbtrack.brackets = 0, 0
    first_char = exp[0]

    if exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif first_char in op_list:
        return 'op', first_char, exp[1:]
    elif first_char == ',':
        return 'comma', ',', exp[1:]
    elif first_char == '{':
        close_brace = exp[1:].find('}') + 1
        return 'lambda', exp[:close_brace+1], exp[close_brace+1:]
    elif first_char.isdigit():
        type = 'number'
    elif first_char.isalpha() or first_char == '_':
        type = 'name'
    elif first_char == '(':
        type = 'paren'
        pbtrack.parens = 1
    elif first_char == '[':
        type = 'list'
        pbtrack.brackets = 1
    else:
        raise SyntaxError('unknown symbol!')

    i = 1   
    while i < len(exp):
        char = exp[i]
        if type in ('paren', 'list'):
            if pbtrack(pbtrack.parens, pbtrack.brackets): break
        elif char.isspace() or \
        (type == 'number' and char not in '1234567890.') or \
        (type == 'name' and not (char.isalnum() or char in '_?')):
            break
        if char == '(': pbtrack.parens += 1
        elif char == ')': pbtrack.parens -= 1
        elif char == '[': pbtrack.brackets += 1
        elif char == ']': pbtrack.brackets -= 1
        i += 1
    if pbtrack.parens != 0 or pbtrack.brackets != 0:
        raise SyntaxError('unpaired parentheses or brackets!')
    token, rest = exp[:i], exp[i:]
    if token in special_words:
        return token, token, rest
    return type, token, rest


def get_name(exp, no_rest=True):  
    type, name, rest = get_token(exp)
    if not type == 'name' or (no_rest and rest):
        raise SyntaxError('invalid variable name!')
    if no_rest: return name
    return name, rest
