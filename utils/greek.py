import re

mappings = """
Α	α	alpha
Β	β	beta
Γ	γ	gamma
Δ	δ	delta
Ε	ε	epsilon
Ζ	ζ	zeta
Η	η	eta
Θ	θ	theta
Ι	ι	iota
Κ	κ	kappa
Λ	λ	lambda
Μ	μ	mu
Ν	ν	nu
Ξ	ξ	xi
Ο	ο	omicron
Π	π	pi
Ρ	ρ	rho
Σ	σ	sigma
Τ	τ	tau
Υ	υ	upsilon
Φ	φ	phi
Χ	χ	chi
Ψ	ψ	psi
Ω	ω	omega
""".splitlines()

alphabet = {}

for line in mappings:
    if not line: continue
    Gr, gr, english = line.split()
    if english == 'theta': 
        en, En = 'th', 'Th'
    elif english == 'psi': 
        en, En = 'ps', 'Ps'
    elif english == 'phi':
        en, En = 'f', 'F'
    else: 
        en = english[0]
        En = en.upper()
    alphabet[Gr] = english[0].upper() + english[1:]
    alphabet[gr] = english
    alphabet[En] = Gr
    alphabet[en] = gr


def gr_to_tex(letter):
    return '\\' + alphabet[letter]


def escape_to_greek(s):
    return re.sub(r'\\([Tt]h|[Pp]s|[a-zA-Z])', lambda m: alphabet[m[1]], s)


if __name__ == "__main__":
    print(escape_to_greek(r'\a \bXy\c1 \D3\s\t\u \t\theta\Psi'))
    print(gr_to_tex(escape_to_greek(r'\th')))
