from sympy import latex, pretty
from re import sub as translate
from builtin import Rational, Fraction, Matrix, is_number, is_function, is_env, is_matrix, floor, inf, log
from objects import Range, Env, Function
from parse import rev_parse, is_tree
from utils.debug import log
import config, objects


depth = 0  # recursion depth
indent_width = 1
indent_level = 0
line_sep = '\n'
options = {}


def calc_format(val, linesep='\n', **opts):
    global options, depth, indent_level, line_sep
    
    if is_tree(val):  # not fully evaluated
        return val
    
    if opts:
        options = opts
    else:
        if depth == 0:
            options = {'tex': config.latex, 'sci': 0, 'bin': 0, 'hex': 0}
        opts = options
        
    if config.latex or opts['tex']:
        return latex(Matrix(val) if is_matrix(val) else val)
    
    if linesep != '\n':
        line_sep = linesep
    else:
        linesep = line_sep

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
            return f"{start}{sep.join([s.ljust(space) for s in row])}{end}"
        mat = [[format(x) for x in row] for row in mat]
        space = max([max([len(s) for s in row]) for row in mat])
        col_num = len(mat[0])
        return '\n'.join(
            [row_str(['']*col_num, '╭', '╮')] +
            [row_str(row, ' ', ' ', ', ') for row in mat] +
            [row_str(['']*col_num, '╰', '╯')])
        
    def format_atom(val):
        if is_number(val):
            mag = abs(val)
            if type(val) is complex:
                re, im = format_float(val.real), format_float(val.imag)
                return f"{re} {'-' if im<0 else '+'} {abs(im)}ⅈ"
            elif mag == inf:
                return '∞'
            elif isinstance(val, Rational) and not opts['sci']:
                if type(val) is Fraction:
                    val.limit_denominator(10**config.precision)
                if opts['bin']: return bin(val)
                elif opts['hex']: return hex(val)
                else: return str(val)
            elif mag <= 0.001 or mag >= 10000:
                return format_scinum(val)
            else: 
                return str(format_float(val))
        elif is_function(val):
            return str(val) if depth == 1 else repr(val)
        elif is_env(val):
            if hasattr(val, 'val'):
                return calc_format(val.val)
            else:
                return str(val) if depth == 1 else repr(val)
        elif isinstance(val, Range):
            return str(val)
        elif isinstance(val, str):
            return f'"{val}"'
        else:
            return pretty(val, use_unicode=True)

    depth += 1
    indent = ' ' * indent_width * indent_level
    s = indent
    if type(val) is tuple:
        if any(map(is_matrix, val)):
            indent_level += 1
            items = f',\n'.join(map(calc_format, val))
            s += f'[\n{items}\n]'
            indent_level -= 1
        elif is_matrix(val):
            s += format_matrix(val)
        else:
            s += '[%s]' % ', '.join(map(calc_format, val))
    else:
        s += format_atom(val)
    s = s.replace('\n', linesep + indent)
    depth -= 1
    return s


log.format = calc_format
objects.tree2str = rev_parse
