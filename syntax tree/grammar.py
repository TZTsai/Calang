Grammar = r"""
STATEMENT   := ( EXP | ASSIGN | CONF | CMD | LOAD | IMPORT ) COMMENT

EXP     := IF-ELSE | WHEN | LOCAL | LAMBDA | ITEM OP EXP | ITEM
ASSIGN  := ( NAME | FUNFORM ) ":=" EXP
CONF    := "conf" NAME /\d+|on|off/ ?
CMD     := "ENV" | "del" NAME +
LOAD    := "load" NAME /-t|-v|-p/ *
IMPORT  := "import" NAME /-t|-v|-p/ *
COMMENT := "#" /.*/

NAME    := LETTER ( LETTER | [\d_] ) * "?" ?
LETTER  := [a-zA-Z\u0374-\u03FF]
FUNFORM := NAME SYNLIST("(", ")", ",", NAME)
FUNC    := NAME SYNLIST("(", ")", ",", EXP)
IF-ELSE := EXP "if" EXP "else" EXP
WHEN    := "when" SYNLIST("(", ")", ";", (EXP "," EXP))
ITEM    := GROUP | FUNC | LIST | NUM | NAME | SYMBOL | ANS

SYNLIST($OPN, $CLS, $SEP, $ITM) := $OPN ( $ITM $SEP ) * $ITM ? $CLS
"""


from mydecorators import memo
import re

def split(text, sep=None, maxsplit=-1):
    return [t.strip() for t in text.split(sep, maxsplit) if t]

def grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    rules = rules.replace('\t', ' ')
    for line in split(rules, '\n'):
        obj, description = split(line, ' := ', 2)
        alts = split(description, ' | ')
        G[obj] = tuple(map(split, alts))
    return G

def parse(type_, text, grammar):

    tokenizer = grammar[' '] + '(%s)'

    def parse_seq(seq, text):
        result = []
        for atom in seq:
            tree, text = parse_atom(atom, text)
            if text is None:
                return (None, None)
            result.append(tree)
        return result, text

    @memo  # avoid parsing the same atom again
    def parse_atom(atom, text):
        if atom in grammar:
            for alt in grammar[atom]:
                tree, rem = parse_seq(alt, text)
                if rem is not None:
                    return [atom]+tree, rem
            return (None, None)
        else:
            m = re.match(tokenizer % atom, text)
            return (None, None) if not m else (m[1], text[m.end():])

    return parse_atom(type_, text)