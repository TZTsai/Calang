MetaGrammar = r"""
DEF     := OBJ := EXP | MACRO := EXP
OBJ     := [A-Z_]+
MACRO   := %[A-Z_]+ < VARS > | %[A-Z_]+ < ITEMS >
VARS    := VAR VARS | VAR
VAR     := \$[A-Z_]+
EXP     := ALT [|] EXP | ALT
ALT     := ITEM_OP ALT | ITEM_OP
ITEM_OP := ITEM OP | ITEM
OP      := [*?+]
ITEM    := GROUP | MACRO | ATOM
ITEMS   := ITEM ITEMS | ITEM
GROUP   := [(] EXP [)]
ATOM    := OBJ | STR | REGEX | CHARSET | VAR
STR     := ".*?"
REGEX   := /.*?/
CHARSET := \[.*?\]
"""

Grammar = r"""
STATEMENT   := ( ASSIGN | CONF | CMD | LOAD | IMPORT | EXP ) COMMENT

EXP     := IF_ELSE | WHEN | LOCAL | LAMBDA | %SEQ<BIN_OP ITEM_OP>
ASSIGN  := ( NAME | FUNFORM ) ":=" EXP
CONF    := "conf" NAME /\d+|on|off/ ?
CMD     := "ENV" | "del" NAME +
LOAD    := "load" NAME /-[tvp]/ *
IMPORT  := "import" NAME /-[tvp]/ *
COMMENT := "#" /.*/

NAME    := LETTER ( LETTER | [\d_] ) * "?" ?
LETTER  := [a-zA-Z\u0374-\u03FF]
FUNFORM := NAME ARGS
ARGS    := %LST<"(" ")" "," NAME>
FUNC    := NAME "(" EXPS ")"
EXPS    := %SEQ<"," EXP>
IF_ELSE := EXP "if" EXP "else" EXP
WHEN    := "when" CASES ";" EXP
CASES   := %LST<"(" ")" ";" ( EXP "," EXP )>
LOCAL   := ( BINDS | BIND ) "->" EXP
BINDS   := %LST<"(" ")" "," BIND>
BIND    := ( ARGLIST | NAME ) "=" EXP
ARGLIST := %LST<"[" "]" "," ( NAME | ARGLIST )>
LAMBDA  := ( ARGS | NAME ) "->" EXP

ITEM_OP := UNL_OP ITEM | ITEM UNR_OP | ITEM
ITEM    := GROUP | FUNC | LIST | ATOM
LIST    := "[" ( %SEQ<";" EXPS> | EXPS ) "]"
ATOM    := NUM | NAME | SYMBOL | ANS

SYMBOL  := "'" NAME
ANS     := /_(\d+|_*)/

NUM     := COMPLEX | FLOAT | INT | BIN_NUM | HEX_NUM
COMPLEX := FLOAT [+-] FLOAT "I"
FLOAT   := INT /\.\d*/ ( [eE] INT ) ?
INT     := /-?\d+/
BIN_NUM := /0b[01]+/
HEX_NUM := /0x[0-9a-fA-F]+/

%LST<$OPN $CLS $SEP $ITM>   := $OPN $ITM ? ( $SEP $ITM ) * ( $CLS | "" )
%SEQ<$SEP $ITM>             := $ITM ? ( $SEP $ITM ) *
"""


from mydecorators import memo, disabled
from myutils import trace
import re


def split(text: str, sep=None, maxsplit=-1):
    return [t.strip() for t in text.split(sep, maxsplit) if t]


def simple_grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    rules = rules.replace('\t', ' ')
    for line in split(rules, '\n'):
        obj, exp = split(line, ' := ', 1)
        alts = split(exp, ' | ')
        G[obj] = tuple(map(split, alts))
    return G


def simple_parse(type_, text, grammar):

    tokenizer = grammar[' '] + '(%s)'

    def parse_seq(seq, text):
        result = []
        for atom in seq:
            tree, text = parse_atom(atom, text)
            if text is None: return (None, None)
            result.append(tree)
        return result, text

    # @trace
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


metagrammar = simple_grammar(MetaGrammar)

def advanced_grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    lines = split(rules.replace('\t', ' '), '\n')
    for line in lines:
        tree, rem = simple_parse('DEF', line, metagrammar)
        assert tree[0] == 'DEF' and not rem
        _, obj, body = refactor_tree(tree)
        G[obj] = body
    return G

