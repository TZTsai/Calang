from operator import (
    and_ as band, or_ as bor, concat, sub, mul, 
    floordiv, truediv, mod, neg, lt, gt, le, ge, inv, xor
)
from functools import reduce, wraps
from itertools import product as itprod, permutations, combinations
from numbers import *
from fractions import Fraction
from copy import deepcopy
from sympy import (
    S, E, pi, nan, oo,
    Symbol, Array, Matrix, Eq, Integer, Float, Expr,
    floor, ceiling, sqrt, log, exp, gamma,
    factorial, expand, factor, solve, summation, product,
    gcd, factorint, binomial,
    sin, cos, tan, asin, acos, atan, cosh, sinh, tanh,
    limit, integrate, diff, simplify
)
# import symengine  # TODO: this may boost the speed of symbolic calculation
from objects import Range, Map, Attr, Env, Op, Function, Builtin
import inspect
import config


def apply(func, args):

    def convert(arg):
        if type(arg) in (list, tuple):
            return tuple(map(convert, arg))
        elif isinstance(arg, Env) and arg.val is not None:
            return arg.val
        else:
            return arg
        
    args = convert(args)
    result = func(args)
    # if isinstance(func, Map):
    # else:
    #     result = func(*args)
    return convert_type(result)


def convert_type(val):
    "Convert the result to the standard types."

    def proc_num(val):
        "convert a number into python number type"
        if isinstance(val, (int, float, complex, Fraction)):
            if isinstance(val, complex):
                return val.real if eq(val.imag, 0) else val
            else:
                return val
        elif isinstance(val, Integer):
            return int(val)
        elif isinstance(val, Float):
            return float(val)
        else:
            val = complex(val)
            return val.real if eq(val.imag, 0) else val

    if type(val) is bool:
        return 1 if val else 0
    elif type(val) in [list, tuple]:
        return tuple(convert_type(a) for a in val)
        # if likematrix(val): return Matrix(val)
        # else: return val
    elif type(val) is dict:
        return Env(binds=val)
    elif callable(val) and not isinstance(val, Function):
        return Function(val)
    else:
        try:
            return proc_num(val)
        except (ValueError, TypeError):
            if isinstance(val, Expr):
                return factor(simplify(val))
            else:
                return val


def is_number(value):
    return isinstance(value, Number)


def iterable(value):
    try:
        iter(value); return True
    except:
        return False


def indexable(value):
    return hasattr(value, '__getitem__')


def is_list(value):
    return isinstance(value, tuple)


def is_vector(value):
    return depth(value) == 1


def is_array(value):
    return isinstance(value, (Array, Matrix))
            

def is_env(value):
    return isinstance(value, Env)


def likematrix(value):
    return (depth(value, max) == depth(value, min) == 2 and
            same(map(len, value)) and len(value[0]) > 0)


def_template_1 = '''
def {f}_(arg1, arg2=None):
    if arg2 is not None:
        pred, seq = arg1, arg2
        return {f}(map(pred, seq))
    else:
        seq = arg1
        return {f}(seq)
'''

for f in ['all', 'any']:
    exec(def_template_1.format(f=f))


def same(lst):
    try: x = lst[0]
    except TypeError:
        return same(tuple(lst))
    except IndexError:
        return True
    return all(eq(x, y) for y in lst[1:])


def add(x, y):
    if is_list(x) and is_list(y):
        raise TypeError  # avoid concat
    return x + y

def div(x, y):
    if all(isinstance(w, Rational) for w in (x, y)):
        return Fraction(x, y)
    else:
        return x / y

def dot(x1, x2):
    '''
    >>> dot(3, [1,2,3])
    (3, 6, 9)
    >>> dot([1, 2], [2, 5])
    12
    '''
    if callable(x1) and is_list(x2):
        return broadcast(x1)(x2)
    if not (is_list(x1) or is_list(x2)):
        return mul(x1, x2)
    d1, d2 = depth(x1), depth(x2)
    if 0 in [d1, d2]:
        raise TypeError  # for broadcast
    if d1 == d2 == 1:
        if len(x1) != len(x2):
            raise ValueError('dim mismatch for dot product')
        return sum(map(mul, x1, x2))
    elif d1 == 1:
        return dot([x1], x2)
    elif d2 == 1:
        return dot(x1, transpose(x2))
    else:
        return tuple(tuple(dot(r, c) for c in transpose(x2)) for r in x1)

def pow(x, y):
    if isinstance(y, int):
        return reduce(dot, [x] * y, 1)
    else:
        return x ** y
    
def exclaim(x):
    if callable(x):
        args = inspect.signature(x).parameters
        if not args:
            return x()
        else:
            x2 = deepcopy(x)
            x2.broadcast = True
            return x2
    else:
        return factorial(x)

        
