from mydecorators import memo, disabled
from myutils import trace, log
from pprint import pprint
from json import dump
import re
from __builtins import binary_ops, unary_l_ops, unary_r_ops


log.out = open('syntax tree/log.yaml', 'w')
# log.maxdepth = 1
# trace = disabled


def split(text: str, sep=None, maxsplit=-1):
    return [t.strip() for t in text.split(sep, maxsplit) if t]


MetaGrammar = split(r"""
DEF     := OBJ := EXP | MACRO := EXP
OBJ     := [A-Z_]+
MACRO   := %[A-Z_]+ < VARS > | %[A-Z_]+ < ITEMS >
VARS    := VAR VARS | VAR
VAR     := \$[A-Z_]+
EXP     := ALT [|] EXP | ALT
ALT     := ITEM_OP ALT | ITEM_OP
ITEM_OP := ITEM OP | ITEM
OP      := [*?+-]
ITEM    := GROUP | MACRO | ATOM
ITEMS   := ITEM ITEMS | ITEM
GROUP   := [(] EXP [)]
ATOM    := OBJ | STR | RE | CHARS | VAR | MARK
STR     := ".*?"
RE      := /.*?/
CHARS   := \[.*?\]
MARK    := (?![>|)]) \S+
""", '\n')

###  COMMENTS ON METAGRAMMAR  ###
# OP:       * for 0 or more matches, + for 1 or more, ? for 0 or 1, 
#           - for 1 match but it will not be included in the result
# MARK:     a token in the grammar that will be matched but not included in the
#           result; be cautious of conflicts with other symbols in MetaGrammar
# MACRO:    used for sub_macro; will not exist in the processed grammar

Grammar = split(r"""
LINE    := ( DEF | CONF | CMD | LOAD | IMPORT | EXP ) COMM ?

DEF      := ( NAME | FUNC ) := EXP
NAME    := /[a-zA-Z\u0374-\u03FF][a-zA-Z\u0374-\u03FF\d_]*[?]?/
FUNC    := NAME PARS
PARS    := %LST < "(" ")" , NAME >

CONF    := conf NAME /\d+|on|off/ ?
CMD     := "ENV" | "del" NAME +
LOAD    := load NAME /-[tvp]/ *
IMPORT  := import NAME /-[tvp]/ *
COMM    := [#] /.*/

EXP     := LOCAL | LAMBDA | IF_ELSE | OP_SEQ
IF_ELSE := OP_SEQ if OP_SEQ else EXP
OP_SEQ  := %SEQ < BOP UOP_IT >
LOCAL   := ( BIND_LS | BIND ) -> EXP
BIND_LS := %LST < "(" ")" , BIND >
BIND    := ( NAME_LS | NAME ) : EXP
NAME_LS := %LST < "[" "]" , ( NAME | NAME_LS ) >
LAMBDA  := ( PARS | NAME ) -> - EXP

UOP_IT  := LUOP ? ITEM RUOP ?
ITEM    := GROUP | WHEN | APPLY | LIST | ATOM
GROUP   := "(" EXP ")"
WHEN    := "when" "(" CASES ")"
CASES   := %SEQ < ; ( EXP , EXP ) > ; EXP
APPLY   := NAME ARG_LS
ARG_LS  := %LST < "(" ")" , EXP >
LIST    := %LST < "[" "]" ; %SEQ < , EXP > > | %LST < "[" "]" , EXP >
ATOM    := NUM | NAME | SYM | ANS

SYM     := ' NAME
ANS     := /_(\d+|_*)/

NUM     := COMPLEX | FLOAT | INT | BIN_NUM | HEX_NUM
COMPLEX := FLOAT [+-] FLOAT I
FLOAT   := INT /\.\d*/ ( [eE] INT ) ?
INT     := /-?\d+/
BIN_NUM := /0b[01]+/
HEX_NUM := /0x[0-9a-fA-F]+/

%LST < $OPN $CLS $SEP $ITM >   := $OPN - $CLS - | $OPN - $ITM ( $SEP $ITM ) * $CLS -
%SEQ < $SEP $ITM >             := $ITM ? ( $SEP $ITM ) *
""", '\n')