@memo
def refactor_tree(tree: list):

    def eliminate(tree):
        if tree[0] == 'DEF':
            obj, exp = tree[1], refactor_tree(tree[3])
            if obj[0] == 'OBJ':
                return 'DEF', obj[1], exp
            else:
                return 'DEF', obj[1], (refactor_tree(obj[3]), exp)

        if tree[0] == 'GROUP':
            tree = tree[2]

        if tree[0] == 'MACRO':  # pop < and >
            tree.pop(2)
            tree.pop(3)
        elif tree[0] == 'EXP' and len(tree) > 2:  # pop |
            tree.pop(2)

        return tree

    def flatten_nested(tree):
        if tree[-1][0] == tree[0]:  # flatten the nested list
            while tree[-1][0] == tree[0]:
                last = eliminate(tree.pop(-1))
                tree.extend(last[1:])
        return tree

    def compress_tags(tree):
        if len(tree) == 2:  # join nested tags
            rest = refactor_tree(tree[1])
            if type(rest) is tuple:
                return [tree[0]+':'+rest[0], *rest[1:]]
        return tree

    if type(tree) is not list:
        return tree
    
    tree = eliminate(tree)
    tree = flatten_nested(tree)
    tree = compress_tags(tree)
    return tuple(map(refactor_tree, tree))


def advanced_parse(type_, text, grammar):

    tokenizer = grammar[' '] + '(%s)'

    # @trace
    @memo  # avoid parsing the same atom again
    def parse(syntax, text):
        tags, body = syntax[0].split(':'), syntax[1:]
        tag = tags[-1]
        tree, rem = [], text
        if tag == 'EXP':
            for alt in body:
                tree, rem = parse(alt, text)
                if rem is not None: break
            return None, None
        elif tag in ('ALT', 'ITEMS', 'VARS'):
            for item in body:
                tr, rem = parse(item, rem)
                if rem is None: return None, None
                if tr: tree.append(tr)
        elif tag == 'OBJ':
            return parse(grammar[body[0]], text)
        elif tag in ('STR', 'CHARSET', 'REGEX'):
            regex = body[0]
            if tag != 'CHARSET': regex = regex[1:-1]
            m = re.match(tokenizer % regex, text)
            if not m: return None, None
            else: return m[1], text[m.end():]
        elif tag == 'ITEM_OP':
            item, op = body
            op = op[1]
            if op == '?':
                _tree, _rem = parse(item, text)
                if _rem is not None:
                    tree, rem = _tree, _rem
            else:  # '*' or '+'
                reps = 0
                while True:
                    tr, _rem = parse(item, rem)
                    if _rem is None: break
                    tree.append(tr)
                    rem = _rem
                if op == '+' and reps == 0:
                    return None, None                    
        elif tag == 'MACRO':
            return apply_macro(body, text)
        else:
            raise TypeError('unrecognized type: %s' % tag)
        return [tag]+tree, rem

    return parse(grammar[type_], text)

@memo
def apply_macro(tree, text):
    pass


trace.ignore.append((None, None))
# trace = disabled


grammar = advanced_grammar(Grammar)


def parse(exp):
    return advanced_parse('STATEMENT', exp, grammar)


## tests ##

def show_grammar():
    for obj, exp in grammar.items(): 
        print(f'{obj}:\n{exp}')
    print()

