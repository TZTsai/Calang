from __builtins import op_list, special_words, inf, first


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

    # def get_midcolon_token(exp):
    #     try:
    #         list_str, body = split(exp, ':', 2)
    #         segs = split(body, ',', 2)
    #         left = list_str + segs[0]
    #     except (ValueError, IndexError):
    #         raise SyntaxError('invalid function expression')
    #     right = exp[len(left):]
    #     return left, right

    # def get_cases_token(exp):
    #     cases = [split(case, ':') for case in split(exp, ',')]
    #     no_colon = first(lambda l: len(l) != 2, cases)
    #     cases = ' 'cases[:no_colon+1]
    #     return 

    exp = exp.strip()
    if not exp:
        raise ValueError('empty expression')

    if exp[0] == ',':
        return 'comma', ',', exp[1:]
    elif exp[0] == ':':
        return 'colon', ':', exp[1:]
    elif exp[0] == '\x0c':
        return 'function', '\x0c', exp[1:]
    elif exp[0].isdigit():
        m = match(exp, lambda c: c.isdigit() or c == '.')
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
    elif exp[0] == '_':
        m = match(exp, lambda c: c.isalnum() or c == '_', 1)
        token, rest = exp[:m], exp[m:]
        _type = 'ans' if len(
            token) == 1 or not token[1].isalpha() else 'symbol'
        return _type, token, rest
    elif exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif exp[0] in op_list:
        return 'op', exp[0], exp[1:]
    elif exp[0] in '([{':
        _type = 'paren' if exp[0] == '(' else 'bracket' \
            if exp[0] == '[' else 'brace'
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


def split(exp, delimiter, /, maxnum=inf):
    """
    >>> split('1 , 3 ,', ',')
    ['1', '3', '']
    >>> split('1,2 +  t,3,4*8', ',')
    ['1', '2 + t', '3', '4 * 8']
    >>> split('f(x), 2,f(x) ,4', ',', 2)
    ['f (x)', ' 2,f(x) ,4']
    >>> split('a,, b,, c', ',', 4)
    ['a', '', 'b', ', c']
    >>> split(' ', ',')
    []
    """
    if not exp.strip():
        return []
    segs, num = [], 1
    while num < maxnum and len(segs) < num:
        tokens = []
        while exp:
            _, token, exp = get_token(exp)
            if token == delimiter:
                num += 1
                break
            tokens.append(token)
        segs.append(' '.join(tokens))
    if num == maxnum:
        segs.append(exp)
    return segs


def get_list(list_exp, delimiter=','):
    return split(list_exp[1:-1], delimiter)


def get_params(list_str):
    return [get_name(s) for s in get_list(list_str)]


if __name__ == "__main__":
    import doctest
    doctest.testmod()
