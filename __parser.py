from __builtins import op_list, special_words


def get_token(exp):
    """ split out the first token of exp and return its type, the token itself,
    and the rest of exp """

    def match(exp, condition, start=0):
        i, n = start, len(exp)
        while i < n and condition(exp[i]):
            i += 1
        return i

    def get_bracketed_token(exp):
        def update_stack(stack, char):
            pairs = ('()', '[]', '{}')
            for p in pairs:
                if char in p:
                    if char == p[0]:
                        stack.append(char)
                    elif stack[-1] != p[0]:
                        raise SyntaxError
                    else:
                        stack.pop()
                    break
        stack = []
        for i in range(len(exp)):
            try:
                update_stack(stack, exp[i])
            except SyntaxError:
                raise SyntaxError(f'unpaired brackets in "{exp[i-14:i+1]}"')
            if stack == []:
                break
        if stack:
            raise SyntaxError(f'unpaired brackets in "{exp[-15:]}"')
        return exp[:i+1], exp[i+1:]

    exp = exp.strip()

    if exp[0] is ',':
        return 'comma', ',', exp[1:]
    elif exp[0] is ':':
        return 'colon', ':', exp[1:]
    elif exp[0].isdigit():
        m = match(exp, lambda c: c.isdigit() or c is '.')
        if m+1 < len(exp) and exp[m] == 'e':  # scientific notation
            start = m+2 if exp[m+1] == '-' else m+1
            m = match(exp, lambda c: c.isdigit(), start)
        return 'number', exp[:m], exp[m:]
    elif exp[0].isalpha():  # name
        m = match(exp, lambda c: c.isalnum() or c in '_?')
        token, rest = exp[:m], exp[m:]
        if token in op_list:  # operation
            return 'op', token, rest
        elif token in special_words:  # keyword
            return token, token, rest
        else:
            return 'name', token, rest
    elif exp[0] is '_':
        m = match(exp, lambda c: c.isalnum() or c is '_', 1)
        token, rest = exp[:m], exp[m:]
        _type = 'ans' if len(
            token) is 1 or not token[1].isalpha() else 'symbol'
        return _type, token, rest
    elif exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif exp[0] in op_list:
        return 'op', exp[0], exp[1:]
    elif exp[0] in '([{':
        _type = 'paren' if exp[0] is '(' else 'bracket' \
            if exp[0] is '[' else 'brace'
        token, rest = get_bracketed_token(exp)
        return _type, token, rest
    elif exp[0] in ')]}':
        raise SyntaxError(f'unpaired brackets in {exp[:15]}')
    else:
        raise SyntaxError(f'unknown symbol: {exp[0]}')


def get_name(exp, no_rest=True):
    _type, name, rest = get_token(exp)
    if not _type == 'name' or (no_rest and rest):
        raise SyntaxError(f'invalid variable name: {exp}!')
    if no_rest:
        return name
    return name, rest


def split(exp, delimiter, maxnum=None):
    segs, num = [], 1
    while exp:
        if num == maxnum:
            segs.append(exp)
            break
        tokens = []
        while exp:
            _, token, exp = get_token(exp)
            if token == delimiter:
                break
            tokens.append(token)
        segs.append(' '.join(tokens))
        num += 1
    return segs


def get_list(list_exp, delimiter=','):
    return split(list_exp[1:-1], delimiter)


def get_params(list_str):
    return [get_name(s) for s in get_list(list_str)]


# test
print(split('1,2,3,4', ','))
print(split('1,2,3,4', ',', 2))