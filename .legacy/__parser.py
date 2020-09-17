from __builtins import op_list, special_words, inf, first
from utils.greek import escape_to_greek
from myutils import trace, log
import re

def match(exp, pattern, start=0):
    exp = exp[start:]
    m = re.match(f'{pattern}', exp)
    return start + m.end() if m else start

def match_name(exp):
    exp = exp.strip()
    name_re = r'[a-zA-Z\u0374-\u03FF\d_]+[?]?'
    m = match(exp, f'({name_re}[.])*{name_re}')
    return exp[:m], exp[m:]
    

class IncompleteLine(SyntaxError):
    "Indicate that this line is not complete."


bracket_pairs = ('()', '[]', '{}')

def get_bracket(exp):
    stack = []
    for i, c in enumerate(exp):
        for p in bracket_pairs:
            if c in p:
                if c == p[0]:
                    stack.append((c, i))
                elif stack[-1][0] == p[0]:
                    _, j = stack.pop()
                    if not stack: yield exp[j:i+1], exp[i+1:]
                else:
                    raise SyntaxError(f'unpaired brackets in "{exp[i-14:i+1]}"!')
                break
    if stack: raise IncompleteLine(stack[-1][1]+1)


closure_kwds = ('lambda', 'with')

def get_colon_token(exp):
    pos, stack, tokens = 0, [], []
    while exp:
        token, exp = match_name(exp)
        type_ = token
        if not token:
            type_, token, exp = get_token(exp)
        pos += len(token)
        if type_ in closure_kwds:
            stack.append(pos)
        elif token == ':':
            if stack: stack.pop()
            else: return
        tokens.append(token)
        if not stack:
            yield ' '.join(tokens), exp
    if stack:
        raise IncompleteLine(stack.pop()+1)


def get_token(exp):
    """ split out the first token of exp and return its type, the token itself,
    and the rest of exp
    >>> get_token('lambda:')
    ('lambda', 'lambda :', '')
    >>> get_token('lambda x , y: x + y')[1:]
    ('lambda x , y :', ' x + y')
    >>> get_token('[3, [4, 5]] + [6]')[1]
    '[3, [4, 5]]'
    """

    exp = exp.strip()
    if not exp:
        raise ValueError('no more tokens')

    exp = escape_to_greek(exp)

    if exp[0].isdigit():  # number
        m = match(exp, r'\d*')
        if m < len(exp) and exp[m] == '.':
            if exp[m+1] != '.':  # double dot - a range
                m = match(exp, r'\d*', start=m+1)
        if m+1 < len(exp) and exp[m] == 'e':  # scientific notation
            start = m+2 if exp[m+1] == '-' else m+1
            m = match(exp, r'\d*', start)
        return 'number', exp[:m], exp[m:]
    if exp[0].isalpha():  # name
        token, rest = match_name(exp)
        if token in op_list:  # operation
            return 'op', token, rest
        elif token in special_words:  # keyword
            type_ = token
            if token in closure_kwds:
                token, rest = next(get_colon_token(exp))
            return type_, token, rest
        else:
            return 'attribute' if '.' in token else 'name', token, rest

    # special symbols
    if exp[:2] == ':=':
        return 'assign', ':=', exp[2:]
    if exp[0] in ",:;|'":
        return exp[0], exp[0], exp[1:]
    if exp[0] == '_':
        m = match(exp, '[A-Za-z0-9_]*', 1)
        token, rest = exp[:m], exp[m:]
        type_ = 'ans' if token == '_' or not token[1].isalpha() else 'symbol'
        return type_, token, rest
    if exp[:2] == '=>':
        return 'arrow', '=>', exp[2:]
    if exp[:2] in op_list:
        return 'op', exp[:2], exp[2:]
    if exp[0] in op_list:
        return 'op', exp[0], exp[1:]
    if exp[0] in '([{':
        type_ = 'paren' if exp[0] == '(' else 'bracket' \
            if exp[0] == '[' else 'brace'
        token, rest = next(get_bracket(exp))
        return type_, token, rest
    if exp[0] in ')]}':
        raise SyntaxError(f'unpaired brackets in {exp[:15]}')
    raise SyntaxError(f'unknown symbol: {exp[0]}')


def get_name(exp, no_rest=True):
    type_, name, rest = get_token(exp)
    if not type_ == 'name' or (no_rest and rest):
        raise SyntaxError(f'invalid variable name: {exp}!')
    if no_rest: return name
    return name, rest


def split(exp, delimiter, maxnum=inf):
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
    >>> split('lambda x, y: 1, 2', ',')
    ['lambda x , y : 1', '2']
    """
    exp = exp.strip()
    if not exp: return []
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
    """
    >>> get_list('[]')
    []
    """
    if list_exp[0] not in '[(' or list_exp[-1] not in ')]':
        raise SyntaxError("not a list expression")
    return split(list_exp[1:-1], delimiter)


def get_params(list_str):
    return [get_name(s) for s in get_list(list_str)]


if __name__ == "__main__":
    import doctest
    doctest.testmod()
