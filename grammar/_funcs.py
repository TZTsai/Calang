from operator import add, sub, mul, pow as pow_, and_ as b_and, or_ as b_or
from functools import reduce
from numbers import Number, Rational
from fractions import Fraction
from sympy import Matrix, Symbol
from _obj import config, Range, Map
from mydecorators import decorator


def is_number(value):
    return isinstance(value, Number)


def is_symbol(value):
    return isinstance(value, Symbol)


def is_iter(value):
    return hasattr(value, "__iter__")


def is_list(value):
    return isinstance(value, tuple) or isinstance(value, list)


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
        return depth(value) == depth(value, min) == 2 and same(*map(len, value))


def is_function(value):
    return callable(value)


def all_(*lst, test=None):
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


def any_(*lst, test=None):
    if test: return any(map(test, lst))
    else: return any(lst)


def same(*lst):
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


def and_(x, y): return x if not x else y
def or_(x, y): return x if x else y
def not_(x): return 0 if x else 1
def eq_(x, y):
    if is_list(x):
        if not is_list(y) or len(x) != len(y): return False
        return all(map(eq_, x, y))
    if is_number(x):
        if not is_number(y): return False
        return abs(x - y) <= config.tolerance
    return x == y
def ne_(x, y): return not eq_(x, y)


def div(x, y):
    if all(isinstance(w, Rational) for w in (x, y)):
        return Fraction(x, y)
    else:
        return x / y

    
def dbfact(x):  # returns the double factorial of x
    '''
    >>> [dbfact(4), dbfact(5)]
    [8, 15]
    '''
    if not isinstance(x, int) or x < 0:
        raise ValueError('invalid argument for factorial!')
    if x in (0, 1): return 1
    else: return x * dbfact(x-2)


def compose(*funcs):
    def compose2(f, funcs):
        return lambda *args, **kws: f(g(*args, **kws))
    return reduce(compose2, funcs)


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


@decorator
def itemwise(op):
    '''
    >>> iadd([1, 2], [2, 3])
    (3, 5)
    >>> iadd([[1, 2], [2, 3]], [[3, 4], [-2, 0]])
    ((4, 6), (0, 3))
    >>> iadd(3, [3, 4, 5])
    (6, 7, 8)
    '''
    def f(x1, x2):
        d1, d2 = depth(x1), depth(x2)
        if d1 == d2:
            if d1 == 0:
                return op(x1, x2)
            else:
                return tuple(f(a1, a2) for a1, a2 in zip(x1, x2))
        elif d1 > d2:
            return tuple(f(a1, x2) for a1 in x1)
        else:
            return tuple(f(x1, a2) for a2 in x2)
    return f


def adjoin(x1, x2):
    '''
    >>> adjoin(abs, [-3])
    3
    >>> adjoin(3, 4)
    12
    '''
    if isinstance(x1, Map):
        return x1(x2)
    elif is_function(x1):
        try: return x1(*x2)
        except TypeError as err:
            if is_function(x2):
                return None  # TODO compose x1 and x2
            else:
                raise err
    else:
        return imul(x1, x2)

def dot(x1, x2):
    '''
    >>> dot(3, [1,2,3])
    (3, 6, 9)
    >>> dot(abs, [-3])
    3
    >>> dot([1, 2], [2, 5])
    12
    '''
    d1, d2 = depth(x1), depth(x2)
    if d1 == 0 or d2 == 0:
        return adjoin(x1, x2)
    elif d1 == d2 == 1:
        if len(x1) != len(x2):
            raise ValueError('dim mismatch for dot product')
        return sum(map(adjoin, x1, x2))
    elif d1 == 1:
        return tuple(dot([x1], x2))
    elif d2 == 1:
        return tuple(dot(x1, transpose(x2)))
    else:
        return tuple(tuple(dot(r, c) for c in transpose(x2)) for r in x1)


def power(x, y):
    return reduce(dot, [x] * y)


iadd = itemwise(add)
isub = itemwise(sub)
idiv = itemwise(div)
imul = itemwise(mul)
ipow = itemwise(power)
iand = itemwise(b_and)
ior  = itemwise(b_or)


def index(lst, id):
    if not hasattr(lst, '__getitem__'):
        raise SyntaxError(f'{lst} is not subscriptable')
    if not is_iter(id): return lst[id]
    else: return tuple(index(lst, i) for i in id)


def subscript(lst, subs):
    if not subs: return lst
    id0 = subs[0]
    items = index(lst, id0)
    if is_iter(id0) or type(id0) is slice:
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


@decorator
def canmap(f):
    def _f(*lst, depth=1):
        return tuple(map(f, *lst))
    return _f


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


def substitute(exp, *bindings):
    if is_iter(exp):
        return tuple(substitute(x, *bindings) for x in exp)
    if hasattr(exp, 'subs'):
        return exp.subs(bindings)
    return exp



if __name__ == "__main__":
    import doctest
    doctest.testmod()
