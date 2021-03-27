import sys
import re
from .debug import log, logfile, freeze
from functools import wraps


def split(predicate, seq):
    true, false = [], []
    for it in seq:
        (true if predicate(it) else false).append(it)
    return true, false

    
# functions dealing with tags
def is_name(s):
    return type(s) is str and s

tag_pattern = re.compile('[A-Z_:]+')
def is_tag(s):
    return is_name(s) and tag_pattern.match(s)

def is_tree(t):
    return isinstance(t, list) and t and is_tag(t[0])

def tree_tag(t):
    return t[0] if is_tree(t) else None


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
            if retry:
                args = freeze(args)
                return _f(*args, retry=0)
            else:
                return f(*args)
    return _f

