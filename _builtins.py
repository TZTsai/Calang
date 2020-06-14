from operator import floordiv, mod, neg, lt, gt, le, ge, xor, inv
from functools import reduce
from numbers import Number, Rational
from fractions import Fraction
from math import inf
from sympy import (
    sqrt, log, exp, gcd, factorial, floor, E, pi,
    sin, cos, tan, asin, acos, atan, cosh, sinh, tanh, 
    solve, limit, integrate, diff, simplify, expand, factor, 
    Integer, Float, Matrix, Expr
)

from _obj import Op, Env, config, Range
from _funcs import (
    is_iter, is_function, is_matrix, is_number, is_vector, is_symbol, is_list, 
    add, sub, mul, div, dot, power, and_, or_, not_, eq_, ne_, adjoin,
    iadd, isub, imul, idiv, ipow, iand, ior, 
    dot, dbfact, all_, any_, first, findall, range_, compose,
    transpose, depth, shape, substitute, flatten, row, col, row, cols, 
)


def process_func(val):

    def pynumfy(val):
        # convert a number into a python number type
        if any(isinstance(val, c) for c in (int, float, complex, Fraction)):
            return val
        elif isinstance(val, Integer):
            return int(val)
        elif isinstance(val, Float):
            return float(val)
        else:
            z = complex(val)
            if eq_(z.imag, 0): return z.real
            else: return z

    def canonical(f):
        def fun(*args, **kwds):
            r = f(*args, **kwds)
            if type(r) is bool:
                return 1 if r else 0
            elif is_iter(r) and not (isinstance(r, Range) or isinstance(r, set)):
                return tuple(fun(a) for a in r)
            else:
                try: return pynumfy(r)
                except (ValueError, TypeError):
                    if isinstance(r, Expr): return factor(simplify(r))
                    else: return r
        return fun

    return canonical(val)


def construct_ops(op_dict, type_):
    for op in op_dict:
        fun, pri = op_dict[op]
        # assert is_function(fun)
        fun = process_func(fun)
        fun.__name__ = op
        op_dict[op] = Op(type_, fun, pri)


binary_ops = {
    '+': (add, 6), '-': (sub, 6), '*': (mul, 8), '/': (div, 8), '^': (power, 18),
    '//': (floordiv, 8), '%': (mod, 8), '⋅': (dot, 10), '(adj)': (adjoin, 20),
    '+.': (iadd, 5), '-.': (isub, 5), '*.': (imul, 7), '/.': (idiv, 7), '^.': (ipow, 13),
    '&.': (iand, 8), '|.': (ior, 7),
    '==': (eq_, 0), '/=': (ne_, 0), '<': (lt, 0), '>': (gt, 0), '<=': (le, 0), '>=': (ge, 0), 
    'xor': (xor, 3), 'in': (lambda x, y: x in y, -2), 'outof': (lambda x, y: x not in y, -2), 
    '~': (Range, 5), '..': (range_, 4), 'and': (and_, -5), 'is': (None, 0), 'or': (or_, -6),  '@': (None, 0)
}
unary_l_ops = {'-': (neg, 10), 'not': (not_, -4), '~.': (inv, 10), '@': (transpose, 10)}
unary_r_ops = {'!': (factorial, 20), '!!': (dbfact, 20)}

construct_ops(binary_ops,   'BOP')
construct_ops(unary_l_ops,  'LOP')
construct_ops(unary_r_ops,  'ROP')

op_list = set(binary_ops).union(set(unary_l_ops)).union(set(unary_r_ops))


keywords = {'if', 'else', 'in', 'dir', 'load', 'conf', 'when', 'import', 'del'}


builtins = {'sin': sin, 'cos': cos, 'tan': tan, 'asin': asin, 'acos': acos, 'atan': atan, 'abs': abs, 'sqrt': sqrt, 'floor': floor, 'log': log, 'E': E, 'PI': pi, 'I': 1j, 'INF': inf, 'max': max, 'min': min, 'gcd': gcd, 'binom': lambda n, m: factorial(n) / (factorial(m) * factorial(n-m)), 'len': len, 'sort': sorted, 'exit': lambda: exit(), 'exp': exp, 'lg': lambda x: log(x)/log(10), 'ln': log, 'log2': lambda x: log(x)/log(2), 'number?': is_number, 'symbol?': is_symbol, 'iter?': is_iter, 'lambda?': is_function, 'matrix?': is_matrix, 'vector?': is_vector, 'function?': is_function, 'list?': is_list, 'list': list, 'sum': lambda l: reduce(add, l), 'product': lambda l: reduce(dot, l), 'matrix': Matrix, 'set': set, 'car': lambda l: l[0], 'cdr': lambda l: l[1:], 'cons': lambda a, l: (a,) + l, 'enum': enumerate, 'row': row, 'col': col, 'shape': shape, 'depth': depth, 'transp': transpose, 'flatten': flatten, 'all': all_, 'any': any_, 'same': lambda l: True if l == [] else all(x == l[0] for x in l[1:]), 'sinh': sinh, 'cosh': cosh, 'tanh': tanh, 'degrees': lambda x: x / pi * 180, 'real': lambda z: z.real if type(z) is complex else z, 'imag': lambda z: z.imag if type(z) is complex else 0, 'conj': lambda z: z.conjugate(), 'angle': lambda z: atan(z.imag / z.real), 'reduce': reduce, 'filter': filter, 'map': map, 'zip': zip, 'find': findall, 'solve': solve, 'lim': limit, 'diff': diff, 'int': integrate, 'subs': substitute, 'expand': expand, 'factor': factor}

for name in builtins:
    val = builtins[name]
    if is_function(val):
        val = process_func(val)
        builtins[name] = val
        val.__name__ = f'<builtin: {name}>'

