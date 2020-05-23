from operator import add, sub, mul, floordiv, mod, ne, neg, lt, gt, le, ge, \
    xor, pow as pow_, and_, or_
from functools import reduce
from numbers import Number, Rational
from fractions import Fraction
from math import e, pi, inf, log10
from sympy import Symbol, solve, limit, integrate, diff, simplify, Integer, Float, Matrix, Expr, \
    sqrt, log, exp, gcd, factorial, floor, sin, cos, tan, asin, acos, atan, cosh, sinh, tanh
from __classes import Op, function, Env, config
from myutils import interact


def is_number(value):
    return isinstance(value, Number)


def is_symbol(value):
    return type(value) == Symbol


def is_iterable(value):
    return hasattr(value, "__iter__")


def is_list(value):
    return isinstance(value, tuple)


def is_matrix(x):
    return list_depth(x) == 2 and is_iterable(x[0]) and \
        all(is_iterable(it) and len(it) == len(x[0]) for it in x[1:])


def is_vector(x):
    return list_depth(x) == 1


def is_function(value):
    return callable(value)


def equal(x, y):
    if is_number(x) and is_number(y):
        return abs(x - y) <= config.tolerance
    else:
        return x == y


def all_(lst, condition=None):
    if condition:
        return all(map(condition, lst))
    else:
        return all(lst)


def any_(lst, condition=None):
    if condition:
        return any(map(condition, lst))
    else:
        return any(lst)


def smart_div(x, y):
    if all(isinstance(w, Rational) for w in (x, y)):
        return Fraction(x, y)
    return x / y


def substitute(exp, *bindings):
    if is_iterable(exp):
        return tuple(substitute(x, *bindings) for x in exp)
    if hasattr(exp, 'subs'):
        return exp.subs(zip([bindings[i] for i in range(len(bindings)) if i % 2 == 0],
                            [bindings[i] for i in range(len(bindings)) if i % 2 == 1]))
    return exp


# set operation supports
def smart_add(a, b):
    if all_((a, b), lambda x: isinstance(x, set)):
        return or_(a, b)
    return add(a, b)

def smart_mul(a, b):
    if all_((a, b), lambda x: isinstance(x, set)):
        return and_(a, b)
    return mul(a, b)


add_ = function.operator('+', smart_add)
sub_ = function.operator('-', sub)
mul_ = function.operator('*', smart_mul)
div_ = function.operator('/', smart_div)
and_ = function.operator('/\\', and_)
or_ = function.operator('\\/', or_)


def power(x, y):
    if is_list(x):
        return reduce(dot, [x] * y)
    elif isinstance(x, function) and isinstance(y, int):
        f = x
        for _ in range(1, y):
            f = x.compose(f)
        return f
    else:
        return pow_(x, y)


def list_depth(value):
    if not is_iterable(value):
        return 0
    if len(value) == 0:
        return 1
    return 1 + max(map(list_depth, value))


def index(lst, id):
    if not hasattr(lst, '__getitem__'):
        raise SyntaxError('{} is not subscriptable'.format(lst))
    if isinstance(lst, range) or not is_iterable(id):
        return lst[id]
    else:
        return tuple(index(lst, i) for i in id)


def to_list(lst):
    def ifIter_toList(obj):
        if hasattr(obj, '__iter__'):
            return tuple(ifIter_toList(it) for it in obj)
        return obj

    if not hasattr(lst, '__iter__'):
        raise ValueError('{} is not iterable!'.format(lst))
    return ifIter_toList(lst)


def subscript(lst, subs):
    if not subs:
        return lst
    index0 = subs[0]
    items = index(lst, index0)
    if is_iterable(index0) or type(index0) == slice:
        return tuple(subscript(item, subs[1:]) for item in items)
    else:
        return subscript(items, subs[1:])


def list_shape(x):
    if not is_iterable(x):
        return tuple()

    def min_(*args):
        return min(args)
    subshapes = [list_shape(a) for a in x]
    return (len(x),) + tuple(map(min_, *subshapes))


def flatten(l):
    """
    >>> flatten([1,2])
    [1, 2]
    >>> flatten([[1,2,[3]],[4]])
    [1, 2, 3, 4]
    """
    if list_depth(l) <= 1: return l
    fl = []
    for x in l: 
        if not is_iterable(x):
            fl.append(x)
        else:
            fl.extend(flatten(x))
    return fl


def row(mat, k):
    if is_matrix(mat):
        return mat[k]
    else:
        raise TypeError(f'{mat} is not a matrix')


def col(mat, k):
    if is_matrix(mat):
        return subscript(mat, [slice(None), k])


def transpose(value):
    if not is_iterable(value):
        return value
    elif is_vector(value):
        return transpose([value])
    else:
        enum_r, enum_c = map(range, list_shape(value)[:2])
        return [[value[r][c] for r in enum_r] for c in enum_c]


def dot(x1, x2):
    d1, d2 = list_depth(x1), list_depth(x2)
    if d1 == d2 == 0:
        if all_((x1, x2), is_function):
            return x1.compose(x2)
        else:
            return mul_(x1, x2)
    elif d2 == 0:
        return tuple(dot(a1, x2) for a1 in x1)
    elif d1 == 0:
        return tuple(dot(x1, a2) for a2 in x2)
    elif max([d1, d2]) == 1:
        if len(x1) == len(x2):
            return sum(map(mul, x1, x2))
        else:
            raise ValueError(f'dimensions do not match')
    elif max([d1, d2]) == 2:
        if d1 == 1:
            return tuple(dot([x1], x2))
        elif d2 == 1:
            return tuple(dot(x1, transpose(x2)))
        else:
            return tuple(tuple(dot(row(x1, r), col(x2, c))
                               for c in range(len(x2[0]))) for r in range(len(x1)))
    else:
        raise TypeError('invalid arguments')


