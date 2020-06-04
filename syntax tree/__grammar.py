from mydecorators import memo, disabled
from myutils import trace, log
from pprint import pprint
from json import dump
import re
from __builtins import binary_ops, unary_l_ops, unary_r_ops


log.out = open('syntax tree/log.txt', 'w')
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
OP      := [*?+\-]
ITEM    := GROUP | MACRO | ATOM
ITEMS   := ITEM ITEMS | ITEM
GROUP   := [(] EXP [)]
ATOM    := OBJ | STR | RE | CHARS | VAR
STR     := ".*?"
RE      := /.*?/
CHARS   := \[.*?\]
""", '\n')


Grammar = split(r"""
LINE    := ( DEF | CONF | CMD | LOAD | IMPORT | EXP ) COMM ?

DEF      := ( NAME | FUNC ) ":=" EXP
NAME    := /[a-zA-Z\u0374-\u03FF][a-zA-Z\u0374-\u03FF\d_]*[?]?/
FUNC    := NAME PARS
PARS    := %LST<"(" ")" "," NAME>

CONF    := "conf" NAME /\d+|on|off/ ?
CMD     := "ENV" | "del" NAME +
LOAD    := "load" NAME /-[tvp]/ *
IMPORT  := "import" NAME /-[tvp]/ *
COMM    := [#] /.*/

EXP     := LOCAL | LAMBDA | IF_ELSE | OP_SEQ
IF_ELSE := OP_SEQ "if" OP_SEQ "else" EXP
OP_SEQ  := %SEQ<BOP UOP_IT>
LOCAL   := ( BIND_LS | BIND ) "->" EXP
BIND_LS := %LST<"(" ")" "," BIND>
BIND    := ( NAME_LS | NAME ) ":" EXP
NAME_LS := %LST<"[" "]" "," ( NAME | NAME_LS )>
LAMBDA  := ( PARS | NAME ) "->" EXP

UOP_IT  := LUOP ? ITEM RUOP ?
ITEM    := GROUP | WHEN | APPLY | LIST | ATOM
GROUP   := "(" EXP ")"
WHEN    := "when" "(" CASES ")"
CASES   := %SEQ<";" ( EXP "," EXP )> ";" EXP
APPLY   := NAME %LST<"(" ")" "," EXP>
LIST    := %LST<"[" "]" ";" %SEQ<"," EXP>> | %LST<"[" "]" "," EXP>
ATOM    := NUM | NAME | SYM | ANS

SYM     := "'" NAME
ANS     := /_(\d+|_*)/

NUM     := COMPLEX | FLOAT | INT | BIN_NUM | HEX_NUM
COMPLEX := FLOAT [+-] FLOAT "I"
FLOAT   := INT /\.\d*/ ( [eE] INT ) ?
INT     := /-?\d+/
BIN_NUM := /0b[01]+/
HEX_NUM := /0x[0-9a-fA-F]+/

%LST<$OPN $CLS $SEP $ITM>   := $OPN $CLS | $OPN $ITM ( $SEP $ITM ) * $CLS
%SEQ<$SEP $ITM>             := $ITM ? ( $SEP $ITM ) *
""", '\n')


# add syntax for operations
bin_op, unl_op, unr_op = ['"' + '" | "'.join(ops) + '"' 
                          for ops in (binary_ops, unary_l_ops, unary_r_ops)]
Grammar.append('BOP    := ' + bin_op)
Grammar.append('LUOP   := ' + unl_op)
Grammar.append('RUOP   := ' + unr_op)


def simple_grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    for line in rules:
        obj, exp = split(line, ':=', 1)
        alts = split(exp, ' | ')
        G[obj] = tuple(map(split, alts))
    return G

metagrammar = simple_grammar(MetaGrammar)


def grammar_parse(type_, text, grammar=metagrammar):

    tokenizer = grammar[' '] + '(%s)'

    def parse_seq(seq, text):
        result = []
        for atom in seq:
            tree, text = parse_atom(atom, text)
            if text is None: return (None, None)
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


def calc_grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    M = {}
    for rule in rules:
        tree, rem = grammar_parse('DEF', rule)
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

    trace = disabled

    @trace
    def prune(tree):
        if type(tree) is list:
            if tree[0] == 'GROUP':
                tree[:] = tree[2]
            if tree[0] == 'EXP' and len(tree) > 2:  # pop |
                tree.pop(2)
            for t in tree: prune(t)

    @trace
    def flatten_nested(tree):
        if type(tree) is list:
            while tree[-1][0] == tree[0]:
                last = tree.pop(-1)
                tree.extend(last[1:])
            for t in tree: flatten_nested(t)            

    @trace
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


def test_grammar():

    def test_refactor():
        t = grammar_parse('DEF', 'EXP := LOCAL | LAMBDA | IF_ELSE | OP_SEQ')[0][3]
        assert refactor_tree(t) == ('EXP', ('OBJ', 'LOCAL'), ('OBJ', 'LAMBDA'), 
                                    ('OBJ', 'IF_ELSE'), ('OBJ', 'OP_SEQ'))
        t = grammar_parse('DEF', 'LC := ( BIND_LS | BIND * ) ? "->" EXP')[0][3]
        assert (refactor_tree(t) == 
('ALT',
 ('ITEM_OP',
  ('EXP', ('OBJ', 'BIND_LS'), ('ITEM_OP', ('OBJ', 'BIND'), ('OP', '*'))),
  ('OP', '?')),
 ('STR', '"->"'),
 ('OBJ', 'EXP')))

    def test_macro():    
        rules = ['LIST    := %LST<"[" "]" ";" %SEQ<"," /.*/>>',
                '%LST<$OPN $CLS $SEP $ITM> := $OPN $CLS | $OPN $ITM ( $SEP $ITM ) * $CLS',
                '%SEQ<$SEP $ITM>           := $ITM ? ( $SEP $ITM ) *']
        assert (calc_grammar(rules) ==
{' ': '\\s*',
 'LIST': ('EXP',
          ('ALT', ('STR', '"["'), ('STR', '"]"')),
          ('ALT',
           ('STR', '"["'),
           ('ALT',
            ('ITEM_OP', ('RE', '/.*/'), ('OP', '?')),
            ('ITEM_OP', ('ALT', ('STR', '","'), ('RE', '/.*/')), ('OP', '*'))),
           ('ITEM_OP',
            ('ALT',
             ('STR', '";"'),
             ('ALT',
              ('ITEM_OP', ('RE', '/.*/'), ('OP', '?')),
              ('ITEM_OP',
               ('ALT', ('STR', '","'), ('RE', '/.*/')),
               ('OP', '*')))),
            ('OP', '*')),
           ('STR', '"]"')))})

    test_refactor()
    test_macro()


if __name__ == "__main__":
    test_grammar()

grammar = calc_grammar(Grammar)
with open('syntax tree/grammar.json', 'w') as gf:
    dump(grammar, gf, indent=2)

# pprint(grammar)
"""
{' ': '\\s*',
 'ANS': ('RE', '/_(\\d+|_*)/'),
 'APPLY': ('ALT',
           ('OBJ', 'NAME'),    
           ('EXP',
            ('ALT', ('STR', '"("'), ('STR', '")"')),
            ('ALT',
             ('STR', '"("'),
             ('OBJ', 'EXP'),
             ('ITEM_OP', ('ALT', ('STR', '","'), ('OBJ', 'EXP')), ('OP', '*')),
             ('STR', '")"')))),
 'DEF': ('ALT',
        ('EXP', ('OBJ', 'NAME'), ('OBJ', 'FUNC')),
        ('STR', '":="'),
        ('OBJ', 'EXP')),
 'ATOM': ('EXP',
          ('OBJ', 'NUM'),
          ('OBJ', 'NAME'),
          ('OBJ', 'SYM'),
          ('OBJ', 'ANS')),
 'BIND': ('ALT',
          ('EXP', ('OBJ', 'NAME_LS'), ('OBJ', 'NAME')),
          ('STR', '":"'),
          ('OBJ', 'EXP')),
 'BIND_LS': ('EXP',
             ('ALT', ('STR', '"("'), ('STR', '")"')),
             ('ALT',
              ('STR', '"("'),
              ('OBJ', 'BIND'),
              ('ITEM_OP',
               ('ALT', ('STR', '","'), ('OBJ', 'BIND')),
               ('OP', '*')),
              ('STR', '")"'))),
 'BIN_NUM': ('RE', '/0b[01]+/'),
 'BOP': ('EXP',
         ('STR', '"+"'),
         ('STR', '"-"'),
         ('STR', '"*"'),
         ('STR', '".*"'),
         ('STR', '"/"'),
         ('STR', '"//"'),
         ('STR', '"^"'),
         ('STR', '"%"'),
         ('STR', '"="'),
         ('STR', '"!="'),
         ('STR', '"<"'),
         ('STR', '">"'),
         ('STR', '"<="'),
         ('STR', '">="'),
         ('STR', '"xor"'),
         ('STR', '"in"'),
         ('STR', '"outof"'),
         ('STR', '"~"'),
         ('STR', '".."'),
         ('STR', '"and"'),
         ('STR', '"or"'),
         ('STR', '"/\\"'),
         ('STR', '"\\/"')),
 'CASES': ('ALT',
           ('ALT',
            ('ITEM_OP',
             ('ALT', ('OBJ', 'EXP'), ('STR', '","'), ('OBJ', 'EXP')),
             ('OP', '?')),
            ('ITEM_OP',
             ('ALT',
              ('STR', '";"'),
              ('ALT', ('OBJ', 'EXP'), ('STR', '","'), ('OBJ', 'EXP'))),
             ('OP', '*'))),
           ('STR', '";"'),
           ('OBJ', 'EXP')),
 'CMD': ('EXP',
         ('STR', '"ENV"'),
         ('ALT', ('STR', '"del"'), ('ITEM_OP', ('OBJ', 'NAME'), ('OP', '+')))),
 'COMM': ('ALT', ('CHARS', '[#]'), ('RE', '/.*/')),
 'COMPLEX': ('ALT',
             ('OBJ', 'FLOAT'),
             ('CHARS', '[+-]'),
             ('OBJ', 'FLOAT'),
             ('STR', '"I"')),
 'CONF': ('ALT',
          ('STR', '"conf"'),
          ('OBJ', 'NAME'),
          ('ITEM_OP', ('RE', '/\\d+|on|off/'), ('OP', '?'))),
 'EXP': ('EXP',
         ('OBJ', 'LOCAL'),
         ('OBJ', 'LAMBDA'),
         ('OBJ', 'IF_ELSE'),
         ('OBJ', 'OP_SEQ')),
 'FLOAT': ('ALT',
           ('OBJ', 'INT'),
           ('RE', '/\\.\\d*/'),
           ('ITEM_OP',
            ('ALT', ('CHARS', '[eE]'), ('OBJ', 'INT')),
            ('OP', '?'))),
 'FUNC': ('ALT', ('OBJ', 'NAME'), ('OBJ', 'PARS')),
 'GROUP': ('ALT', ('STR', '"("'), ('OBJ', 'EXP'), ('STR', '")"')),
 'HEX_NUM': ('RE', '/0x[0-9a-fA-F]+/'),
 'IF_ELSE': ('ALT',
             ('OBJ', 'OP_SEQ'),
             ('STR', '"if"'),
             ('OBJ', 'OP_SEQ'),
             ('STR', '"else"'),
             ('OBJ', 'EXP')),
 'IMPORT': ('ALT',
            ('STR', '"import"'),
            ('OBJ', 'NAME'),
            ('ITEM_OP', ('RE', '/-[tvp]/'), ('OP', '*'))),
 'INT': ('RE', '/-?\\d+/'),
 'ITEM': ('EXP',
          ('OBJ', 'GROUP'),
          ('OBJ', 'WHEN'),
          ('OBJ', 'APPLY'),
          ('OBJ', 'LIST'),
          ('OBJ', 'ATOM')),
 'LAMBDA': ('ALT',
            ('EXP', ('OBJ', 'PARS'), ('OBJ', 'NAME')),
            ('STR', '"->"'),
            ('OBJ', 'EXP')),
 'LINE': ('ALT',
          ('EXP',
           ('OBJ', 'DEF'),
           ('OBJ', 'CONF'),
           ('OBJ', 'CMD'),
           ('OBJ', 'LOAD'),
           ('OBJ', 'IMPORT'),
           ('OBJ', 'EXP')),
          ('ITEM_OP', ('OBJ', 'COMM'), ('OP', '?'))),
 'LIST': ('EXP',
          ('EXP',
           ('ALT', ('STR', '"["'), ('STR', '"]"')),
           ('ALT',
            ('STR', '"["'),
            ('ALT',
             ('ITEM_OP', ('OBJ', 'EXP'), ('OP', '?')),
             ('ITEM_OP', ('ALT', ('STR', '","'), ('OBJ', 'EXP')), ('OP', '*'))),
            ('ITEM_OP',
             ('ALT',
              ('STR', '";"'),
              ('ALT',
               ('ITEM_OP', ('OBJ', 'EXP'), ('OP', '?')),
               ('ITEM_OP',
                ('ALT', ('STR', '","'), ('OBJ', 'EXP')),
                ('OP', '*')))),
             ('OP', '*')),
            ('STR', '"]"'))),
          ('EXP',
           ('ALT', ('STR', '"["'), ('STR', '"]"')),
           ('ALT',
            ('STR', '"["'),
            ('OBJ', 'EXP'),
            ('ITEM_OP', ('ALT', ('STR', '","'), ('OBJ', 'EXP')), ('OP', '*')),
            ('STR', '"]"')))),
 'LOAD': ('ALT',
          ('STR', '"load"'),
          ('OBJ', 'NAME'),
          ('ITEM_OP', ('RE', '/-[tvp]/'), ('OP', '*'))),
 'LOCAL': ('ALT',
           ('EXP', ('OBJ', 'BIND_LS'), ('OBJ', 'BIND')),
           ('STR', '"->"'),
           ('OBJ', 'EXP')),
 'LUOP': ('EXP',
          ('STR', '"-"'),
          ('STR', '"not"'),
          ('STR', '"!"'),
          ('STR', '"@"')),
 'NAME': ('RE', '/[a-zA-Z\\u0374-\\u03FF][a-zA-Z\\u0374-\\u03FF\\d_]*[?]?/'),
 'NAME_LS': ('EXP',
             ('ALT', ('STR', '"["'), ('STR', '"]"')),
             ('ALT',
              ('STR', '"["'),
              ('EXP', ('OBJ', 'NAME'), ('OBJ', 'NAME_LS')),
              ('ITEM_OP',
               ('ALT',
                ('STR', '","'),
                ('EXP', ('OBJ', 'NAME'), ('OBJ', 'NAME_LS'))),
               ('OP', '*')),
              ('STR', '"]"'))),
 'NUM': ('EXP',
         ('OBJ', 'COMPLEX'),
         ('OBJ', 'FLOAT'),
         ('OBJ', 'INT'),
         ('OBJ', 'BIN_NUM'),
         ('OBJ', 'HEX_NUM')),
 'OP_SEQ': ('ALT',
            ('ITEM_OP', ('OBJ', 'UOP_IT'), ('OP', '?')),
            ('ITEM_OP',
             ('ALT', ('OBJ', 'BOP'), ('OBJ', 'UOP_IT')),
             ('OP', '*'))),
 'PARS': ('EXP',
          ('ALT', ('STR', '"("'), ('STR', '")"')),
          ('ALT',
           ('STR', '"("'),
           ('OBJ', 'NAME'),
           ('ITEM_OP', ('ALT', ('STR', '","'), ('OBJ', 'NAME')), ('OP', '*')),
           ('STR', '")"'))),
 'RUOP': ('EXP', ('STR', '"!"'), ('STR', '"!!"')),
 'SYM': ('ALT', ('STR', '"\'"'), ('OBJ', 'NAME')),
 'UOP_IT': ('ALT',
            ('ITEM_OP', ('OBJ', 'LUOP'), ('OP', '?')),
            ('OBJ', 'ITEM'),
            ('ITEM_OP', ('OBJ', 'RUOP'), ('OP', '?'))),
 'WHEN': ('ALT',
          ('STR', '"when"'),
          ('STR', '"("'),
          ('OBJ', 'CASES'),
          ('STR', '")"'))}
"""