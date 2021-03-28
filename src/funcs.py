from operator import *
from numbers import *
import inspect
from functools import reduce, wraps
from itertools import product as itprod, permutations, combinations
from fractions import Fraction
from copy import deepcopy
import numpy as np
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

from objects import *
from utils.funcs import *
import config


class IsInstance:
    """
    >>> Is = IsInstance()
    >>> Is.list([1, 2])
    True
    >>> Is(int, float)(2)
    True
    >>> Is(int, float)(1, 1.0)
    True
    >>> Is(int, float)(1, 'b')
    False
    >>> Is.re.error
    """
    
    @staticmethod
    def q(val, type):
        if isinstance(val, Env) and val.val is not None:
            val = val.val
        return isinstance(val, type)

    def __init__(self, ns=None):
        if ns is None:
            self.ns = globals()
        else:
            self.ns = ns
            
    def __getattr__(self, type):
        ns = super().__getattribute__('ns')
        type = eval(type, ns)
        if hasattr(type, '__package__'):
            return IsInstance(type.__dict__)
        else:
            return lambda *args: all(IsInstance.q(arg, type)
                                     for arg in args)

    def __call__(self, *types):
        return lambda *args: all(IsInstance.q(arg, types)
                                 for arg in args)

Is = IsInstance()

is_array = Is(Array, Matrix)
is_matrix = Is.Matrix
is_attr = Is.Attr
is_number = Is.Number
is_list = Is.tuple

def is_env(val):  # special case
    return isinstance(val, Env)


def call(fn, val):
    return fn(val)


def convert_input(arg):
    if Is(list, tuple)(arg):
        return tuple(map(convert_input, arg))
    elif Is.Env(arg) and arg.val is not None:
        return arg.val
    elif Is.dict(arg):
        return {k: convert_input(v) for k, v in arg.items()}
    else:
        return arg
    

def convert_output(val):
    "Convert the result to the standard types."
    
    def convert_num(val):
        "convert a number into python number type"
        if Is(int, float, complex, Fraction)(val):
            if Is.complex(val):
                return val.real if val.imag == 0 else val
            else:
                return val
        elif Is.Integer(val):
            return int(val)
        elif Is.Float(val):
            return float(val)
        else:
            return convert_num(complex(val))

    if is_tree(val):
        return val
    elif type(val) is bool:
        return 1 if val else 0
    elif type(val) in [list, tuple]:
        return tuple(convert_output(a) for a in val)
    elif Is.dict(val):
        return Env(binds=val)
    elif callable(val) and not Is.Function(val):
        return Function(val)
    else:
        try: val = simplify(val)
        except: pass
        try: return convert_num(val)
        except: return val
        

Function.proc_in = convert_input
Function.proc_out = convert_output


def likematrix(value):
    if isinstance(value, Matrix): return True
    return (depth(value, max) == depth(value, min) == 2 and
            same(map(len, value)) and len(value[0]) > 0)


def add(x, y):
    if is_list(x) and is_list(y):
        raise TypeError  # avoid concat
    return x + y

def div(x, y):
    if all(isinstance(w, Rational) for w in (x, y)):
        return Fraction(x, y)
    else:
        return x / y
    
def pow(x, y):
    if isinstance(y, int) and y > 0:
        return reduce(dot, [x] * y)
    else:
        return x ** y
    
def in_(x, y):
    if isinstance(y, type):
        return isinstance(x, y)
    else:
        return x in y

def and_(x, y):
    """
    >>> and_([1, 2], [2, 3])
    [2]
    >>> and_(lambda x: x%2, [1, 2, 3])
    [1, 3]
    >>> and_((x*2 for x in range(4)), lambda x: )
    >>> and_(0b1011, 0b1101)
    9
    """
    if all_(iterable, [x, y]):
        if indexable(x):
            return [i for i in y if i in x]
        elif indexable(y):
            return [i for i in x if i in y]
        else:
            return (i for i in x if i in y)
    elif any_(callable, [x, y]):
        if not callable(x):
            x, y = y, x
        if not iterable(y):
            raise TypeError("invalid types for operator '&'")
        g = (i for i in y if x(i))
        return tuple(g) if indexable(y) else g
    elif isinstance(x, Integral) and isinstance(y, Integral):
        return band(x, y)
    else:
        raise TypeError("invalid types for operator '&'")

