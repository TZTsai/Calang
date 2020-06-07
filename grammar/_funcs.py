from operator import add, sub, mul, pow as pow_
from functools import reduce
from numbers import Number, Rational
from fractions import Fraction
from sympy import Matrix, Symbol
from _obj import config, Range, function


def is_number(value):
    return isinstance(value, Number)


def is_symbol(value):
    return isinstance(value, Symbol)


def is_iter(value):
    return hasattr(value, "__iter__")


def is_list(value):
    return isinstance(value, tuple)


def is_vector(value):
    return depth(value) == 1


def is_matrix(value):
    return isinstance(value, Matrix) or value.mat


def is_function(value):
    return callable(value)


def equal(x, y):
    if is_number(x) and is_number(y):
        return abs(x - y) <= config.tolerance
    else: return x == y

    
def db_fact(x):  # returns x!!
    if not isinstance(x, int) or x < 0:
        raise ValueError('invalid argument for factorial!')
    if x in (0, 1): return 1
    else: return x * db_fact(x-2)


def all_(condition, *lst):
    if condition: return all(map(condition, lst))
    else: return all(lst)


def any_(condition, *lst):
    if condition: return any(map(condition, lst))
    else: return any(lst)


def same(lst):
    if not lst: return True
    x = lst[0]
    return all(equal(x, y) for y in lst[1:])


def div_(x, y):
    if all(isinstance(w, Rational) for w in (x, y)):
        return Fraction(x, y)
    return x / y


def substitute(exp, *bindings):
    if is_iter(exp):
        return tuple(substitute(x, *bindings) for x in exp)
    if hasattr(exp, 'subs'):
        return exp.subs(bindings)
    return exp


add_ = function.operator('+', add)
sub_ = function.operator('-', sub)
mul_ = function.operator('*', mul)


def power(x, y):
    if is_list(x):
        return reduce(dot, [x] * y)
    elif isinstance(x, function) and isinstance(y, int):
        f = x
        for _ in range(1, y): f = x.compose(f)
        return f
    else:
        return pow_(x, y)


def depth(value):
    if not is_iter(value): return 0
    if len(value) == 0: return 1
    return 1 + max(map(depth, value))


def index(lst, id):
    if not hasattr(lst, '__getitem__'):
        raise SyntaxError('{} is not subscriptable'.format(lst))
    if isinstance(lst, range) or isinstance(lst, Range) or not is_iter(id):
        return lst[id]
    else:
        return tuple(index(lst, i) for i in id)


def tolist(lst):
    def _tolist(obj):
        if hasattr(obj, '__iter__'):
            return tuple(_tolist(it) for it in obj)
        return obj
    if not hasattr(lst, '__iter__'):
        raise ValueError('{} is not iterable!'.format(lst))
    return _tolist(lst)


def subscript(lst, subs):
    if not subs: return lst
    index0 = subs[0]
    items = index(lst, index0)
    if is_iter(index0) or type(index0) == slice:
        return tuple(subscript(item, subs[1:]) for item in items)
    else:
        return subscript(items, subs[1:])


def shape(x):
    if not is_iter(x): return tuple()
    subshapes = [shape(a) for a in x]
    return (len(x),) + tuple(map(min, *subshapes))


def flatten(l):
    """
    >>> flatten([1,2])
    [1, 2]
    >>> flatten([[1,2,[3]],[4]])
    [1, 2, 3, 4]
    """
    if depth(l) <= 1: return l
    fl = []
    for x in l: 
        if not is_iter(x): fl.append(x)
        else: fl.extend(flatten(x))
    return fl


def row(mat, k):
    assert is_matrix(mat)
    return mat[k]

def rows(mat):
    assert is_matrix(mat)
    return len(mat)

def col(mat, k):
    assert is_matrix(mat)
    return subscript(mat, [slice(None), k])

def cols(mat):
    assert is_matrix(mat)
    return len(mat[0])

def transpose(value):
    if not is_iter(value):
        return value
    elif is_vector(value):
        return transpose([value])
    elif is_matrix(value):
        rn, cn = rows(value), cols(value)
        return [[value[r][c] for r in range(rn)] for c in range(cn)]


def dot(x1, x2):
    d1, d2 = depth(x1), depth(x2)
    if d1 == d2 == 0:
        if all_(is_function, x1, x2):
            return x1.compose(x2)
        else:
            return mul_(x1, x2)
    elif d2 == 0:
        return tuple(dot(a1, x2) for a1 in x1)
    elif d1 == 0:
        return tuple(dot(x1, a2) for a2 in x2)
    elif max(d1, d2) == 1:
        if len(x1) == len(x2):
            return sum(map(mul, x1, x2))
        else:
            raise ValueError(f'dimension mismatch for dot operation')
    elif max(d1, d2) == 2:
        if d1 == 1:
            return tuple(dot([x1], x2))
        elif d2 == 1:
            return tuple(dot(x1, transpose(x2)))
        else:
            return tuple(tuple(dot(r, c) for c in transpose(x2)) for r in x1)
    else:
        raise TypeError('invalid dimension')


def compose(*funcs):
    def compose2(f, g):
        return lambda *args: f(g(*args))
    return reduce(compose2, funcs)


def tomap(f):
    def _f(lst): return tuple(f(x) for x in lst)
    return _f


def first(cond, lst):
    for i, x in enumerate(lst):
        if cond(x): return i
    return -1


def findall(cond, lst):
    if is_function(cond):
        return [i for i, x in enumerate(lst) if cond(x)]
    else:
        return [i for i, x in enumerate(lst) if equal(x, cond)]


def range_(x, y):
    if isinstance(x, Range):
        return Range(x.first, y, x.last)
    else:
        return Range(x, y)

