from functools import reduce
from numbers import Number, Rational
from fractions import Fraction
from math import inf
from operator import floordiv, mod, neg, lt, gt, le, ge, xor, inv
import symengine  # TODO: use this to do symbolic calculation
from sympy import (
    S, E, pi, nan,
    Array, Matrix,
    floor, ceiling, factorial, expand, factor, solve,
    sqrt, log, exp, gamma,
    gcd, factorint, binomial,
    sin, cos, tan, asin, acos, atan, cosh, sinh, tanh,
    limit, integrate, diff
)
import config
from objects import Op, Env, Range, Builtin, Enum
from funcs import *


def construct_ops(op_dict, type):
    for op in op_dict:
        fun, pri = op_dict[op]
        op_dict[op] = Op(type, op, fun, pri)
        
        
def log2(x): return log(x) / log(2)
def log10(x): return log(x) / log(10)
def sum(*x): return reduce(add_, x, initial=0)
def prod(*x): return reduce(dot, x, initial=1)
def deg(x): return x / 180 * pi
def ang(z): return atan(z.imag / z.real)


binary_ops = {
    '+': (add_, 6), '-': (sub_, 6), '*': (mul_, 8), '/': (div_, 8), '^': (pow_, 18),
    '//': (floordiv, 8), '%': (mod, 8), '÷': (divmod, 8), '⋅': (dot, 10),
    '/\\': (and_, 8), '\\/': (or_, 7), 'xor': (xor, 3),
    '==': (eq_, 0), '~=': (ne_, 0), '<': (lt, 0), '>': (gt, 0), '<=': (le, 0), '>=': (ge, 0), 
    'in': (lambda x, y: x in y, -2), ':': (range_, 4), '.': (index, 16),
    '(get)': (getattr_, 20), '(app)': (apply, 22)
}
unary_l_ops = {'-': (neg, 10), 'not': (not_, -4), '~': (inv, 10), '∠': (ang, 4)}
unary_r_ops = {'!': (factorial, 22), '..': (unpack, 11), '°': (deg, 24), "'": (transpose, 15)}

operators = {'BOP': binary_ops, 'LOP': unary_l_ops, 'ROP': unary_r_ops}

for op_type, op_dict in operators.items():
    construct_ops(op_dict, op_type)

shortcircuit_ops = operators['SOP'] = ['or', 'if', 'and']

binary_ops['(app)'].broadcast = False


builtins = {
    # constants
    'euler': E, 'ℯ': E, 'pi': pi, 'π': pi, 'φ': S.GoldenRatio, 'im': 1j, 'ⅈ': 1j, '∞': inf,
    # common functions
    'abs': abs, 'sqrt': sqrt, 'floor': floor, 'ceil': ceiling, 
    # list functions
    'list': tuple, 'len': len, 'sort': sorted, 'max': max, 'min': min,
    'enum': enumerate, 'zip': zip, 'sum': sum, 'prod': prod,
    'all': all_, 'any': any_, 'find': findall, 'next': next,
    # array functions
    'matrix': Matrix, 'shape': shape, 'depth': depth, 'transp': transpose, 'flatten': flatten,
    # real valued functions
    'exp': exp, 'log': log, 'ln': log, 'lg': log10, 'log2': log2,
    # higher order functions
    'compose': compose, 'reduce': reduce, 'filter': filter, 'map': map,
    # triangular functions
    'sin': sin, 'cos': cos, 'tan': tan, 'asin': asin, 'acos': acos, 'atan': atan, 
    'sinh': sinh, 'cosh': cosh, 'tanh': tanh,
    # symbolic functions
    'solve': solve, 'lim': limit, 'diff': diff, 'int': integrate, 'subs': substitute,
    'expand': expand, 'factor': factor,
    # whole number functions
    'gcd': gcd, 'factorial': factorial, 'binomial': binomial, 'factors': factorint
}

for name, val in builtins.items():
    if callable(val):
        builtins[name] = Builtin(val, name)
