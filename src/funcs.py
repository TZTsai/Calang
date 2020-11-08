from operator import and_ as b_and, or_ as b_or, concat
from functools import reduce, wraps
from numbers import Number, Rational
from fractions import Fraction
from sympy import Expr, Integer, Float, Matrix, Symbol, factor, simplify, factorial
from objects import Range, Map, Attr, Env, Op, Function, Builtin, OperationError
import config


def apply(func, val):
    "Apply $func on $val with pre-processing and post-processing."
    
    def numfy(val):
        "convert a number into python number type"
        if any(isinstance(val, c) for c in
               (int, float, complex, Fraction)):
            if isinstance(val, complex):
                return val.real if eq_(val.imag, 0) else val
            else:
                return val
        elif isinstance(val, Integer):
            return int(val)
        elif isinstance(val, Float):
            return float(val)
        else:
            val = complex(val)
            return val.real if eq_(val.imag, 0) else val

    def standardize(val):
        "standardize the result"
        if type(val) is bool:
            return 1 if val else 0
        elif type(val) is list:
            return tuple(standardize(a) for a in val)
        elif type(val) is dict:
            return Env(binds=val)
        else:
            try: return numfy(val)
            except (ValueError, TypeError):
                if isinstance(val, Expr):
                    return factor(simplify(val))
                else: return val
                
    def convert(arg):
        "convert input value"
        if type(arg) is tuple:
            return tuple(map(convert, arg))
        elif isinstance(arg, Env) and hasattr(arg, 'val'):
            return arg.val
        # elif isinstance(arg, str) and config.symbolic:
        #     return Symbol(arg)
        else:
            return arg
        
    val = convert(val)
    result = func(val)
    return standardize(result)


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
    '''
    >>> is_matrix([[1,2],[3,4]])
    True
    >>> is_matrix([[1,2,3],[1,2]])
    False
    >>> is_matrix([[1,[2]],[3,4]])
    False
    >>> is_matrix([1])
    False
    '''
    if isinstance(value, Matrix): 
        return True
    else:
        return (depth(value) == depth(value, min) == 2 and
                same(map(len, value)) and len(value[0]) > 0)


def is_function(value):
    '''
    >>> is_function(abs)
    True
    >>> is_function(lambda: 1)
    True
    '''
    return callable(value)


def is_env(value):
    return isinstance(value, Env)


def all_(lst, test=None):
    '''
    >>> all_(2, 4, 6, test=lambda x: x%2==0)
    True
    >>> all_()
    True
    >>> all_(1, 0, 1)
    False
    >>> all_(1, 1)
    True
    '''
    if test: return all(map(test, lst))
    else: return all(lst)


def any_(lst, test=None):
    if test: return any(map(test, lst))
    else: return any(lst)


def same(lst):
    '''
    >>> same(1, 1.0, 2/2)
    True
    >>> same()
    True
    >>> same(*map(len, [[1,2],[3,4]]))
    True
    >>> same(1, 2, 1)
    False
    '''
    try: x = lst[0]
    except TypeError:
        return same(tuple(lst))
    except IndexError:
        return True
    return all(eq_(x, y) for y in lst[1:])


def add_(x, y):
    if is_list(x) or is_list(y):
        raise TypeError
    return x + y

def sub_(x, y):
    return x - y

def mul_(x, y):
    return x * y

def div_(x, y):
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
    if not (is_list(x1) or is_list(x2)):
        if is_function(x1) and is_function(x2):
            return compose(x1, x2)
        else:
            return mul_(x1, x2)
    d1, d2 = depth(x1), depth(x2)
    if 0 in [d1, d2]:
        raise TypeError  # for broadcast
    if d1 == d2 == 1:
        if len(x1) != len(x2):
            raise ValueError('dim mismatch for dot product')
        return sum(map(mul_, x1, x2))
    elif d1 == 1:
        return dot([x1], x2)
    elif d2 == 1:
        return dot(x1, transpose(x2))
    else:
        return tuple(tuple(dot(r, c) for c in transpose(x2)) for r in x1)

