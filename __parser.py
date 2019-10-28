from __builtins import op_list, special_words


def get_token(exp):
    exp = exp.strip()

    balanced = lambda counts: all(counts[b] == 0 for b in counts)
    brackets = {'paren':0, 'list':0, 'lambda':0}
    def update_brackets(char):
        bracket_cnt = ('paren', 1 if char == '(' else -1) if char in '()' \
        else ('list', 1 if char == '[' else -1) if char in '[]' else \
        ('lambda', 1 if char == '{' else -1)
        brackets[bracket_cnt[0]] += bracket_cnt[1]

    first_char = exp[0]

    if first_char == ',':
        return 'comma', ',', exp[1:]
    elif first_char.isdigit() or first_char in '.':
        type = 'number'
        e = 0  # for scientific notation
    elif first_char.isalpha() or first_char == '_':
        type = 'name'
    elif first_char in '([{':
        type = 'paren' if first_char == '(' else 'list' \
            if first_char == '[' else 'lambda'
        brackets[type] = 1
    elif exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif first_char in op_list:
        return 'op', first_char, exp[1:]
    else:
        raise SyntaxError('unknown symbol: {}'.format(first_char))

    i = 1   
    while i < len(exp):
        char = exp[i]

        if type in brackets:
            if balanced(brackets): break
        elif char.isspace() or (type == 'number' and
            (char not in '1234567890.e' and not (e and char == '-'))) or \
        (type == 'name' and not (char.isalnum() or char in '_?')):
            break

        if type == 'number' and char == 'e':
            if e > 0: raise SyntaxError
            e = 1

        if char in r'()[]{}':
            update_brackets(char)

        i += 1

    if not balanced(brackets):
        raise SyntaxError('unpaired brackets!')

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
        tokens = []
        while content:
            type, token, content = get_token(content)
            if type == 'comma':
                break
            elif comprehension_possible and type == 'for':
                comprehension = True
            tokens.append(token)
        l.append(' '.join(tokens))
    if comprehension_possible:
        return l, comprehension
    return l


def get_params(list_str):
    return [get_name(s) for s in get_list(list_str)]