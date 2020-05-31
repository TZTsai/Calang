import re


alphabet = {}
with open('utils/greek_alphabet.txt', 'r', encoding='utf8') as fi:
    for line in fi.readlines():
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
