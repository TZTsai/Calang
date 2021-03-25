from funcs import *


def construct_ops(op_dict, type):
    for op in op_dict:
        fun, pri = op_dict[op]
        op_dict[op] = Op(type, op, fun, pri)
        

binary_ops = {
    '+': (add, 6), '-': (sub, 6), '×': (mul, 8), '÷': (div, 8), '^': (pow, 18),
    '//': (floordiv, 8), './': (truediv, 8), '%': (mod, 8), '/%': (divmod, 8), '⋅': (dot, 10),
    '&': (and_, 8), '|': (or_, 7), '⊗': (xor, 3), '∧': (land, 3), '∨': (lor, 2),
    '==': (eq, 0), '~=': (neq, 0), '<': (lt, 0), '>': (gt, 0), '<=': (le, 0), '>=': (ge, 0), 
    'in': (in_, -2), ':': (range_, 4), '.': (index, 16), '<-': (substitute, 22),
    '(get)': (get_attr, 25), '(app)': (apply, 30)
}

unary_l_ops = {
    '-': (neg, 10), 'not': (not_, -4), '¬': (not_, 9), '~': (inv, 10), '∠': (ang, 4)
}

unary_r_ops = {
    '!': (factorial, 22), '..': (unpack, 11), '°': (deg, 24), "ᵀ": (transpose, 15)
}

operators = {'BOP': binary_ops, 'LOP': unary_l_ops, 'ROP': unary_r_ops}

for op_type, op_dict in operators.items():
    construct_ops(op_dict, op_type)

binary_ops['(app)'].broadcast = False

shortcircuit_ops = operators['SOP'] = ['or', 'if', 'and']

op_symbols = set.union(*map(set, operators.values()))

amb_ops = {op for op in op_symbols
           if sum(op in ops for ops in operators.values()) > 1}


builtins = {
    # constants
    'euler': E, 'ℯ': E, 'pi': pi, 'π': pi, 'φ': S.GoldenRatio, 'im': 1j, 'ⅈ': 1j, '∞': oo,
    # types
    'Number': Number, 'Integer': Integral, 'Rational': Rational, 
    'Real': Real, 'Complex': Complex, 'Fraction': Fraction,
    'Symbol': Symbol, 'Matrix': Matrix, 'Array': Array, 'List': tuple, 
    'String': str, 'Env': Env, 'Range': Range, 'Enum': Enum,
    # common functions
    'abs': abs, 'sqrt': sqrt, 'floor': floor, 'ceil': ceiling, 
    # list functions
    'list': tuple, 'len': len, 'max': max, 'min': min, 'all': all_, 'any': any_,
    'enum': enumerate, 'zip': zip, 'sort': sorted,
    'sum': sum_, 'prod': prod, 'Σ': summation, 'Π': product,
    'find': findall, 'next': next,
    # array functions
    'matrix': Matrix, 'shape': shape, 'depth': depth, 'transp': transpose, 'flatten': flatten,
    # real valued functions
    'exp': exp, 'log': log, 'ln': log, 'lg': log10, 'log2': log2,
    # higher order functions
    'compose': compose, 'reduce': reduce, 'filter': filter, 'map': map,
    # triangular functions
    'sin': sin, 'cos': cos, 'tan': tan, 'asin': asin, 'acos': acos, 'atan': atan, 
    'sinh': sinh, 'cosh': cosh, 'tanh': tanh,
    # symbolic functions
    'solve': solve, 'lim': limit, 'diff': diff, 'int': integrate, 'subs': substitute,
    'expand': expand, 'factor': factor, 'simplify': simplify,
    # integral number functions
    'gcd': gcd, 'factorial': factorial, 'binomial': binomial, 'factors': factorint
}

synonym_builtins = {
    '∃': 'any',
    '∀': 'all',
    'ℤ': 'Integer',
    'ℚ': 'Rational',
    'ℝ': 'Real',
    'ℂ': 'Complex',
}

for name, val in builtins.items():
    if callable(val) and not isinstance(val, type):
        builtins[name] = Builtin(val, name)

for name1, name2 in synonym_builtins.items():
    builtins[name1] = builtins[name2]
