### Builtin Functions
from operator import *
from math import *
from functools import reduce

builtins = {'sin':sin, 'cos':cos, 'tan':tan, 'asin':asin, 'acos':acos, 
'atan':atan, 'abs':abs, 'sqrt':sqrt, 'floor':floor, 'ceil':ceil, 'log':log,
'E':e, 'Pi':pi, 'range':range, 'max':max, 'min':min, 'reduce':reduce,
'binom':lambda n, m: factorial(n) / factorial(m),
'sum': lambda f, l: reduce(add, (f(x) for x in l)),
'prod':lambda f, l: reduce(mul, (f(x) for x in l))}