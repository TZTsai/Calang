from functools import wraps
from .debug import log
import sys


def memo(f):  # a decorator to improve performance
    "Use a table to store computed results of a function."
    table = {}
    @wraps(f)
    def _f(*args):
        # print(table)
        try:
            return table[args]
        except KeyError:
            result = f(*args)
            table[args] = result
            return result
        except TypeError:
            return f(*args)
    return _f


def trace(f):  # a decorator for debugging
    "Print info before and after the call of a function."
    @wraps(f)
    def _f(*args):
        signature = f"{f.__name__}({', '.join(map(repr, args))}):"
        log(f' ---> {signature}')
        log.depth += 1
        try: result = f(*args)
        finally: log.depth -= 1
        log(f' <--- {signature} === {result}')
        return result
    return _f


def disabled(f): return f  # used to disable a decorator