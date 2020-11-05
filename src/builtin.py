from operator import floordiv, mod, neg, lt, gt, le, ge, xor, inv
from functools import reduce
from numbers import Number, Rational
from fractions import Fraction
from math import inf
from sympy import (
    sqrt, log, exp, gcd, factorial, floor, E, pi, factorint,
    sin, cos, tan, asin, acos, atan, cosh, sinh, tanh, 
    solve, limit, integrate, diff, expand, factor, Matrix
)

import config
from objects import Op, Env, Range, PyFunc, Builtin
from funcs import (
    is_iter, is_function, is_matrix, is_number, is_vector, is_symbol, is_list, apply,
    add, sub, mul, div, power, and_, or_, not_, eq_, ne_, iadd, isub, imul, idiv, ipow, iand, ior, 
    adjoin, unpack, dot, fact2, all_, any_, first, findall, range_, range_inc, range_dec, compose,
    transpose, depth, shape, substitute, flatten, row, col, row, cols, help_
)


def construct_ops(op_dict, type):
    for op in op_dict:
        fun, pri = op_dict[op]
        fun = PyFunc(fun)
        op_dict[op] = Op(type, op, fun, pri)


binary_ops = {
    '+': (add, 6), '-': (sub, 6), '*': (mul, 8), '/': (div, 8), '^': (power, 18),
    '//': (floordiv, 8), '%': (mod, 8), '.': (dot, 10),
    '.+': (iadd, 5), '.-': (isub, 5), '.*': (imul, 7), './': (idiv, 7), '.^': (ipow, 13),
    '&': (iand, 8), '|': (ior, 7),
    '==': (eq_, 0), '/=': (ne_, 0), '<': (lt, 0), '>': (gt, 0), '<=': (le, 0), '>=': (ge, 0), 
    'xor': (xor, 3), 'in': (lambda x, y: x in y, -2), 'outof': (lambda x, y: x not in y, -2), 
    '..': (range_, 4), '+..': (range_inc, 4), '-..': (range_dec, 4),
    'and': (and_, -5), 'or': (or_, -6), '': (adjoin, 20), #'of': (NotImplemented, -3)
}
unary_l_ops = {'-': (neg, 10), 'not': (not_, -4), '~': (inv, 10)}
unary_r_ops = {'!': (factorial, 22), '!!': (fact2, 22), '~': (unpack, 22)}

operators = {'BOP': binary_ops, 'LOP': unary_l_ops, 'ROP': unary_r_ops}
for op_type, op_dict in operators.items():
    construct_ops(op_dict, op_type)


builtins = {'sin': sin, 'cos': cos, 'tan': tan, 'asin': asin, 'acos': acos, 'atan': atan, 'abs': abs, 'sqrt': sqrt, 'floor': floor, 'log': log, 'E': E, 'PI': pi, 'I': 1j, 'INF': inf, 'max': max, 'min': min, 'gcd': gcd, 'binom': lambda n, m: factorial(n) / (factorial(m) * factorial(n-m)), 'len': len, 'sort': sorted, 'exp': exp, 'lg': lambda x: log(x)/log(10), 'ln': log, 'log2': lambda x: log(x)/log(2), 'number?': is_number, 'symbol?': is_symbol, 'iter?': is_iter, 'lambda?': is_function, 'matrix?': is_matrix, 'vector?': is_vector, 'function?': is_function, 'list?': is_list, 'list': tuple, 'sum': lambda *x: reduce(add, x), 'product': lambda *x: reduce(dot, x), 'compose': compose, 'matrix': Matrix, 'set': set, 'car': lambda l: l[0], 'cdr': lambda l: l[1:], 'cons': lambda a, l: (a,) + l, 'enum': enumerate, 'row': row, 'col': col, 'shape': shape, 'depth': depth, 'transp': transpose, 'flatten': flatten, 'all': all_, 'any': any_, 'same': lambda l: True if l == [] else all(x == l[0] for x in l[1:]), 'sinh': sinh, 'cosh': cosh, 'tanh': tanh, 'degrees': lambda x: x / pi * 180, 'real': lambda z: z.real if type(z) is complex else z, 'imag': lambda z: z.imag if type(z) is complex else 0, 'conj': lambda z: z.conjugate(), 'angle': lambda z: atan(z.imag / z.real), 'reduce': reduce, 'filter': filter, 'map': map, 'zip': zip, 'find': findall, 'solve': solve, 'lim': limit, 'diff': diff, 'int': integrate, 'subs': substitute, 'expand': expand, 'factor': factor, 'pfactors': factorint, 'next': next, 'help': help_}

for name, val in builtins.items():
    if callable(val):
        builtins[name] = Builtin(val)