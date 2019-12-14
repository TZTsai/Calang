from operator import *
from operator import pow as expt
from math import *
from functools import reduce
from numbers import Number
from  __classes import Op


def isNumber(value):
    return issubclass(type(value), Number)

def isIterable(value):
    return hasattr(value, "__iter__")

def isFunction(value):
    return callable(value)

def subscript(lst, index):
    if not hasattr(lst, '__getitem__'):
        raise SyntaxError('{} is not subscriptable'.format(lst))
    return [lst[i] for i in index] if isIterable(index) else lst[index]

def toList(lst):
    def ifIter_toList(obj):
        if hasattr(obj, '__iter__'):
            return [ifIter_toList(it) for it in obj]
        return obj
    if not hasattr(lst, '__iter__'):
        raise ValueError('{} is not iterable!'.format(lst))
    return ifIter_toList(lst)

def compose(f, g):
    return lambda *args: f(g(*args))

def boolToBin(op):
    return compose(lambda b: 1 if b else 0, op)

def concatLists(l1, l2):
    l1.extend(l2)
    return l1

def reconstruct(op_dict, type):
    for op in op_dict:
        info = op_dict[op]
        op_dict[op] = Op(op, type, info[0], info[1])


from decimal import Decimal, getcontext
from fractions import Fraction
decimal_div = lambda x, y: Decimal(x)/Decimal(y)
fractal_div = lambda x, y: Fraction(x)/Fraction(y)
getcontext().prec = 4

binary_ops = {'+':(add, 6), '-':(sub, 6), '*':(mul, 8), '/':(fractal_div, 8),
'//':(floordiv, 8), '^':(expt, 14), '%':(mod, 8), '&':(and_, 4), '|':(or_, 2),
'=':(lambda x, y: 1 if x == y else 0, 0), '!=':(boolToBin(ne), 0),
'<':(boolToBin(lt), 0), '>':(boolToBin(gt), 0), '<=':(boolToBin(le), 0), 
'>=':(boolToBin(ge), 0), 'xor': (boolToBin(xor), 3), 
'in': (lambda x, l: 1 if x in l else 0, -2), 
'@':(subscript, 16), '~': (lambda a, b: range(a, b+1), 5),
'and': (boolToBin(lambda a, b: a and b), -5),
'or': (boolToBin(lambda a, b: a or b), -6)}
reconstruct(binary_ops, 'bin')

unitary_l_ops = {'-':(neg, 10), 'not':(lambda n: 1 if n == 0 else 1, -4)}
reconstruct(unitary_l_ops, 'uni_l')

unitary_r_ops = {'!': (factorial, 99)}
# actually a unitary op on the right will always be immediately carried out
reconstruct(unitary_r_ops, 'uni_r')

op_list = list(binary_ops) + list(unitary_l_ops) + list(unitary_r_ops)

special_words = set(['if', 'else', 'cases', 'for', 'in', 'ENV', 'load', 'config'])


import numpy as np
from numpy.polynomial import Polynomial
poly = lambda *coeffs: Polynomial(coeffs)
def solve(p):
    if type(p) is not Polynomial:
        raise TypeError('expected a polynomial!')
    return list(p.roots())

builtins = {'sin': sin, 'cos': cos, 'tan': tan, 'asin': asin, 'acos': acos,
'atan': atan, 'abs': abs, 'sqrt': sqrt, 'floor': floor, 'ceil': ceil, 'log': log,
'E': e, 'PI': pi, 'I': 1j, 'range': range, 'max': max, 'min': min, 'gcd': gcd,
'list': toList, 'binom': lambda n, m: factorial(n)/factorial(m), 'log10': log10,
'log2': log2, 'exp': exp, 'fact': factorial, 'len': len, 'sort': sorted, 
'empty?': lambda l: 0 if len(l) else 1, 'number?': boolToBin(isNumber),
'iter?': boolToBin(isIterable), 'function?': boolToBin(isFunction),
'list?': lambda l: 1 if isinstance(l, list) else 0, 
'range?': lambda l: 1 if isinstance(l, range) else 0,
'sum': lambda l: reduce(add, l), 'prod': lambda l: reduce(mul, l),
'car': lambda l: l[0], 'cdr': lambda l: l[1:], 
'all':all, 'any':any, 'same': lambda l: True if l == [] else all(x == l[0] for x in l[1:]),
'sinh':sinh, 'cosh':cosh, 'tanh':tanh, 'degrees':degrees, 
'real': lambda z: z.real, 'imag': lambda z: z.imag, 'conj': lambda z: z.conjugate(),
'angle': lambda z: atan(z.imag/z.real), 
'reduce': reduce, 'filter': compose(list, filter), 'map': compose(list, map),
'poly': poly, 'solve': solve, 'array': lambda *a: np.array(a)}