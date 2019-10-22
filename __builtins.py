from operator import *
from math import *
from functools import reduce


def nVal(bool_op):
    def apply(a, b):
        return 1 if bool_op(a, b) else 0
    return apply

def get_items(lst, indices, in_rec=False):
    def get_from_indexList(lst, indices):
        if indices == []: return lst
        items = get_items(lst, indices[0], True)
        if hasattr(indices[0], '__iter__'):
            return (get_from_indexList(item, indices[1:]) for item in items)
        else:
            return get_from_indexList(items, indices[1:])
    if not hasattr(lst, '__getitem__'):
        raise SyntaxError('{} is not subscriptable'.format(lst))
    if not in_rec and isinstance(indices, list):
        get_from_indexList(lst, indices)
    if hasattr(indices, '__iter__'):
        return (lst[i] for i in indices)
    else:
        return lst[indices]


def toList(lst):
    def ifIter_toList(obj):
        if hasattr(obj, '__iter__'):
            return [ifIter_toList(it) for it in obj]
        return obj
    if not hasattr(lst, '__iter__'):
        raise ValueError('{} is not iterable!'.format(lst))
    return ifIter_toList(lst)


binary_ops = {'+':(add, 1), '-':(sub, 1), '*':(mul, 2), '/':(truediv, 2),
'//':(floordiv, 2), '^':(pow, 3), '%':(mod, 2), '&':(and_, -1), '|':(or_, -2),
'=':(nVal(eq), 0), '!=':(nVal(ne), 0), '<':(nVal(lt), 0), '>':(nVal(gt), 0),
'<=':(nVal(le), 0), '>=':(nVal(ge), 0), 'IN':(nVal(lambda e, l: e in l), 0),
'@':(get_items, 5), '~':(lambda a, b: range(a, b+1), 6)}
unitary_ops = {'-':(neg, 4), '!':(lambda n: 0 if n == 0 else 1, 4)}

op_list = list(binary_ops) + list(unitary_ops)

special_words = set(['ans', 'if', 'else', 'cases', 'for', 'in'])

builtins = {'sin':sin, 'cos':cos, 'tan':tan, 'asin':asin, 'acos':acos, 
'atan':atan, 'abs':abs, 'sqrt':sqrt, 'floor':floor, 'ceil':ceil, 'log':log,
'E':e, 'Pi':pi, 'range':range, 'max':max, 'min':min, 'reduce':reduce,
'list':toList, 'binom':lambda n, m: factorial(n) / factorial(m),
'sum': lambda f, l: reduce(add, (f(x) for x in l)),
'prod':lambda f, l: reduce(mul, (f(x) for x in l))}