def pow_(x, y):
    if isinstance(y, int):
        return reduce(dot, [x] * y, 1)
    else:
        return x ** y



def and_(x, y):
    if all_([x, y], is_list):
        return [i for i in x if i in y]
    else:
        return b_and(x, y)

def or_(x, y):
    if any_([x, y], is_list):
        dx, dy = depth(x), depth(y)
        if abs(dx - dy) <= 1:
            if max(dx, dy) == 2 and len(x) == len(y):  # matrix augmentation
                return tuple(or_(xi, yi) for xi, yi in zip(x, y))
            if dx < dy: x = x,
            if dx > dy: y = y,
            return concat(x, y)
        else:
            raise TypeError('dimension mismatch')
    elif all_([x, y], is_env):
        assert x.parent is y.parent, \
            'two objects do not have the same parent'
        e = Env(parent=x.parent, binds=x)
        e.update(y)
    else:
        return b_or(x, y)

def not_(x):
    return 0 if x else 1

def eq_(x, y):
    if is_list(x):
        if not is_list(y) or len(x) != len(y):
            return False
        else:
            return all(map(eq_, x, y))
    if is_number(x):
        if not is_number(y):
            return False
        else:
            return abs(x - y) <= config.tolerance
    return x == y

def ne_(x, y):
    return not eq_(x, y)


def fact2(x):  # returns the double factorial of x
    '''
    >>> [fact2(4), fact2(5)]
    [8, 15]
    '''
    if not isinstance(x, int) or x < 0:
        raise ValueError('invalid number for "!!"')
    result = 1
    for i in range(x, 0, -2): result *= i
    return result


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
    def wrapped(args):
        depths = [depth(a) for a in args]
        if same(depths):
            return f(args)
        else:
            dmax = max(depths)
            i = depths.index(dmax)
            args_list = [[*args[:i], a, *args[i+1:]] for a in args[i]]
            return tuple(f(args) for args in args_list)
    return wrapped

Function.broadcast = broadcast


def adjoin(x1, x2):
    '''
    >>> adjoin(abs, [-3])
    3
    >>> adjoin(3, 4)
    12
    >>> adjoin(abs, Attr('__class__'))
    <class 'builtin_function_or_method'>
    '''
    if isinstance(x2, Attr):
        return x2.getFrom(x1)
    elif is_list(x1) and is_list(x2):
        return subscript(x1, x2)
    elif is_function(x1):
        return apply(x1, x2)
    else:
        raise OperationError('invalid types for adjoin')


def compose(*funcs):
    def compose2(f, g):
        def h(*args): return f(g(*args))
        h.__name__ = f'<composed: {f.__name__} and {g.__name__}>'
        return h
    return reduce(compose2, funcs)


def unpack(lst):
    return ['(unpack)', lst]


def subscript(lst, subs):
    if not subs: return lst
    assert depth(subs) == 1
    id0 = subs[0]
    items = lst[id0]
    if type(id0) is slice:
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
    if is_function(cond):
        return [i for i, x in enumerate(lst) if cond(x)]
    else:
        return [i for i, x in enumerate(lst) if eq_(x, cond)]


def range_(x, y):
    if isinstance(x, Range):
        return Range(x.first, y, x.last)
    else:
        return Range(x, y)

def range_inc(x: Range, y):
    first, step = x.first, x.last
    return Range(first, y, first+step)

def range_dec(x: Range, y):
    first, step = x.first, x.last
    return Range(first, y, first-step)


def substitute(exp, *bindings):
    if hasattr(exp, 'subs'):
        return exp.subs(bindings)
    if is_iter(exp):
        return tuple(substitute(x, *bindings) for x in exp)
    return exp



if __name__ == "__main__":
    import doctest
    doctest.testmod()