def or_(x, y):
    if all_(is_env, [x, y]):
        assert x.parent is y.parent, \
            "operator '|' applied to Envs having different parents"
        e = Env(parent=x.parent, binds=x)
        e.update(y)
        return e
    elif any_(indexable, [x, y]):
        dx, dy = depth(x), depth(y)
        if abs(dx - dy) <= 1:
            # if max(dx, dy) == 2 and len(x) == len(y):  # matrix augmentation
            #     return tuple(or_(xi, yi) for xi, yi in zip(x, y))
            if dx < dy: x = [x]
            if dx > dy: y = [y]
            return concat([x, y])
        else:
            raise TypeError('dimension mismatch')
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
    
def empty(x, y):
    raise Exception  # should not be called
    
def exclaim(x):
    if callable(x):
        args = inspect.signature(x).parameters
        if not args:
            return x()
        else:
            return broadcast(x)
    else:
        return factorial(x)

def log2(x): return log(x, 2)
def log10(x): return log(x, 10)
def sum_(*x): return reduce(add, x, 0)
def prod(*x): return reduce(dot, x, 1)
def deg(x): return x / 180 * pi
def polar(r, t): return complex(r*cos(t), r*sin(t))


class FromNumpy:
    
    def __init__(self, module=np):
        self.m = module
    
    @staticmethod
    def convert(f):
        @wraps(f)
        def wrapped(*args, **kwds):
            ret = f(*args, **kwds)
            if any_(Is.np.ndarray, args):
                return ret
            elif isinstance(ret, np.ndarray):
                return ret.tolist()
            else:
                return ret
        return wrapped
    
    def __getattr__(self, name):
        if name == 'random':
            return FromNumpy(np.random)
        return FromNumpy.convert(getattr(self.m, name))
    
# def extend(f):
#     def deco(g):
#         @wraps(g)
#         def extended(*args, **kwds):
#             it = g(*args, **kwds)
#             args, kwds = next(it)
#             try:
#                 next(it)
#             except StopIteration as e:
#                 return e.value
#         return extended
#     return deco

from_np = FromNumpy()

_dot = from_np.dot
transpose = from_np.transpose
outer = from_np.outer
ones = from_np.ones
zeros = from_np.zeros
diag = from_np.diag
rand = from_np.random.rand
reshape = from_np.reshape
concat = from_np.hstack


def dot(x1, x2):
    if all_(callable, [x1, x2]):
        return compose(x1, x2)
    else:
        return _dot(x1, x2)


def broadcast(f):
    @wraps(f)
    def wrapped(*args, **kwds):
        bc = np.broadcast(*args)
        ret = np.empty(bc.shape)
        ret.flat = [f(*args) for args in bc]
        return ret
    wrapped.__name__ = '<broadcast: %s>' % repr(f)
    return wrapped

Function.broadcast = broadcast


def compose(f, g):
    def h(*args, **kwds):
        val = apply(g, args, kwds)
        return apply(f, val)
    h.__name__ = f'<compose: {repr(f)} ⋅ {repr(g)}>'
    return h


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
        items = [ind(lst, k) for k in id0]
        return tuple(index(item, idx[1:]) for item in items)
    else:
        items = ind(lst, id0)
        return index(items, idx[1:])
    
def get_attr(obj, attr):
    if isinstance(attr, Attr):
        attr = attr.name
    else:
        raise TypeError
    if isinstance(obj, Env):
        return obj[attr]
    else:
        return getattr(obj, attr)
    

def shape(x):
    if not indexable(x): return ()
    subshapes = [shape(a) for a in x]
    return (len(x), *map(min, *subshapes))


def flatten(l):
    """
    >>> flatten([1,2])
    [1, 2]
    >>> flatten([[1,2,[3]],[4]])
    [1, 2, 3, 4]
    """
    if not iterable(l):
        return l
    fl = []
    for x in l:
        if not iterable(x): fl.append(x)
        else: fl.extend(flatten(x))
    return fl


# def transpose(value):
#     d = depth(value, min)
#     if d == 0:
#         return value
#     elif d == 1:
#         return transpose([value])
#     else:
#         rn, cn = rows(value), cols(value)
#         return [[value[r][c] for r in range(rn)] for c in range(cn)]


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
        return tuple(substitute(x, bindings) for x in exp)
    return exp



if __name__ == "__main__":
    import doctest
    doctest.testmod()