# add syntax for operations
bin_op, unl_op, unr_op = ['"' + '" | "'.join(ops) + '"' 
                          for ops in (binary_ops, unary_l_ops, unary_r_ops)]
Grammar.append('BOP    := ' + bin_op)
Grammar.append('LUOP   := ' + unl_op)
Grammar.append('RUOP   := ' + unr_op)


def simple_grammar(rules, whitespace=r'\s+'):
    G = {' ': whitespace}
    for line in rules:
        obj, exp = split(line, ':=', 1)
        alts = split(exp, ' | ')
        G[obj] = tuple(map(split, alts))
    return G

metagrammar = simple_grammar(MetaGrammar)


def parse_grammar(type_, text, grammar=metagrammar):

    tokenizer = grammar[' '] + '(%s)'

    def parse_seq(seq, text):
        result = []
        for atom in seq:
            tree, text = parse_atom(atom, text)
            if text is None: return (None, None)
            if tree is not None: result.append(tree)
        return result, text

    @trace
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
            if not m: 
                return (None, None)
            elif atom[:3] == '(?!' and atom[-1] == ')':
                # negative lookahead, should not consume the space
                return (None, text)
            else: 
                return (m[1], text[m.end():])

    return parse_atom(type_, ' '+text)


def calc_grammar(rules, whitespace=r'\s+'):
    G = {' ': whitespace}
    M = {}
    for rule in rules:
        tree, rem = parse_grammar('DEF', rule)
        assert tree[0] == 'DEF' and not rem
        name, body = tree[1][1], refactor_tree(tree[3])
        if name[0] == '%': 
            pars = tree[1][3]
            M[name] = [refactor_tree(pars), body]  # MACRO
        else: G[name] = body
    for obj in G: 
        G[obj] = sub_macro(G[obj], M)
    return G


def refactor_tree(tree: list):

    def prune(tree):
        if type(tree) is list:
            if tree[0] == 'GROUP':
                tree[:] = tree[2]
            if tree[0] == 'EXP' and len(tree) > 2:  # pop |
                tree.pop(2)
            for t in tree: prune(t)

    def flatten_nested(tree):
        if type(tree) is list:
            while tree[-1][0] == tree[0]:
                last = tree.pop(-1)
                tree.extend(last[1:])
            for t in tree: flatten_nested(t)            

    def simplify_tag(tree):  # also convert the tree into a pure tuple
        if type(tree) is list:
            while len(tree) == 2 and type(tree[1]) is list:
                tree = tree[1]
            return tuple(simplify_tag(t) for t in tree)
        return tree
    
    prune(tree)
    flatten_nested(tree)
    return simplify_tag(tree)


# @trace
def sub_macro(tree, macros, bindings=None):
    if type(tree) is tuple:
        if tree[0] == 'MACRO':
            name, args = tree[1], tree[3]
            pars, body = macros[name]
            args = args[1:]
            pars = [p[1] for p in pars[1:]]
            bindings = dict(zip(pars, args))
            return sub_macro(body, macros, bindings)
        elif tree[0] == 'VAR':
            var = tree[1]
            try: return sub_macro(bindings[var], macros, bindings)
            except: raise SyntaxError('failed to substitute the macro')
        else:
            return tuple(sub_macro(t, macros, bindings) for t in tree)
    else:
        return tree


## tests
def check(f, args, expected):
    actual = f(*args)
    if actual != expected:
        comp_list(expected, actual)
        raise AssertionError(f'Wrong Answer of {f.__name__}{tuple(args)}\n' +
                             f'Expected: {expected}\n' +
                             f'Actual: {actual}\n')

def comp_list(l1, l2):
    if type(l1) not in (tuple, list, dict):
        if l1 != l2: print(l1, l2)
    elif len(l1) != len(l2):
        print(l1, l2)
    else:
        for i1, i2 in zip(l1, l2):
            if type(l1) is dict: comp_list(l1[i1], l2[i2])
            else: comp_list(i1, i2)

