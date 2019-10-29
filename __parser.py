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
    if first_char is ',':
        return 'comma', ',', exp[1:]
    elif first_char.isdigit() or first_char in '.':
        type = 'number'
    elif first_char.isalpha() or first_char is '_':
        type = 'name'
    elif first_char in '([{':
        type = 'paren' if first_char is '(' else 'list' \
            if first_char is '[' else 'lambda'
        brackets[type] = 1
    elif first_char in ')]}':
        raise SyntaxError('unpaired brackets!')
    elif first_char is ',':
        return 'comma', ',', exp[1:]
    elif exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif first_char in op_list:
        return 'op', first_char, exp[1:]
    else:
        raise SyntaxError('unknown symbol: {}'.format(first_char))

    i = 1   
    while i < len(exp):
        char = exp[i]
        if type is 'number' and char is 'e':
            if i == len(exp)-1:
                raise SyntaxError('invalid scientific notation!')
            elif exp[i+1] is '-':
                i += 1
            elif not exp[i+1].isdigit():
                break
        elif type in brackets:
            if balanced(brackets): break
        elif char.isspace() or\
        (type is 'number' and not (char in '1234567890.')) or \
        (type is 'name' and not (char.isalnum() or char in '_?')):
            break

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