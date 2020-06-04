from mydecorators import memo, disabled
from myutils import trace, log
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
OP      := [*?+]
ITEM    := GROUP | MACRO | ATOM
ITEMS   := ITEM ITEMS | ITEM
GROUP   := [(] EXP [)]
ATOM    := OBJ | STR | REGEX | CHARSET | VAR
STR     := ".*?"
REGEX   := /.*?/
CHARSET := \[.*?\]
""", '\n')


Grammar = split(r"""
STATEMENT   := ( ASSIGN | CONF | CMD | LOAD | IMPORT | EXP ) COMMENT ?

ASSIGN  := ( NAME | FUNFORM ) ":=" EXP
NAME    := /[a-zA-Z\u0374-\u03FF][a-zA-Z\u0374-\u03FF\d_]*[?]?/
FUNFORM := NAME PARAMS
PARAMS  := %LST<"(" ")" "," NAME>

CONF    := "conf" NAME /\d+|on|off/ ?
CMD     := "ENV" | "del" NAME +
LOAD    := "load" NAME /-[tvp]/ *
IMPORT  := "import" NAME /-[tvp]/ *
COMMENT := [#] /.*/

EXP     := LOCAL | LAMBDA | IF_ELSE | OP_SEQ
IF_ELSE := OP_SEQ "if" OP_SEQ "else" EXP
OP_SEQ  := %SEQ<BIN_OP ITEM_OP>
LOCAL   := ( BINDS | BIND ) "->" EXP
BINDS   := %LST<"(" ")" "," BIND>
BIND    := ( ARGLIST | NAME ) ":" EXP
ARGLIST := %LST<"[" "]" "," ( NAME | ARGLIST )>
LAMBDA  := ( PARAMS | NAME ) "->" EXP

ITEM_OP := UNL_OP ? ITEM UNR_OP ?
ITEM    := GROUP | WHEN | FUNC | LIST | ATOM
GROUP   := "(" EXP ")"
WHEN    := "when" CASES ";" EXP
CASES   := %LST<"(" ")" ";" ( EXP "," EXP )>
FUNC    := NAME "(" EXPS ")"
EXPS    := %SEQ<"," EXP>
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

%LST<$OPN $CLS $SEP $ITM>   := $OPN $ITM ? ( $SEP $ITM ) * $CLS
%SEQ<$SEP $ITM>             := $ITM ? ( $SEP $ITM ) *
""", '\n')


# add syntax for operations
bin_op, unl_op, unr_op = ['"' + '" | "'.join(ops) + '"' 
                          for ops in (binary_ops, unary_l_ops, unary_r_ops)]
Grammar.append('BIN_OP  := ' + bin_op)
Grammar.append('UNL_OP  := ' + unl_op)
Grammar.append('UNR_OP  := ' + unr_op)


def simple_grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    for line in rules:
        obj, exp = split(line, ':=', 1)
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


def calc_grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    M = {}
    for rule in rules:
        tree, rem = simple_parse('DEF', rule, metagrammar)
        assert tree[0] == 'DEF' and not rem
        name, body = tree[1][1], tree[3]
        if name[0] == '%': M[name] = [tree[1][3], body]  # MACRO
        else: G[name] = body
    for obj in G: G[obj] = refactor_tree(G[obj], M)
    return G


# @trace
@memo
def refactor_tree(tree: list, macros, bindings=None):

    def replace(tree):
        if tree[0] == 'GROUP':
            tree = tree[2]

        if tree[0] == 'MACRO':
            name, args = tree[1], tree[3]
            pars, body = macros[name]
            args = [p[1] for p in flatten_nested(args)[1:]]
            pars = [p[1] for p in flatten_nested(pars)[1:]]
            return refactor_tree(body, macros, dict(zip(pars, args)))
        elif tree[0] == 'EXP' and len(tree) > 2:  # pop |
            tree.pop(2)
        elif tree[0] == 'VAR':
            var = tree[1]
            try: return bindings[var]
            except: raise SyntaxError('failed to substitute the macro')

        return tree

    def flatten_nested(tree):
        if tree[-1][0] == tree[0]:  # flatten the nested list
            while tree[-1][0] == tree[0]:
                last = replace(tree.pop(-1))
                tree.extend(last[1:])
        return tree

    def simplify_tag(tree):
        if len(tree) == 2:  # join nested tags
            rest = refactor_tree(tree[1], macros, bindings)
            if type(rest) is tuple: return rest
        return tree

    if type(tree) is not list:
        return tree
    
    tree = replace(tree)
    tree = flatten_nested(tree)
    tree = simplify_tag(tree)
    return tuple(refactor_tree(t, macros, bindings) for t in tree)


grammar = calc_grammar(Grammar)

def calc_parse(type_, text, grammar=grammar):

    whitespace = grammar[' ']
    tokenizer = whitespace + '(%s)'

    @trace
    @memo  # avoid parsing the same atom again
    def parse(syntax, text):
        # if text == '': return None, None
        tag, body = syntax[0], syntax[1:]

        if tag == 'EXP':
            for alt in body:
                tree, rem = parse(alt, text)
                if rem is not None: return tree, rem
            return None, None
        elif tag in ('ALT', 'ITEMS', 'VARS'):
            tree, rem = [], text
            # this will save a lot of time
            for item in body:
                if item[0] == 'STR':
                    if item[1][1:-1] not in text:
                        return None, None
            for item in body:
                tr, rem = parse(item, rem)
                if rem is None: return None, None
                if tr:
                    if type(tr[0]) is list:
                        tree.extend(tr)
                    else:
                        tree.append(tr)
            if len(tree) == 1: tree = tree[0]
            return tree, rem
        elif tag == 'OBJ':
            obj = body[0]
            # OP objects requires a lot of search
            if '_OP' in obj and text == '': return None, None
            tree, rem = parse(grammar[obj], text)
            if rem is None: return None, None
            tree = process_tag(obj, tree)
            return tree, rem
        elif tag == 'STR':
            literal = body[0][1:-1]
            try:
                sp = re.match(whitespace, text)
                end = sp.end() + len(literal)
                assert text[sp.end():end] == literal
            except (AttributeError, AssertionError):
                return None, None
            return literal, text[end:]
        elif tag in ('CHARSET', 'REGEX'):
            pattern = body[0]
            if tag == 'REGEX': pattern = pattern[1:-1]
            m = re.match(tokenizer % pattern, text)
            if not m: return None, None
            else: return m[1], text[m.end():]
        elif tag == 'ITEM_OP':
            tree, rem = [], text
            item, [_, op] = body
            rep, maxrep = 0, 1 if op == '?' else -1
            while maxrep < 0 or rep < maxrep:
                tr, _rem = parse(item, rem)
                if _rem is None: break
                if tr: tree.append(tr)
                rem = _rem
            if op == '+' and rep == 0:
                return None, None
            if len(tree) == 1: tree = tree[0]
            return tree, rem
        else:
            raise TypeError('unrecognized type: %s' % tag)

    def process_tag(tag, tree):
        prefixes = ['NUM', 'EXP', 'ATOM']
        if type(tree) is str:
            tree = [tag, tree]
        if len(tree) > 1 and type(tree[0]) is str and tag in prefixes:
            tree[0] = tag + ':' + tree[0]
        elif len(tree) > 0:
            tree = [tag] + tree
        return tree

    return parse(grammar[type_], text)


def parse(exp):
    return calc_parse('STATEMENT', exp)



## tests ##

def show_grammar(raw=False):
    if raw: 
        print(grammar)
    else:
        for obj, exp in grammar.items(): 
            print(f'{obj}:\n{exp}')
    print()

def simple_parse_egs():
    print(parse('3'))
    print(parse('x'))
    print(parse('3+4'))
    print(parse('4!'))
    print(parse('[]'))
    # print(parse('x := 5'))
    # print(parse('x := 3 * f()'))
    # print(parse('(x*(y+2))/3'))
    # print(parse('f(x):=1/x'))
    # print(parse('[x+f(f(3*6)^2), [2, 6], g(3, 6)]'))

def bad_syntax_egs():
    print(parse('(3'))
    print(parse('[3, f(4])'))

def test():
    # show_grammar()
    simple_parse_egs()

test()