def test_grammar():

    def test_parse():
        check(parse_grammar, ('ALT', ', -'), (['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['MARK', ',']]], ['OP', '-']]], ''))
        check(parse_grammar, 
        ('DEF', 'LIST    := %LST < "[" "]" ; %SEQ < , /.*/ > >'), 
        (['DEF', ['OBJ', 'LIST'], ':=', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['MACRO', '%LST', '<', ['ITEMS', ['ITEM', ['ATOM', ['STR', '"["']]], ['ITEMS', ['ITEM', ['ATOM', ['STR', '"]"']]], ['ITEMS', ['ITEM', ['ATOM', ['MARK', ';']]], ['ITEMS', ['ITEM', ['MACRO', '%SEQ', '<', ['ITEMS', ['ITEM', ['ATOM', ['MARK', ',']]], ['ITEMS', ['ITEM', ['ATOM', ['RE', '/.*/']]]]], '>']]]]]], '>']]]]]], ''))
        check(parse_grammar, 
        ('DEF', 'EXP := LOCAL | LAMBDA | IF_ELSE | OP_SEQ'), 
        (['DEF', ['OBJ', 'EXP'], ':=', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'LOCAL']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'LAMBDA']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'IF_ELSE']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'OP_SEQ']]]]]]]]]], ''))
        check(parse_grammar,
        ('DEF', 'LC := ( BIND_LS | BIND * ) ? "->" EXP'),
        (['DEF', ['OBJ', 'LC'], ':=', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['GROUP', '(', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BIND_LS']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BIND']]], ['OP', '*']]]]], ')']], ['OP', '?']], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['STR', '"->"']]]], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'EXP']]]]]]]]], ''))

    def test_refactor():
        check(refactor_tree, 
        [['DEF', ['OBJ', 'EXP'], ':=', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'LOCAL']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'LAMBDA']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'IF_ELSE']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'OP_SEQ']]]]]]]]]]], 
        ('DEF', ('OBJ', 'EXP'), ':=', ('EXP', ('OBJ', 'LOCAL'), ('OBJ', 'LAMBDA'), ('OBJ', 'IF_ELSE'), ('OBJ', 'OP_SEQ'))))
        check(refactor_tree, 
        [['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['GROUP', '(', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BIND_LS']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BIND']]], ['OP', '*']]]]], ')']], ['OP', '?']], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['STR', '"->"']]]], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'EXP']]]]]]]]],
        ('ALT', ('ITEM_OP', ('EXP', ('OBJ', 'BIND_LS'), ('ITEM_OP', ('OBJ', 'BIND'), ('OP', '*'))), ('OP', '?')), ('STR', '"->"'), ('OBJ', 'EXP')))

    def test_macro():    
        rules = ['LIST    := %LST < "[" "]" ; %SEQ < , /.*/ > >',
                '%LST < $OPN $CLS $SEP $ITM > := $OPN $CLS | $OPN $ITM ( $SEP $ITM ) * $CLS',
                '%SEQ < $SEP $ITM >           := $ITM ? ( $SEP $ITM ) *']
        check(calc_grammar, [rules],
{' ': '\\s+',
 'LIST': ('EXP',
          ('ALT', ('STR', '"["'), ('STR', '"]"')),
          ('ALT',
           ('STR', '"["'),
           ('ALT',
            ('ITEM_OP', ('RE', '/.*/'), ('OP', '?')),
            ('ITEM_OP', ('ALT', ('MARK', ','), ('RE', '/.*/')), ('OP', '*'))),
           ('ITEM_OP',
            ('ALT',
             ('MARK', ';'),
             ('ALT',
              ('ITEM_OP', ('RE', '/.*/'), ('OP', '?')),
              ('ITEM_OP',
               ('ALT', ('MARK', ','), ('RE', '/.*/')),
               ('OP', '*')))),
            ('OP', '*')),
           ('STR', '"]"')))})

    test_parse()
    test_refactor()
    test_macro()


if __name__ == "__main__":
    test_grammar()

grammar = calc_grammar(Grammar)
with open('syntax tree/grammar.json', 'w') as gf:
    dump(grammar, gf, indent=2)

# pprint(grammar)
