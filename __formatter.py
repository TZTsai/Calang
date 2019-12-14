from __builtins import *

def normal_mat(mat):
    space = max([max([len(format(x)) for x in row]) for row in mat])
    entry_str = lambda x: format(x).ljust(space)
    row_str = lambda row, start, end: '{} {}{}\n'.format(start, 
        ' '.join(map(entry_str, row)), end)
    s = row_str(mat[0], '┌', '┐')
    for row in mat[1:-1]: s += row_str(row, '│', '│')
    s += row_str(mat[-1], '└', '┘')
    return s

latex_mat = lambda mat: '\\begin{bmatrix}' + ' \\\\ '.join([
    ' & '.join(map(format,row)) for row in mat]) + '\\end{bmatrix}'

latex_table = lambda mat: r'\begin{table}[h!] \centering' + \
    f"\n\\begin{{tabular}}{{{'|c'*len(mat[0])+'|'}}}\n\\hline\n" + \
    ' \\\\ \\hline\n'.join([' & '.join(map(format,row)) for row in mat]) + \
    ' \\\\ \\hline\n\\end{tabular}\n\\end{table}'

matrix_format = normal_mat


def format(val):
    def pos_scinum_str(x):
        supscripts = '\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079'
        e = floor(log10(x))
        b = x/10**e
        supscript_pos = lambda n: ''.join([supscripts[int(i)] for i in format(n)])
        supscript = lambda n: '\u207b'+supscript_pos(-n) if e < 0 else supscript_pos(n)
        return f"{b}×10{supscript(e)}"
    if isNumber(val):
        if type(val) is Fraction: return val
        elif type(val) is complex:
            re, im = val.real, val.imag
            return f"{re} {'' if im<0 else '+'} {im}i"
        elif abs(val) <= 0.001 or abs(val) >= 10000:
            if val == 0: return '0'
            elif val > 0: return pos_scinum_str(val)
            else: return '-'+pos_scinum_str(-val)
        else: return val
    elif type(val) is list:
        if len(val) > 1 and type(val[0]) is list and all(
            [type(it) is list and len(it) == len(val[0])
            for it in val[1:]]):  # regarded as a matrix
            return matrix_format(val)
        else:
            return '['+', '.join(map(format, val))+']'
    else:
        return val