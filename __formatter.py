from __builtins import Rational, Fraction, Matrix, is_number, is_list, \
    is_matrix, floor, log10, inf
from sympy import latex
from types import FunctionType
from re import sub as translate
from utils.greek import gr_to_tex

def format(val, config, indent=0):
    if config.latex:
        s = latex(Matrix(val) if is_matrix(val) else val)
        # substitute the Greek letters to tex representations
        return translate(r'[^\x00-\x7F]', lambda m: gr_to_tex(m[0]), s)

    def format_float(x):
        prec = config.precision
        return float(f'%.{prec}g' % x)
    def format_scinum(x):
        def positive_case(x):
            supscripts = '⁰¹²³⁴⁵⁶⁷⁸⁹'
            e = floor(log10(x))
            b = format_float(x/10**e)
            supscript_pos = lambda n: ''.join([supscripts[int(i)] for i in str(n)])
            supscript = lambda n: '⁻' + supscript_pos(-n) if e < 0 else supscript_pos(n)
            return f"{b}×10{supscript(e)}"
        if x == 0: return '0'
        return positive_case(x) if x > 0 else '-' + positive_case(-x)
    def format_matrix(mat, indent):
        mat = [[format(x, config) for x in row] for row in mat]
        space = max([max([len(s) for s in row]) for row in mat])
        just_space = lambda s: s.ljust(space)
        row_str = lambda row, start, end, sep='  ': \
            ' '*indent + f"{start} {sep.join(map(just_space, row))}{end}"
        col_num = len(mat[0])
        return '\n'.join([row_str(['']*col_num, '╭', '╮')] +
                         [row_str(row, ' ', ' ', ', ') for row in mat] +
                         [row_str(['']*col_num, '╰', '╯')])
    def format_atom(val):
        if is_number(val):
            if isinstance(val, Rational):
                if type(val) == Fraction:
                    val.limit_denominator(10**config.precision)
                return str(val)
            elif type(val) == complex:
                re, im = format_float(val.real), format_float(val.imag)
                return f"{re}{'-' if im<0 else '+'}{abs(im)}i"
            elif abs(val) == inf:
                return '∞'
            elif abs(val) <= 0.001 or abs(val) >= 10000:
                return format_scinum(val)
            else: return str(format_float(val))
        elif type(val) is FunctionType:  # builtin
            return val.str
        else:  # symbol, function, range
            mapping = [(r'\*\*', '^'), (r'(?<![\,\(\[])\*', ' ')]
            s = str(val)
            for p in mapping:
                s = translate(p[0], p[1], s)
            return s

    s = ' ' * indent
    indented_format = lambda v: format(v, config, indent+2)
    if is_list(val):
        contains_mat = False
        for a in val:
            if is_matrix(a):  contains_mat = True
        if contains_mat:
            s += '[\n' + ',\n'.join(map(indented_format, val)) + '\n' + s + ']'
        elif is_matrix(val):
            s = format_matrix(val, indent)
        else:
            s += '['+', '.join(map(lambda v: format(v, config), val))+']'
    else:
        s += format_atom(val)
    return s