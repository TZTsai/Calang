from __builtins import op_list, special_words


def get_token(exp):
    exp = exp.strip()
    pbtrack = lambda p, b: p == 0 and b == 0
    pbtrack.parens, pbtrack.brackets = 0, 0
    first_char = exp[0]

    if first_char == ',':
        return 'comma', ',', exp[1:]
    elif first_char == '{':
        close_brace = exp[1:].find('}') + 1
        return 'lambda', exp[:close_brace+1], exp[close_brace+1:]
    elif first_char.isdigit() or first_char in '.':
        type = 'number'; e = 0
    elif first_char.isalpha() or first_char == '_':
        type = 'name'
    elif first_char == '(':
        type = 'paren'
        pbtrack.parens = 1
    elif first_char == '[':
        type = 'list'
        pbtrack.brackets = 1
    elif exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif first_char in op_list:
        return 'op', first_char, exp[1:]
    else:
        raise SyntaxError('unknown symbol!')

    i = 1   
    while i < len(exp):
        char = exp[i]

        if type in ('paren', 'list'):
            if pbtrack(pbtrack.parens, pbtrack.brackets): break

        elif char.isspace() or \
        (type == 'number' and
            (char not in '1234567890.e' and not (e and char == '-'))) or \
        (type == 'name' and not (char.isalnum() or char in '_?')):
            break

        if type == 'number' and char == 'e':
            if e > 0: raise SyntaxError
            e += 1

        if char == '(': pbtrack.parens += 1
        elif char == ')': pbtrack.parens -= 1
        elif char == '[': pbtrack.brackets += 1
        elif char == ']': pbtrack.brackets -= 1

        i += 1

    if pbtrack.parens != 0 or pbtrack.brackets != 0:
        raise SyntaxError('unpaired parentheses or brackets!')

    token, rest = exp[:i], exp[i:]
    if token in op_list:
        return 'op', token, rest
    elif token in special_words:
        return token, token, rest
    return type, token, rest


def get_name(exp, no_rest=True):  
    type, name, rest = get_token(exp)
    if not type == 'name' or (no_rest and rest):
        raise SyntaxError('invalid variable name!')
    if no_rest: return name
    return name, rest


def get_list(list_exp, comprehension_possible=False):
    content = list_exp[1:-1]
    l = []
    comprehension = False
    while content:
        item = ''
        while content:
            type, token, content = get_token(content)
            if type == 'comma':
                break
            elif comprehension_possible and type == 'for':
                comprehension = True
            item += token
        l.append(item)
    if comprehension_possible:
        return l, comprehension
    return l


def get_params(list_str):
    return [get_name(s) for s in get_list(list_str)]