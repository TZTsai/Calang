from sympy import latex, pretty, init_printing
from re import sub as translate
from funcs import Rational, Fraction, Array, Matrix, \
    is_number, is_array, floor, oo, log, likematrix
from objects import Range, Env, Function
from parse import deparse
from utils.debug import log
from utils.funcs import is_tree, tree_tag
from functools import wraps
import config, objects


sympy_matrix_box = '⎡⎤⎢⎥⎣⎦'
matrix_box = '┌┐││└┘'  # or "╭╮  ╰╯"
map_matrix_box = str.maketrans(sympy_matrix_box, matrix_box)
supscripts = '⁰¹²³⁴⁵⁶⁷⁸⁹'


class Formatter:
    indent = ' '
    options = {'tex': config.latex, 'sci': 0, 'bin': 0, 'hex': 0}
    
    def __init__(self):
        self.depth = 0
        self.opts = None
        
    def format(self, val, linesep='\n', **opts):
        self.opts = opts if opts else self.options

        if config.latex or self.opts['tex']:
            s = latex(val)
        else:
            s = self.fmt(val)
            
        return s.replace('\n', linesep)
    
    def format_float(self, x):
        prec = config.precision
        return float(f'%.{prec}g' % x)

    def format_scinum(self, x):
        def pos_supscript(n):
            return ''.join([supscripts[int(i)] for i in str(n)])
        def supscript(n):
            return '⁻' + pos_supscript(-n) if n < 0 else pos_supscript(n)
        def positive_case(x):
            e = floor(log(x)/log(10))
            b = self.format_float(x/10**e)
            return f"{b}×10{supscript(e)}"
        if x == 0:
            return '0'
        elif x > 0:
            return positive_case(x)
        else:
            return '-' + positive_case(-x)
    
    def format_list(self, val):
        if self.depth > 4: return '[...]'
        
        def row_str(row, start, end, sep='  '):
            return f"{start}{sep.join([s.ljust(space) for s in row])}{end}\n"
        def empty_row_str(start, end):
            return row_str([''] * col_num, start, end)
        
        if likematrix(val):
            sm = [[self.fmt(x) for x in row] for row in val]
            space = max([max([len(s) for s in row]) for row in sm])
            col_num = len(sm[0])
            return (empty_row_str(*matrix_box[:2]) +
                    empty_row_str(*matrix_box[2:4]).join(
                        row_str(row, *matrix_box[2:4], ', ') for row in sm) +
                    empty_row_str(*matrix_box[4:]))
            
        sl = list(map(self.fmt, val))
        if any('\n' in s for s in sl):
            s = f',\n'.join(sl).replace('\n', '\n' + self.indent)
            return f'[\n{self.indent}{s}\n]'
        else:
            return '[%s]' % ', '.join(map(self.fmt, val))
    
    def format_array(self, val):
        if self.depth > 3: return '[...]'
        
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
        
    def format_number(self, val):
        mag = abs(val)
        if type(val) is complex:
            re = self.format_float(val.real)
            im = self.format_float(val.imag)
            return f"{re} {'-' if im<0 else '+'} {abs(im)}ⅈ"
        elif mag == oo:
            return '∞'
        elif isinstance(val, Rational) and not self.opts['sci']:
            if type(val) is Fraction:
                val.limit_denominator(10**config.precision)
            if self.opts['bin']:
                return bin(val)
            elif self.opts['hex']:
                return hex(val)
            else:
                return str(val)
        elif mag <= 0.001 or mag >= 10000:
            return self.format_scinum(val)
        else:
            return str(self.format_float(val))
        
    def format_func(self, val):
        return str(val) if self.depth == 1 else repr(val)
        
    def format_env(self, val):
        if val.val is not None:
            return self.fmt(val.val)
        else:
            return str(val) # if depth == 1 else repr(val)

    def fmt(self, val):
        try:
            self.depth += 1
            if is_tree(val):  # not fully evaluated
                return str(val)
            elif type(val) is str:
                return f'"{val}"'
            elif type(val) is tuple:
                return self.format_list(val)
            elif is_array(val):
                return self.format_array(val)
            elif is_number(val):
                return self.format_number(val) 
            elif callable(val):
                return self.format_func(val)
            elif isinstance(val, Env):
                return self.format_env(val)
            else:
                try: return pretty(val)
                except: return str(val)
        finally:
            self.depth -= 1


calc_formatter = Formatter()
calc_format = calc_formatter.format

log.format = calc_format
objects.deparse = deparse

init_printing(str_printer=calc_format, use_unicode=True)
