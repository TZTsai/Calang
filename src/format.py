from sympy import latex, pretty, init_printing
from re import sub as translate
from builtin import Rational, Fraction, Array, Matrix, is_number, is_array, floor, oo, log
from objects import Range, Env, Function
from parse import deparse
from utils.debug import log
from utils.funcs import is_tree, tree_tag
from functools import wraps
import config, objects


depth = 0  # recursion depth
indent = ' '
options = {}

sympy_matrix_box = '⎡⎤⎢⎥⎣⎦'
matrix_box = '┌┐││└┘'  # or "╭╮  ╰╯"
map_matrix_box = str.maketrans(sympy_matrix_box, matrix_box)


def formatter_wrapper(formatter):
    @wraps(formatter)
    def wrapped(value, linesep='\n', **opts):
        global depth
        depth += 1
        s = formatter(value, **opts)
        depth -= 1
        return s.replace('\n', linesep)
    return wrapped


@formatter_wrapper
def calc_format(val, **opts):
    global options, line_sep
    
    if is_tree(val):  # not fully evaluated
        return str(val)
    
    if opts:
        options = opts
    else:
        if depth == 0:
            options = {'tex': config.latex, 'sci': 0, 'bin': 0, 'hex': 0}
        opts = options
        
    if config.latex or opts['tex']:
        return latex(val)

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
    
    def format_list(val):
        if depth > 2: return '[...]'
        ss = list(map(calc_format, val))
        if any('\n' in s for s in ss):
            s = f',\n'.join(ss).replace('\n', '\n' + indent)
            return f'[\n{indent}{s}\n]'
        else:
            return '[%s]' % ', '.join(map(calc_format, val))
    
    def format_array(val):
        if depth > 2: return '[...]'
        
        s = pretty(val)
        if sympy_matrix_box[0] not in s:
            return s
        
        s = s.translate(map_matrix_box)
        ul, ur, ml, mr, ll, lr = matrix_box  # upper left, upper right ...
        sw = len(s.split('\n', 1)[0])  # line width
        
        start = ul + ' ' * (sw - 2) + ur + '\n'
        end = '\n' + ll + ' ' * (sw - 2) + lr
        
        s = s.replace(ul,ml).replace(ll,ml).replace(ur,mr).replace(lr,mr)
        return start + s + end
        
        # def row_str(row, start, end, sep='  '):
        #     return f"{start}{sep.join([s.ljust(space) for s in row])}{end}\n"
        # def empty_row_str(start, end):
        #     return row_str([''] * col_num, start, end)
        
        # mat = [[format(x) for x in row] for row in mat]
        # space = max([max([len(s) for s in row]) for row in mat])
        # col_num = len(mat[0])
        
        # return (empty_row_str(*matrix_box[:2]) +
        #         empty_row_str(*matrix_box[2:4]).join(
        #             row_str(row, *matrix_box[2:4], ', ') for row in mat) +
        #         empty_row_str(*matrix_box[4:]))
        
    def format_number(val):
        mag = abs(val)
        if type(val) is complex:
            re, im = format_float(val.real), format_float(val.imag)
            return f"{re} {'-' if im<0 else '+'} {abs(im)}ⅈ"
        elif mag == oo:
            return '∞'
        elif isinstance(val, Rational) and not opts['sci']:
            if type(val) is Fraction:
                val.limit_denominator(10**config.precision)
            if opts['bin']:
                return bin(val)
            elif opts['hex']: return hex(val)
            else:
                return str(val)
        elif mag <= 0.001 or mag >= 10000:
            return format_scinum(val)
        else:
            return str(format_float(val))
        
    def format_func(val):
        return str(val) if depth == 1 else repr(val)
        
    def format_env(val):
        if val.val is not None:
            return calc_format(val.val)
        else:
            return str(val) # if depth == 1 else repr(val)

    if type(val) is str:
        return f'"{val}"'
    if type(val) is tuple:
        return format_list(val)
    elif is_array(val):
        return format_array(val)
    elif is_number(val):
        return format_number(val) 
    elif callable(val):
        return format_func(val)
    elif isinstance(val, Env):
        return format_env(val)
    else:
        return pretty(val)


log.format = calc_format
objects.deparse = deparse

init_printing(str_printer=calc_format, use_unicode=True)
