from _obj import stack


# track the brackets
par_stk = stack()

def push_par(par, pos):
    par_stk.push((par, pos))

def pop_par(par):
    if par_stk.peek() == par:
        par_stk.pop()
    else:
        par_stk.clear()
        raise SyntaxError('unexpected closing parenthesis')

parentheses = '()', '[]', '{}'
open_pars, close_pars = zip(*parentheses)
par_map = dict(zip(close_pars, open_pars))

class BracketUnclosedError(SyntaxError):
    "The string has unclosed parentheses."

def track_par(line):
    for i, c in enumerate(line):
        if c in open_pars: push_par(c, i)
        elif c in close_pars: pop_par(par_map[c])
    if par_stk:
        raise BracketUnclosedError(par_stk.peek())