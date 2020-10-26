from functools import wraps


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
    indent = '  '
    trace.level = 0
    @wraps(f)
    def _f(*args):
        signature = f"{f.__name__}({', '.join(map(repr, args))})"
        print(indent * trace.level + f'---> {signature}')
        trace.level += 1
        try: result = f(*args)
        finally: trace.level -= 1
        print(indent * trace.level + f'<--- {signature} === {result}')
        return result
    return _f