def test_grammar():
    expected_grammar = {' ': '\\s*', 'STATEMENT': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ASSIGN'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'CONF'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'CMD'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LOAD'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'IMPORT'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), ('ITEM_OP:ITEM:ATOM:OBJ', 'COMMENT')), 'EXP': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'IF_ELSE'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'WHEN'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LOCAL'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LAMBDA'), ('ALT:ITEM_OP:ITEM:MACRO', '%SEQ', ('ITEMS', ('ITEM:ATOM:OBJ', 'BIN_OP'), ('ITEM:ATOM:OBJ', 'ITEM_OP')))), 'ASSIGN': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'FUNFORM')), ('ITEM_OP:ITEM:ATOM:STR', '":="'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'CONF': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"conf"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP', ('ITEM:ATOM:REGEX', '/\\d+|on|off/'), ('OP', '?'))), 'CMD': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:STR', '"ENV"'), ('ALT', ('ITEM_OP:ITEM:ATOM:STR', '"del"'), ('ITEM_OP', ('ITEM:ATOM:OBJ', 'NAME'), ('OP', '+')))), 'LOAD': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"load"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP', ('ITEM:ATOM:REGEX', '/-[tvp]/'), ('OP', '*'))), 'IMPORT': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"import"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP', ('ITEM:ATOM:REGEX', '/-[tvp]/'), ('OP', '*'))), 'COMMENT': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"#"'), ('ITEM_OP:ITEM:ATOM:REGEX', '/.*/')), 'NAME': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'LETTER'), ('ITEM_OP', ('ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LETTER'), ('ALT:ITEM_OP:ITEM:ATOM:CHARSET', '[\\d_]')), ('OP', '*')), ('ITEM_OP', ('ITEM:ATOM:STR', '"?"'), ('OP', '?'))), 'LETTER': ('EXP:ALT:ITEM_OP:ITEM:ATOM:CHARSET', '[a-zA-Z\\u0374-\\u03FF]'), 'FUNFORM': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP:ITEM:ATOM:OBJ', 'ARGS')), 'ARGS': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:STR', '"("'), ('ITEM:ATOM:STR', '")"'), ('ITEM:ATOM:STR', '","'), ('ITEM:ATOM:OBJ', 'NAME'))), 'FUNC': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP:ITEM:ATOM:STR', '"("'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXPS'), ('ITEM_OP:ITEM:ATOM:STR', '")"')), 'EXPS': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%SEQ', ('ITEMS', ('ITEM:ATOM:STR', '","'), ('ITEM:ATOM:OBJ', 'EXP'))), 'IF_ELSE': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP'), ('ITEM_OP:ITEM:ATOM:STR', '"if"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP'), ('ITEM_OP:ITEM:ATOM:STR', '"else"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'WHEN': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"when"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'CASES'), ('ITEM_OP:ITEM:ATOM:STR', '";"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'CASES': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:STR', '"("'), ('ITEM:ATOM:STR', '")"'), ('ITEM:ATOM:STR', '";"'), ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP'), ('ITEM_OP:ITEM:ATOM:STR', '","'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')))), 'LOCAL': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'BINDS'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'BIND')), ('ITEM_OP:ITEM:ATOM:STR', '"->"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'BINDS': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:STR', '"("'), ('ITEM:ATOM:STR', '")"'), ('ITEM:ATOM:STR', '","'), ('ITEM:ATOM:OBJ', 'BIND'))), 'BIND': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ARGLIST'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME')), ('ITEM_OP:ITEM:ATOM:STR', '"="'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'ARGLIST': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:STR', '"["'), ('ITEM:ATOM:STR', '"]"'), ('ITEM:ATOM:STR', '","'), ('ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ARGLIST')))), 'LAMBDA': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ARGS'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME')), ('ITEM_OP:ITEM:ATOM:STR', '"->"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'ITEM_OP': ('EXP', ('ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'UNL_OP'), ('ITEM_OP:ITEM:ATOM:OBJ', 'ITEM')), ('ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'ITEM'), ('ITEM_OP:ITEM:ATOM:OBJ', 'UNR_OP')), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ITEM')), 'ITEM': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'GROUP'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'FUNC'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LIST'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ATOM')), 'LIST': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"["'), ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:MACRO', '%SEQ', ('ITEMS', ('ITEM:ATOM:STR', '";"'), ('ITEM:ATOM:OBJ', 'EXPS'))), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'EXPS')), ('ITEM_OP:ITEM:ATOM:STR', '"]"')), 'ATOM': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NUM'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'SYMBOL'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ANS')), 'SYMBOL': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"\'"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME')), 'ANS': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/_(\\d+|_*)/'), 'NUM': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'COMPLEX'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'FLOAT'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'INT'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'BIN_NUM'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'HEX_NUM')), 'COMPLEX': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'FLOAT'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[+-]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'FLOAT'), ('ITEM_OP:ITEM:ATOM:STR', '"I"')), 'FLOAT': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'INT'), ('ITEM_OP:ITEM:ATOM:REGEX', '/\\.\\d*/'), ('ITEM_OP', ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:CHARSET', '[eE]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'INT')), ('OP', '?'))), 'INT': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/-?\\d+/'), 'BIN_NUM': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/0b[01]+/'), 'HEX_NUM': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/0x[0-9a-fA-F]+/'), '%LST': (('VARS', ('VAR', '$OPN'), ('VAR', '$CLS'), ('VAR', '$SEP'), ('VAR', '$ITM')), ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:VAR', '$OPN'), ('ITEM_OP', ('ITEM:ATOM:VAR', '$ITM'), ('OP', '?')), ('ITEM_OP', ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:VAR', '$SEP'), ('ITEM_OP:ITEM:ATOM:VAR', '$ITM')), ('OP', '*')), ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:VAR', '$CLS'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '""')))), '%SEQ': (('VARS', ('VAR', '$SEP'), ('VAR', '$ITM')), ('EXP:ALT', ('ITEM_OP', ('ITEM:ATOM:VAR', '$ITM'), ('OP', '?')), ('ITEM_OP', ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:VAR', '$SEP'), ('ITEM_OP:ITEM:ATOM:VAR', '$ITM')), ('OP', '*'))))}

    for obj in grammar:
        if grammar[obj] != expected_grammar[obj]:
            print('grammar changed!')
            print('From:', expected_grammar[obj])
            print('To:', grammar[obj], end='\n\n')
            raise AssertionError
    print('grammar unchanged', end='\n\n')

def simple_parse_egs():
    print(parse('x := 3 + 5'))
    print(parse('x * (y+2)'))
    print(parse('f(x):=1/x'))
    print(parse('[x+f(f(3*6)^2), [2, 6], g(3, 6)]'))

def test():
    show_grammar()
    test_grammar()
    simple_parse_egs()

test()