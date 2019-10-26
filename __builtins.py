from operator import *
from math import *
from functools import reduce
from  __classes import Op


def booltobin(bool_op):
    def apply(a, b):
        return 1 if bool_op(a, b) else 0
    return apply

def get_items(lst, indices):
    def get_from_index(lst, index):
        if not hasattr(lst, '__getitem__'):
            raise SyntaxError('{} is not subscriptable'.format(lst))
        if hasattr(index, '__iter__'):
            return (lst[i] for i in index)
        return lst[index]
    if not hasattr(indices, '__iter__') or isinstance(indices, range):
        return get_from_index(lst, indices)
    if indices == []: return lst
    items = get_from_index(lst, indices[0])
    if hasattr(indices[0], '__iter__'):
        return (get_items(item, indices[1:]) for item in items)
    else:
        return get_items(items, indices[1:])


def toList(lst):
    def ifIter_toList(obj):
        if hasattr(obj, '__iter__'):
            return [ifIter_toList(it) for it in obj]
        return obj
    if not hasattr(lst, '__iter__'):
        raise ValueError('{} is not iterable!'.format(lst))
    return ifIter_toList(lst)


def reconstruct(op_dict, type):
    for op in op_dict:
        info = op_dict[op]
        op_dict[op] = Op(type, info[0], info[1])


binary_ops = {'+':(add, 6), '-':(sub, 6), '*':(mul, 8), '/':(truediv, 8),
'//':(floordiv, 8), '^':(pow, 14), '%':(mod, 8), '&':(and_, 4), '|':(or_, 2),
'=':(booltobin(eq), 0), '!=':(booltobin(ne), 0), '<':(booltobin(lt), 0),
'>':(booltobin(gt), 0), '<=':(booltobin(le), 0), '>=':(booltobin(ge), 0),
'in':(lambda x, l: 1 if x in l else 0, -2), 'xor': (booltobin(xor), 3),
'@':(get_items, 16), '++': (concat, 10), '~':(lambda a, b: range(a, b+1), 6),
'and':(booltobin(lambda a, b: a and b), -5),
'or': (booltobin(lambda a, b: a or b), -6)}

reconstruct(binary_ops, 'bin')

unitary_ops = {'-':(neg, 10), 'not':(lambda n: 1 if n == 0 else 1, -4),
'!': (inv, 12)}

reconstruct(unitary_ops, 'uni')

op_list = list(binary_ops) + list(unitary_ops)

special_words = set(['ans', 'if', 'else', 'cases', 'for', 'in'])

builtins = {'sin':sin, 'cos':cos, 'tan':tan, 'asin':asin, 'acos':acos,
'atan':atan, 'abs':abs, 'sqrt':sqrt, 'floor':floor, 'ceil':ceil, 'log':log,
'E':e, 'PI':pi, 'I':1j, 'range':range, 'max':max, 'min':min, 'reduce':reduce,
'list':toList, 'binom':lambda n, m: factorial(n) / factorial(m), 'log10':log10,
'log2':log2, 'exp':exp,
'sum': lambda l: reduce(add, l), 'prod':lambda l: reduce(mul, l)}