def log2(x): return log(x) / log(2)
def log10(x): return log(x) / log(10)
def sum_(*x): return reduce(add, x, 0)
def prod(*x): return reduce(dot, x, 1)
def deg(x): return x / 180 * pi
def ang(z): return atan(z.imag / z.real)

    
def in_(x, y):
    if isinstance(y, type):
        return isinstance(x, y)
    else:
        return x in y

def and_(x, y):
    if all_(is_list, [x, y]):
        return [i for i in x if i in y]
    else:
        return band(x, y)

def or_(x, y):
    if any_(is_list, [x, y]):
        dx, dy = depth(x), depth(y)
        if abs(dx - dy) <= 1:
            if max(dx, dy) == 2 and len(x) == len(y):  # matrix augmentation
                return tuple(or_(xi, yi) for xi, yi in zip(x, y))
            if dx < dy: x = (x,)
            if dx > dy: y = (y,)
            return concat(x, y)
        else:
            raise TypeError('dimension mismatch')
    elif all_(is_env, [x, y]):
        assert x.parent is y.parent, \
            'two objects do not have the same parent'
        e = Env(parent=x.parent)
        e.update(x); e.update(y)
        return e
    else:
        return bor(x, y)

def land(x, y):
    return 1 if x and y else 0

def lor(x, y):
    return 1 if x or y else 0

def not_(x):
    return 0 if x else 1

def eq(x, y):
    return Eq(x, y)

def neq(x, y):
    return not eq(x, y)


def depth(value, key=max):
    '''
    >>> depth([1])
    1
    >>> depth(abs)
    0
    >>> depth(-9)
    0
    >>> depth([1, [2]])
    2
    >>> depth([1, [2]], min)
    1
    >>> depth([1, [2, [3]]])
    3
    '''
    if not is_list(value): return 0
    if len(value) == 0: return 1
    return 1 + key(map(depth, value))


def broadcast(f):
    @wraps(f)
    def wrapped(*args):
        depths = [depth(l) for l in args]
        if not same(depths):
            i = depths.index(max(depths))
            args = [[*args[:i], a, *args[i+1:]] for a in args[i]]
        return tuple(f(*a) for a in args)
    return wrapped

Function.broadcast = broadcast


def compose(*funcs):
    def compose2(f, g):
        def h(*args): return f(g(*args))
        h.__name__ = f'<composed: {f.__name__} ⋅ {g.__name__}>'
        return h
    return reduce(compose2, funcs)


def unpack(lst):
    return ['UNPACK', lst]


def index(lst, idx):
    def ind(lst, i):
        if type(i) is int:
            if i == 0:
                raise IndexError('zero index')
            elif i > 0:
                return lst[i-1]
            else:
                return lst[i]
        else:
            return lst[i]
    
    try:
        id0 = idx[0]
    except TypeError:
        return ind(lst, idx)
    except IndexError:
        return lst
    
    if isinstance(id0, Range):
        for attr in ['first', 'last']:
            if (i := getattr(id0, attr)) < 0:
                setattr(id0, attr, len(lst) + i + 1)
        items = [ind(lst, i) for i in id0]
        return tuple(index(item, idx[1:]) for item in items)
    else:
        items = ind(lst, id0)
        return index(items, idx[1:])
    
def get_attr(obj, attr: Attr):
    if isinstance(obj, Env):
        return obj[attr.name]
    else:
        return getattr(obj, attr.name)
    

def shape(x):
    if not iterable(x): return ()
    subshapes = [shape(a) for a in x]
    return (len(x), *map(min, *subshapes))


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
        if not iterable(x): fl.append(x)
        else: fl.extend(flatten(x))
    return fl


def transpose(value):
    d = depth(value, min)
    if d == 0:
        return value
    elif d == 1:
        return transpose([value])
    else:
        rn, cn = rows(value), cols(value)
        return [[value[r][c] for r in range(rn)] for c in range(cn)]


# def canmap(f):
#     @wraps(f)
#     def _f(*lst, depth=1):
#         return tuple(map(f, *lst))
#     return _f


def first(cond, lst):
    for i, x in enumerate(lst):
        if cond(x): return i
    return -1


def findall(cond, lst):
    if callable(cond):
        return [i for i, x in enumerate(lst) if cond(x)]
    else:
        return [i for i, x in enumerate(lst) if eq(x, cond)]


def range_(x, y):
    if isinstance(x, Range):
        return Range(x.first, x.last, y)
    else:
        return Range(x, y)


def substitute(exp, bindings):
    if hasattr(exp, 'subs'):
        return exp.subs(bindings)
    if iterable(exp):
        return tuple(substitute(x, *bindings) for x in exp)
    return exp



if __name__ == "__main__":
    import doctest
    doctest.testmod()