def compose(*funcs):
    def compose2(f, g):
        return lambda *args: f(g(*args))
    return reduce(compose2, funcs)


def first(cond, lst):
    try:
        return list(map(cond, lst)).index(True)
    except ValueError:
        return len(lst)


def find(cond, lst):
    if is_function(cond):
        return [i for i in range(len(lst)) if cond(lst[i])]
    else:
        return [i for i in range(len(lst)) if equal(lst[i], cond)]


def standardize(name, val):

    def pynumfy(val):
        # convert a number into a python number type
        if any(isinstance(val, c) for c in (int, float, complex, Fraction)):
            return val
        elif isinstance(val, Integer):
            return int(val)
        elif isinstance(val, Float):
            return float(val)
        else:
            return (lambda z: z.real if z.imag == 0 else z)(complex(val))

    def unify_types(x):
        if type(x) is bool:
            return 1 if x else 0
        elif is_iterable(x) and not any_((range, set), lambda c: isinstance(x, c)):
            return tuple(unify_types(a) for a in x)
        else:
            try:
                return pynumfy(x)
            except (ValueError, TypeError):
                return simplify(x) if isinstance(x, Expr) else x

    if is_function(val):
        fun = compose(unify_types, val)
        fun.str = name
        return fun
    return val


def reconstruct(op_dict, type):
    for op in op_dict:
        info = op_dict[op]
        op_dict[op] = Op(type, standardize(op, info[0]), info[1])


binary_ops = {'+': (add_, 6), '-': (sub_, 6), '*': (mul_, 8), '/': (div_, 8), '.': (dot, 7),
              '//': (floordiv, 8), '^': (power, 14), '%': (mod, 8), '=': (equal, 0),
              '!=': (ne, 0), '<': (lt, 0), '>': (gt, 0), '<=': (le, 0),
              '>=': (ge, 0), 'xor': (xor, 3), 'in': (lambda x, y: x in y, -2),
              '@': (index, 16), '~': (lambda a, b: range(a, b + 1), 5),
              'and': (and_, -5), 'or': (or_, -6), '/\\': (and_, 8), '\\/': (or_, 7)}
reconstruct(binary_ops, 'bin')

unitary_l_ops = {'-': (neg, 10), 'not': (lambda n: 1 if n == 0 else 0, -4)}
reconstruct(unitary_l_ops, 'uni_l')

unitary_r_ops = {'!': (factorial, 99), '%': (lambda x: 0.01*x, 99)}
# actually a unitary op on the right will always be immediately carried out
reconstruct(unitary_r_ops, 'uni_r')

op_list = set(binary_ops).union(set(unitary_l_ops)).union(set(unitary_r_ops))

special_words = {'if', 'else', 'in', 'ENV', 'load', 'format', 'when',
                 'import', 'del', 'lambda', 'with'}

builtins = {'add': add_, 'sub': sub_, 'mul': mul_, 'div': div_,
            'sin': sin, 'cos': cos, 'tan': tan, 'asin': asin, 'acos': acos,
            'atan': atan, 'abs': abs, 'sqrt': sqrt, 'floor': floor, 'log': log,
            'E': e, 'PI': pi, 'I': 1j, 'INF': inf, 'range': range, 'max': max, 'min': min, 'gcd': gcd,
            'binom': lambda n, m: factorial(n) / (factorial(m) * factorial(n-m)), 
            'len': len, 'sort': sorted, 'exit': lambda: exit(),
            'exp': exp, 'lg': lambda x: log(x)/log(10), 'ln': log, 'log2': lambda x: log(x)/log(2),
            'empty?': lambda l: 0 if len(l) else 1, 'number?': is_number, 'symbol?': is_symbol,
            'iter?': is_iterable, 'lambda?': is_function, 'matrix?': is_matrix, 'vector?': is_vector,
            'list': to_list, 'sum': lambda l: reduce(add, l), 'product': lambda l: reduce(mul, l),
            'car': lambda l: l[0], 'cdr': lambda l: l[1:], 'cons': lambda a, l: (a,) + l, 'enum': compose(range, len),
            'row': row, 'col': col, 'shape': list_shape, 'depth': list_depth, 'transp': transpose, 'flatten': flatten,
            'all': all_, 'any': any, 'same': lambda l: True if l == [] else all(x == l[0] for x in l[1:]),
            'sinh': sinh, 'cosh': cosh, 'tanh': tanh, 'degrees': lambda x: x / pi * 180,
            'real': lambda z: z.real if type(z) is complex else z, 'imag': lambda z: z.imag if type(z) is complex else 0,
            'conj': lambda z: z.conjugate(), 'angle': lambda z: atan(z.imag / z.real),
            'reduce': reduce, 'filter': filter, 'map': map, 'zip': zip, 'find': find,
            'solve': solve, 'lim': limit, 'diff': diff, 'int': integrate, 'subs': substitute}

for name in builtins:
    val = builtins[name]
    if is_function(val):
        builtins[name] = standardize(name, val)
        builtins[name].str = f'<built-in: {name}>'


if __name__ == "__main__":
    import doctest
    doctest.testmod()
