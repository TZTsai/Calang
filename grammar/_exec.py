from _obj import stack
from _eval import eval_tree


### TODO 
#   0. DEF
#   1. CMD: dir, conf, del, ...
#   2. import and load
#   3. auto indent


# track the brackets
par_stk = stack()

def push_par(par, pos):
    par_stk.push((par, pos))

def pop_par(par):
    if par_stk.peek() == par:
        par_stk.pop()
    else:
        par_stk.clear()
        raise SyntaxError('invalid parentheses')

parentheses = ')(', '][', '}{'
close_pars, open_pars = zip(*parentheses)
par_map = dict(parentheses)

class BracketUnclosedError(SyntaxError):
    "The string has unclosed parentheses."

def track_par(line):
    for i, c in enumerate(line):
        if c in open_pars: push_par(c, i)
        elif c in close_pars: pop_par(par_map[c])
    if par_stk:
        raise BracketUnclosedError(par_stk.peek())



if __name__ == "__main__":
    import doctest
    doctest.testmod()