from sympy import latex, pretty
from re import sub as translate
from builtin import Rational, Fraction, Matrix, is_number, is_matrix, is_function, floor, inf, log
from objects import Range, Env, Map
from decompile import decompile
from utils.greek import gr_to_tex
import config

Map.decompile = decompile

indent = 0

def calc_format(val, **opts):
    if config.latex or opts['tex']:
        s = latex(Matrix(val) if is_matrix(val) else val)
        # substitute the Greek letters to tex representations
        return translate(r'[^\x00-\x7F]', lambda m: gr_to_tex(m[0]), s)
    
    def format_float(x):
        prec = config.precision
        return float(f'%.{prec}g' % x)
    def format_scinum(x):
        def positive_case(x):
            supscripts = '⁰¹²³⁴⁵⁶⁷⁸⁹'
            e = floor(log(x)/log(10))
            b = format_float(x/10**e)
            supscript_pos = lambda n: ''.join([supscripts[int(i)] for i in str(n)])
            supscript = lambda n: '⁻' + supscript_pos(-n) if e < 0 else supscript_pos(n)
            return f"{b}×10{supscript(e)}"
        if x == 0: return '0'
        return positive_case(x) if x > 0 else '-' + positive_case(-x)
    def format_matrix(mat):
        def row_str(row, start, end, sep='  '):
            return ' '*indent + f"{start}{sep.join([s.ljust(space) for s in row])}{end}"
        mat = [[format(x) for x in row] for row in mat]
        space = max([max([len(s) for s in row]) for row in mat])
        col_num = len(mat[0])
        return '\n'.join([row_str(['']*col_num, '╭', '╮')] +
                         [row_str(row, ' ', ' ', ', ') for row in mat] +
                         [row_str(['']*col_num, '╰', '╯')])
    def format_atom(val):
        if is_number(val):
            mag = abs(val)
            if type(val) == complex:
                re, im = format_float(val.real), format_float(val.imag)
                return f"{re} {'-' if im<0 else '+'} {abs(im)}ⅈ"
            elif mag == inf:
                return '∞'
            elif isinstance(val, Rational) and not opts['sci']:
                if type(val) == Fraction:
                    val.limit_denominator(10**config.precision)
                if opts['bin']:
                    return bin(val)
                elif opts['hex']:
                    return hex(val)
                else:
                    return str(val)
            elif mag <= 0.001 or mag >= 10000:
                return format_scinum(val)
            else: 
                return str(format_float(val))
        elif is_function(val):
            return str(val) if isinstance(val, Map) else val.__name__
        elif isinstance(val, Range):
            return str(val)
        elif isinstance(val, Env):
            if hasattr(val, 'val'):
                return calc_format(val.val, **opts)
            else:
                return str(val)
        else:
            return pretty(val, use_unicode=True)

    global indent
    s = ' ' * indent
    if type(val) is tuple:
        if any(map(is_matrix, val)):
            indent += 2
            s += '[\n%s\n%s]' % (',\n'.join(
                map(lambda v: calc_format(v, **opts), val)), s)
            indent -= 2
        elif is_matrix(val):
            s = format_matrix(val)
        else:
            s += '[%s]' % ', '.join(
                map(lambda v: calc_format(v, **opts), val))
    elif type(val) is list:
        s += '<incomplete eval: %s>' % decompile(val)
    else:
        s += format_atom(val)
    return s
