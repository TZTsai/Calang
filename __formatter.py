from __builtins import *
from sympy import latex
from re import sub as translate

def format(val, indent=0):

    def is_matrix(x):
        return is_iterable(x) and len(x) > 1 and is_iterable(x[0]) and \
            all(is_iterable(it) and len(it) == len(x[0]) for it in x[1:])
    if config.latex:
        return latex(Matrix(val) if is_matrix(val) else val)

    def format_float(x):
        prec = config.prec
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
        mat = [[format(x) for x in row] for row in mat]
        space = max([max([len(s) for s in row]) for row in mat])
        just_space = lambda s: s.ljust(space)
        row_str = lambda row, start, end: \
            ' '*indent + f"{start} {' '.join(map(just_space, row))}{end}"
        col_num = len(mat[0])
        return '\n'.join([row_str(['']*col_num, '╭', '╮')] +
                         [row_str(row, ' ', ' ') for row in mat] +
                         [row_str(['']*col_num, '╰', '╯')])
    def format_atom(val):
        if is_number(val):
            if isinstance(val, Rational):
                if type(val) == Fraction:
                    val.limit_denominator(10**config.prec)
                return str(val)
            elif type(val) == complex:
                re, im = format_float(val.real), format_float(val.imag)
                return f"{re} {'-' if im<0 else '+'} {abs(im)}i"
            elif abs(val) == inf:
                return '∞'
            elif abs(val) <= 0.001 or abs(val) >= 10000:
                return format_scinum(val)
            else: return str(format_float(val))
        else:  # symbol, function, range
            mapping = [(r'\*\*', '^'), (r'(?<![\,\(\[])\*', '\u00b7')]
            s = str(val)
            for p in mapping:
                s = translate(p[0], p[1], s)
        return s

    s = ' ' * indent
    indented_format = lambda v: format(v, indent+2)
    if type(val) in (list, tuple):
        if any(is_matrix(it) for it in val):
            s += '[\n' + ',\n'.join(map(indented_format, val)) + '\n' + s + ']'
        elif is_matrix(val):
            s = format_matrix(val, indent)
        else:
            s += '['+', '.join(map(format, val))+']'
    else:
        s += format_atom(val)
    return s


def prettyprint(val):
    print(format(val))


config = lambda: None
config.prec = 4
config.latex = False