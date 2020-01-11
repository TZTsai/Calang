from __builtins import op_list, special_words


def get_token(exp):
    exp = exp.strip()

    def get_bracketed_token(exp):
        def update(f):
            def match(b):
                def change(c):
                    nonlocal cnt
                    if b == c: cnt = f(cnt)
                return change
            return match
        inc_match = update(lambda n: n+1)
        dec_match = update(lambda n: n-1)
        cnt = 0
        if exp[0] is '(':
            inc = inc_match('('); dec = dec_match(')')
        elif exp[0] is '[':
            inc = inc_match('['); dec = dec_match(']')
        elif exp[0] is '{':
            inc = inc_match('{'); dec = dec_match('}')

        for i in range(len(exp)):
            inc(exp[i]); dec(exp[i])
            if cnt == 0: break
        if cnt: raise SyntaxError(f'unpaired brackets in {exp[-15:]}')
        return exp[:i+1], exp[i+1:]
    
    def match(exp, condition, start=0):
        i, n = start, len(exp)
        while i < n and condition(exp[i]): i += 1
        return i

    if exp[0] is ',':
        return 'comma', ',', exp[1:]
    elif exp[0] is ':':
        return 'colon', ':', exp[1:]
    elif exp[0] is ';':
        return 'semicolon', ';', exp[1:]
    elif exp[0] is '"':
        return 'ans', '.-2', exp[1:]
    elif exp[0] is '\'':
        m = match(exp, lambda c: c.isdigit(), 1)
        return 'ans', exp[:m], exp[m:]
    elif exp[0].isdigit():
        m = match(exp, lambda c: c in '0123456789.')
        if m+1 < len(exp) and exp[m] == 'e':  # scientific notation
            start = m+2 if exp[m+1] == '-' else m+1
            m = match(exp, lambda c: c.isdigit(), start)
        return 'number', exp[:m], exp[m:]
    elif exp[0].isalpha() or exp[0] is '_':
        m = match(exp, lambda c: c.isalnum() or c in '_?')
        token, rest = exp[:m], exp[m:]
        if token in op_list:  # operation
            return 'op', token, rest
        elif token in special_words:  # keyword
            return token, token, rest
        if token[0] is '_':  # symbol
            type = 'symbol'
        else:  # variable name
            type = 'name'
        return type, token, rest
    elif exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    elif exp[0] in op_list:
        return 'op', exp[0], exp[1:]
    elif exp[0] in '([{':
        type = 'paren' if exp[0] is '(' else 'bracket' \
            if exp[0] is '[' else 'brace'
        token, rest = get_bracketed_token(exp)
        return type, token, rest
    elif exp[0] in ')]}':
        raise SyntaxError(f'unpaired brackets in {exp[:15]}')
    else:
        raise SyntaxError(f'unknown symbol: {exp[0]}')


def get_name(exp, no_rest=True):  
    type, name, rest = get_token(exp)
    if not type == 'name' or (no_rest and rest):
        raise SyntaxError(f'invalid variable name: {exp}!')
    if no_rest: return name
    return name, rest


def split(exp, delimiter):
    def grouped_tokens(exp, delimiter):
        def gen():
            nonlocal exp, stop
            while exp:
                _, token, exp = get_token(exp)
                if token == delimiter: return
                yield token
            stop = True
        stop = False
        while not stop: yield gen()
    if not exp: return []
    token_groups = grouped_tokens(exp, delimiter)
    return [' '.join(group) for group in token_groups]


def get_list(list_exp, delimiter=','):
    return split(list_exp[1:-1], delimiter)


def get_params(list_str):
    return [get_name(s) for s in get_list(list_str)]