from __builtins import op_list, special_words


def get_token(exp):
    exp = exp.strip()

    def get_bracketed_token(exp):
        def update(f):
            def match(b):
                def change(c):
                    if b == c: cnt[0] = f(cnt[0])
                return change
            return match
        inc_match = update(lambda n: n+1)
        dec_match = update(lambda n: n-1)
        cnt = [0]
        if exp[0] is '(':
            inc = inc_match('('); dec = dec_match(')')
        elif exp[0] is '[':
            inc = inc_match('['); dec = dec_match(']')
        elif exp[0] is '{':
            inc = inc_match('{'); dec = dec_match('}')

        for i in range(len(exp)):
            inc(exp[i]); dec(exp[i])
            if cnt[0] == 0: break
        return exp[:i+1], exp[i+1:]

    first_char = exp[0]
    if first_char is ',':
        return 'comma', ',', exp[1:]
    if first_char is ':':
        return 'colon', ':', exp[1:]
    if first_char is ';':
        return 'semicolon', ';', exp[1:]
    elif first_char.isdigit() or first_char in '.':
        type = 'number'
    elif first_char.isalpha() or first_char is '_':
        type = 'name'
    elif first_char in '([{':
        type = 'paren' if first_char is '(' else 'list' \
            if first_char is '[' else 'lambda'
        token, rest = get_bracketed_token(exp)
        return type, token, rest
    elif first_char in ')]}':
        raise SyntaxError('unpaired brackets!')
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
        elif char.isspace() or \
            (type is 'number' and not (char in '1234567890.')) or \
            (type is 'name' and not (char.isalnum() or char in '_?')):
            break

        i += 1

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
    token_groups = grouped_tokens(exp, delimiter)
    return [' '.join(group) for group in token_groups]


def get_list(list_exp, delimiter=','):
    return split(list_exp[1:-1], delimiter)


def get_params(list_str):
    return [get_name(s) for s in get_list(list_str)]