from fractions import Fraction


def check_matrix(list_2D):
    assert hasattr(list_2D, '__iter__')
    assert all(map(lambda l: hasattr(l, '__iter__'), list_2D))
    assert len(set([len(l) for l in list_2D])) == 1


#### READ & PRINT ####
def read_mat(mstr):
    return [[eval(e) for e in r.split()] for r in mstr.splitlines()]

def read_mat_latex(mstr):
    return [[eval(e) for e in r.split('&')] for r in mstr.split('\\')]

def display_mat(mat):
    for i in range(rows_num(mat)):
        for j in range(cols_num(mat)):
            print(mat[i][j], end=' ')
        print()
    print('------------------')

def print_latex_code(mat):
    print('\\begin{bmatrix}')
    print(' \\\\ '.join([' & '.join(map(str,row)) for row in mat]))
    print('\\end{bmatrix}')


#### VECTOR ####
def addv(v1, v2):
    return [a1+a2 for a1, a2 in zip(v1, v2)]

def scalev(v, s):
    return [s*a for a in v]

def subv(v1, v2):
    return addv(v1, scalev(v2, -1))

def dotp(v1, v2):
    assert len(v1) == len(v2)
    return sum([a1*a2 for a1,a2 in zip(v1, v2)])


#### MATRIX ####
def rows_num(rows):
    return len(rows)

def cols_num(rows):
    return len(rows[0])

def row(rows, k):
    assert k < rows_num(rows)
    return rows[k]

def col(rows, k):
    assert k < cols_num(rows)
    return [row[k] for row in rows]

def to_mat(v):
    return [[x] for x in v]

def addm(m1, m2):
    assert rows_num(m1) == rows_num(m2) and cols_num(m1) == cols_num(m2)
    return [addv(v1, v2) for v1, v2 in zip(m1, m2)]

def subm(m1, m2):
    return addm(m1, scalem(m2, -1))

def multm(m1, m2):
    assert cols_num(m1) == rows_num(m2)
    return [[dotp(row, col(m2, c)) for c in range(cols_num(m2))] for row in m1]

def map_mat(f, m):
    return [[f(e) for e in r] for r in m]

def scalem(m, s):
    return map_mat(lambda x: s*x, m)

def issquare(m):
    return rows_num(m) == cols_num(m)

def idmat(n):
    delta = lambda i, j: 1 if i == j else 0
    return [[delta(i, j) for i in range(n)] for j in range(n)]

def augment(m1, m2):
    assert(rows_num(m1) == rows_num(m2))
    return [tuple(v1)+tuple(v2) for v1, v2 in zip(m1, m2)]

def slice(m, start, end=None):
    return [row[start:end] for row in m]

def mat_eq(m1, m2):
    iszero = lambda x: x == 0
    return all(all(iszero(e) for e in r) for r in subm(m1, m2))

def diag(m):
    c_num = cols_num(m)
    return [[m[r][c] if c == r else 0 for c in range(c_num)] for r in range(len(m))]

def lower(m):
    c_num = cols_num(m)
    return [[m[r][c] if c < r else 0 for c in range(c_num)] for r in range(len(m))]

def upper(m):
    c_num = cols_num(m)
    return [[m[r][c] if c > r else 0 for c in range(c_num)] for r in range(len(m))]

def transpose(m):
    r_num = rows_num(m)
    c_num = cols_num(m)
    return [[m[r][c] for r in range(r_num)] for c in range(c_num)]

def to_float(m, prec=2):
    return map_mat(lambda x: round(float(x), prec), m)
