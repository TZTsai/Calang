from numpy.polynomial import Polynomial

poly = lambda *coeffs: Polynomial(coeffs)

def roots(*args):
    if len(args) == 1 and type(args[0]) is Polynomial:
        return list(p.roots())
    return list(Polynomial(args).roots())


export = {'poly': poly, 'roots': roots}