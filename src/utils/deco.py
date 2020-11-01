import sys
from functools import wraps
from .debug import log
import config


def memo(f): 
    "Use a table to store computed results of a function."
    table = {}
    @wraps(f)
    def _f(*args):
        try:
            return table[args]
        except KeyError:
            result = f(*args)
            table[args] = result
            return result
        except TypeError:
            return f(*args)
    return _f


def trace(f):
    "Print info before and after the call of a function."
    @wraps(f)
    def _f(*args):
        signature = trace.signature(f, args)
        log('%s:' % signature)
        log.depth += 1
        try:
            result = f(*args)
            log.depth -= 1
        except:
            log(signature, 'exited due to exception')
            log.depth -= 1
            raise
        log(f'{signature} ==> {result}')
        return result
    return _f

trace.signature = lambda f, args: f'{f}{args}'
    

def disabled(f, *ignore): return f  # used to disable a decorator


if not config.debug: trace = disabled