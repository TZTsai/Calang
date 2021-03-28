import sys, os
import re
from .debug import logfile, freeze
from functools import wraps, partial
from my_utils.utils import interact, main


def fsplit(predicate, seq, ret_idx=False):
    true, false = [], []
    idx_true = []
    for i, t in enumerate(seq):
        if predicate(t):
            true.append(t)
            idx_true.append(i)
        else:
            false.append(t)
    if ret_idx:
        return true, false, idx_true
    else:
        return true, false

    
def same(lst):
    try:
        it = iter(lst)
        x = next(it)
        return all(x == y for y in it)
    except:
        return True


def depth(value, key=max, _cache=None):
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
    if _cache is None:  # prevent from infinite recursion
        _cache = set()
        
    if not indexable(value):
        return 0
    
    if id(value) in _cache:
        return float('inf')
    else:
        _cache.add(id(value))
    
    return 1 + key([depth(v, key, _cache) for v in value], default=0)


def deepmap(f, args, kwds=None):
    def _f(*args, **kwds):
        depths = [depth(l) for l in args]
        if not same(depths):
            i = depths.index(max(depths))
            args = [[*args[:i], a, *args[i+1:]] for a in args[i]]
            return tuple(_f(*a, **kwds) for a in args)
        elif not depths or depths[0] == 0:
            return f(*args, **kwds)
        else:
            return tuple(map(partial(f, **kwds), *args))
    if not kwds: kwds = {}
    return _f(*args, **kwds)


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


def iterable(value):
    return hasattr(value, '__iter__')

def indexable(value):
    try:
        value[:0]
        return True
    except:
        return False

def haslen(value):
    return hasattr(value, '__len__')


# decorators

def memo(f):
    "Use a table to store computed results of a function."
    table = {}
    @wraps(f)
    def _f(*args, retry=1):
        try:
            return table[args]
        except KeyError:
            result = f(*args)
            table[args] = result
            return result
        except TypeError:
            # if retry:
            #     args = freeze(args)
            #     return _f(*args, retry=0)
            # else:
            return f(*args)
    return _f
