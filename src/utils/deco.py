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
        signature = format_call(f, args)
        log('%s:' % signature)
        log.indent += 2
        try:
            result = f(*args)
            log.indent -= 2
        except Exception as e:
            log(signature, ' exited due to %s' % (str(e) or 'an exception'))
            log.indent -= 2
            raise
        log(f'{signature} ==> {result}')
        return result
    return _f

def format_call(f, args):
    if f.__name__ == '_func': f, args = args
    return '%s%s' % (repr(f), log.format(args))
    

def disabled(f, *ignore): return f  # used to disable a decorator
