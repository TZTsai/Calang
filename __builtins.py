from operator import add, sub, mul, floordiv, mod, and_, or_, ne, neg, lt, gt, le, ge, xor
from operator import pow as expt
from functools import reduce
from numbers import Number, Rational
from fractions import Fraction
from math import e, pi, inf, log10
from sympy import Symbol, solve, limit, integrate, diff, simplify, evalf, Number as sympyNumber, \
    sqrt, log, exp, gcd, factorial, floor, sin, cos, tan, asin, acos, atan, cosh, sinh, tanh
from __classes import Op


def is_number(value):
    return isinstance(value, Number) or isinstance(value, sympyNumber)

def is_symbol(value):
    return type(value) == Symbol


def is_iterable(value):
    return hasattr(value, "__iter__")


def is_function(value):
    return callable(value)


def index(lst, index):
    if not hasattr(lst, '__getitem__'):
        raise SyntaxError('{} is not subscriptable'.format(lst))
    return tuple(lst[i] for i in index) if is_iterable(index) else lst[index]


def to_list(lst):
    def ifIter_toList(obj):
        if hasattr(obj, '__iter__'):
            return tuple(ifIter_toList(it) for it in obj)
        return obj

    if not hasattr(lst, '__iter__'):
        raise ValueError('{} is not iterable!'.format(lst))
    return ifIter_toList(lst)


def compose(f, g):
    return lambda *args: f(g(*args))


def boolToBin(op):
    return compose(lambda b: 1 if b else 0, op)


def reconstruct(op_dict, type):
    for op in op_dict:
        info = op_dict[op]
        op_dict[op] = Op(op, type, info[0], info[1])


def smart_div(x, y):
    if all(isinstance(w, Rational) for w in (x, y)):
        return Fraction(x, y)
    return x / y

def substitute(exp, *bindings):
    if is_iterable(exp):
        return tuple(substitute(x, *bindings) for x in exp)
    return exp.subs(zip([bindings[i] for i in range(len(bindings)) if i%2 == 0],
                        [bindings[i] for i in range(len(bindings)) if i%2 == 1]))


binary_ops = {'+': (add, 6), '-': (sub, 6), '*': (mul, 8), '/': (smart_div, 8),
              '//': (floordiv, 8), '^': (expt, 14), '%': (mod, 8), '&': (and_, 4), '|': (or_, 2),
              '=': (lambda x, y: 1 if x == y else 0, 0), '!=': (boolToBin(ne), 0),
              '<': (boolToBin(lt), 0), '>': (boolToBin(gt), 0), '<=': (boolToBin(le), 0),
              '>=': (boolToBin(ge), 0), 'xor': (boolToBin(xor), 3),
              'in': (lambda x, l: 1 if x in l else 0, -2),
              '@': (index, 16), '~': (lambda a, b: range(a, b + 1), 5),
              'and': (boolToBin(lambda a, b: a and b), -5),
              'or': (boolToBin(lambda a, b: a or b), -6)}
reconstruct(binary_ops, 'bin')

unitary_l_ops = {'-': (neg, 10), 'not': (lambda n: 1 if n == 0 else 1, -4)}
reconstruct(unitary_l_ops, 'uni_l')

unitary_r_ops = {'!': (factorial, 99)}
# actually a unitary op on the right will always be immediately carried out
reconstruct(unitary_r_ops, 'uni_r')

op_list = list(binary_ops) + list(unitary_l_ops) + list(unitary_r_ops)

special_words = {'if', 'else', 'cases', 'for', 'in', 'ENV', 'load', 'format', 'import'}

builtins = {'sin': sin, 'cos': cos, 'tan': tan, 'asin': asin, 'acos': acos,
            'atan': atan, 'abs': abs, 'sqrt': sqrt, 'floor': floor, 'log': log,
            'E': e, 'PI': pi, 'I': 1j, 'INF': inf, 'range': range, 'max': max, 'min': min, 'gcd': gcd,
            'binom': lambda n, m: factorial(n) / factorial(m), 'fact': factorial, 'len': len, 'sort': sorted,
            'exp': exp, 'lg': lambda x: log(x)/log(10), 'ln': log, 'log2': lambda x: log(x)/log(2),
            'empty?': lambda l: 0 if len(l) else 1, 'number?': boolToBin(is_number), 'symbol?': boolToBin(is_symbol),
            'iter?': boolToBin(is_iterable), 'function?': boolToBin(is_function), 'list': to_list, 
            'sum': lambda l: reduce(add, l), 'prod': lambda l: reduce(mul, l),
            'car': lambda l: l[0], 'cdr': lambda l: l[1:],
            'all': all, 'any': any, 'same': lambda l: True if l == [] else all(x == l[0] for x in l[1:]),
            'sinh': sinh, 'cosh': cosh, 'tanh': tanh, 'degrees': lambda x: x / pi * 180,
            'real': lambda z: z.real if type(z) is complex else z, 'imag': lambda z: z.imag if type(z) is complex else z, 
            'conj': lambda z: z.conjugate(), 'angle': lambda z: atan(z.imag / z.real),
            'reduce': reduce, 'filter': compose(tuple, filter), 'map': compose(tuple, map), 
            'solve': solve, 'lim': limit, 'diff': diff, 'int': integrate, 'subs': substitute, 'simp': simplify}
