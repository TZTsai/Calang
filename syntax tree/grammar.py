from mydecorators import memo, disabled
from myutils import trace
import re
from __builtins import binary_ops, unary_l_ops, unary_r_ops


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
PARAMS  := %LST<[(] [)] [,] NAME>

CONF    := "conf" NAME /\d+|on|off/ ?
CMD     := "ENV" | "del" NAME +
LOAD    := "load" NAME /-[tvp]/ *
IMPORT  := "import" NAME /-[tvp]/ *
COMMENT := [#] /.*/

EXP     := LOCAL | LAMBDA | IF_ELSE | OP_SEQ
IF_ELSE := OP_SEQ "if" OP_SEQ "else" EXP
OP_SEQ  := %SEQ<BIN_OP ITEM_OP>
LOCAL   := ( BINDS | BIND ) "->" EXP
BINDS   := %LST<[(] [)] [,] BIND>
BIND    := ( ARGLIST | NAME ) [:] EXP
ARGLIST := %LST<"[" "]" [,] ( NAME | ARGLIST )>
LAMBDA  := ( PARAMS | NAME ) "->" EXP

ITEM_OP := UNL_OP ITEM | ITEM UNR_OP | ITEM
ITEM    := GROUP | WHEN | FUNC | LIST | ATOM
GROUP   := [(] EXP [)]
WHEN    := "when" CASES [;] EXP
CASES   := %LST<[(] [)] [;] ( EXP [,] EXP )>
FUNC    := NAME [(] EXPS [)]
EXPS    := %SEQ<[,] EXP>
LIST    := "[" ( %SEQ<[;] EXPS> | EXPS ) "]"
ATOM    := NUM | NAME | SYMBOL | ANS

SYMBOL  := ['] NAME
ANS     := /_(\d+|_*)/

NUM     := COMPLEX | FLOAT | INT | BIN_NUM | HEX_NUM
COMPLEX := FLOAT [+-] FLOAT [I]
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
    for rule in rules:
        tree, rem = simple_parse('DEF', rule, metagrammar)
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


grammar = calc_grammar(Grammar)


def calc_parse(type_, text, grammar=grammar):

    whitespace = grammar[' ']
    tokenizer = whitespace + '(%s)'

    @trace
    @memo  # avoid parsing the same atom again
    def parse(syntax, text, replace=None):
        tags, body = syntax[0].split(':'), syntax[1:]
        tag = tags[-1]
        if tag == 'EXP':
            for alt in body:
                tree, rem = parse(alt, text, replace)
                if rem is not None: return tree, rem
            return None, None
        elif tag in ('ALT', 'ITEMS', 'VARS'):
            tree, rem = [], text
            for item in body:
                tr, rem = parse(item, rem, replace)
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
            tree, rem = parse(grammar[obj], text, replace)
            if rem is None:
                return None, None
            # add the tag
            if type(tree) is str:
                return [obj, tree], rem
            if len(tree) > 1 and type(tree[0]) is str:
                tree[0] = obj + ':' + tree[0]
            elif len(tree) > 0:
                tree = [obj] + tree
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
                tr, _rem = parse(item, rem, replace)
                if _rem is None: break
                if tr: tree.append(tr)
                rem = _rem
            if op == '+' and rep == 0:
                return None, None
            if len(tree) == 1: tree = tree[0]
            return tree, rem
        elif tag == 'MACRO':
            return apply_macro(body, text)
        elif tag == 'VAR':
            try: syntax = dict(replace)[body[0]]
            except: return None, None
            return parse(syntax, text, replace)
        else:
            raise TypeError('unrecognized type: %s' % tag)

    @memo
    def apply_macro(tree, text):
        name, args = tree
        syntax = grammar[name]
        pars, body = syntax
        assert pars[0] == 'VARS' and args[0] == 'ITEMS'
        pars, args = pars[1:], args[1:] # remove tags
        pars = [p[1] for p in pars]     # only keep param names
        if len(pars) != len(args):
            raise TypeError('macro arity mismatch')
        replace = tuple(zip(pars, args))
        return parse(body, text, replace)

    return parse(grammar[type_], text)


trace.ignore.append((None, None))
trace = disabled


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

def test_grammar():
    expected = {' ': '\\s*', 'STATEMENT': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ASSIGN'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'CONF'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'CMD'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LOAD'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'IMPORT'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), ('ITEM_OP', ('ITEM:ATOM:OBJ', 'COMMENT'), ('OP', '?'))), 'ASSIGN': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'FUNFORM')), ('ITEM_OP:ITEM:ATOM:STR', '":="'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'NAME': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/[a-zA-Z\\u0374-\\u03FF][a-zA-Z\\u0374-\\u03FF\\d_]*[?]?/'), 'FUNFORM': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP:ITEM:ATOM:OBJ', 'PARAMS')), 'PARAMS': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:CHARSET', '[(]'), ('ITEM:ATOM:CHARSET', '[)]'), ('ITEM:ATOM:CHARSET', '[,]'), ('ITEM:ATOM:OBJ', 'NAME'))), 'CONF': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"conf"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP', ('ITEM:ATOM:REGEX', '/\\d+|on|off/'), ('OP', '?'))), 'CMD': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:STR', '"ENV"'), ('ALT', ('ITEM_OP:ITEM:ATOM:STR', '"del"'), ('ITEM_OP', ('ITEM:ATOM:OBJ', 'NAME'), ('OP', '+')))), 'LOAD': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"load"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP', ('ITEM:ATOM:REGEX', '/-[tvp]/'), ('OP', '*'))), 'IMPORT': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"import"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP', ('ITEM:ATOM:REGEX', '/-[tvp]/'), ('OP', '*'))), 'COMMENT': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:CHARSET', '[#]'), ('ITEM_OP:ITEM:ATOM:REGEX', '/.*/')), 'EXP': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LOCAL'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LAMBDA'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'IF_ELSE'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'OP_SEQ')), 'IF_ELSE': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'OP_SEQ'), ('ITEM_OP:ITEM:ATOM:STR', '"if"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'OP_SEQ'), ('ITEM_OP:ITEM:ATOM:STR', '"else"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'OP_SEQ': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%SEQ', ('ITEMS', ('ITEM:ATOM:OBJ', 'BIN_OP'), ('ITEM:ATOM:OBJ', 'ITEM_OP'))), 'LOCAL': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'BINDS'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'BIND')), ('ITEM_OP:ITEM:ATOM:STR', '"->"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'BINDS': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:CHARSET', '[(]'), ('ITEM:ATOM:CHARSET', '[)]'), ('ITEM:ATOM:CHARSET', '[,]'), ('ITEM:ATOM:OBJ', 'BIND'))), 'BIND': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ARGLIST'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME')), ('ITEM_OP:ITEM:ATOM:CHARSET', '[:]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'ARGLIST': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:STR', '"["'), ('ITEM:ATOM:STR', '"]"'), ('ITEM:ATOM:CHARSET', '[,]'), ('ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ARGLIST')))), 'LAMBDA': ('EXP:ALT', ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'PARAMS'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME')), ('ITEM_OP:ITEM:ATOM:STR', '"->"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'ITEM_OP': ('EXP', ('ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'UNL_OP'), ('ITEM_OP:ITEM:ATOM:OBJ', 'ITEM')), ('ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'ITEM'), ('ITEM_OP:ITEM:ATOM:OBJ', 'UNR_OP')), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ITEM')), 'ITEM': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'GROUP'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'WHEN'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'FUNC'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'LIST'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ATOM')), 'GROUP': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:CHARSET', '[(]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[)]')), 'WHEN': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"when"'), ('ITEM_OP:ITEM:ATOM:OBJ', 'CASES'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[;]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')), 'CASES': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%LST', ('ITEMS', ('ITEM:ATOM:CHARSET', '[(]'), ('ITEM:ATOM:CHARSET', '[)]'), ('ITEM:ATOM:CHARSET', '[;]'), ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[,]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXP')))), 'FUNC': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[(]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'EXPS'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[)]')), 'EXPS': ('EXP:ALT:ITEM_OP:ITEM:MACRO', '%SEQ', ('ITEMS', ('ITEM:ATOM:CHARSET', '[,]'), ('ITEM:ATOM:OBJ', 'EXP'))), 'LIST': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:STR', '"["'), ('ITEM_OP:ITEM:EXP', ('ALT:ITEM_OP:ITEM:MACRO', '%SEQ', ('ITEMS', ('ITEM:ATOM:CHARSET', '[;]'), ('ITEM:ATOM:OBJ', 'EXPS'))), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'EXPS')), ('ITEM_OP:ITEM:ATOM:STR', '"]"')), 'ATOM': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NUM'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'NAME'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'SYMBOL'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'ANS')), 'SYMBOL': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:CHARSET', "[']"), ('ITEM_OP:ITEM:ATOM:OBJ', 'NAME')), 'ANS': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/_(\\d+|_*)/'), 'NUM': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'COMPLEX'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'FLOAT'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'INT'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'BIN_NUM'), ('ALT:ITEM_OP:ITEM:ATOM:OBJ', 'HEX_NUM')), 'COMPLEX': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'FLOAT'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[+-]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'FLOAT'), ('ITEM_OP:ITEM:ATOM:CHARSET', '[I]')), 'FLOAT': ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:OBJ', 'INT'), ('ITEM_OP:ITEM:ATOM:REGEX', '/\\.\\d*/'), ('ITEM_OP', ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:CHARSET', '[eE]'), ('ITEM_OP:ITEM:ATOM:OBJ', 'INT')), ('OP', '?'))), 'INT': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/-?\\d+/'), 'BIN_NUM': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/0b[01]+/'), 'HEX_NUM': ('EXP:ALT:ITEM_OP:ITEM:ATOM:REGEX', '/0x[0-9a-fA-F]+/'), '%LST': (('VARS', ('VAR', '$OPN'), ('VAR', '$CLS'), ('VAR', '$SEP'), ('VAR', '$ITM')), ('EXP:ALT', ('ITEM_OP:ITEM:ATOM:VAR', '$OPN'), ('ITEM_OP', ('ITEM:ATOM:VAR', '$ITM'), ('OP', '?')), ('ITEM_OP', ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:VAR', '$SEP'), ('ITEM_OP:ITEM:ATOM:VAR', '$ITM')), ('OP', '*')), ('ITEM_OP:ITEM:ATOM:VAR', '$CLS'))), '%SEQ': (('VARS', ('VAR', '$SEP'), ('VAR', '$ITM')), ('EXP:ALT', ('ITEM_OP', ('ITEM:ATOM:VAR', '$ITM'), ('OP', '?')), ('ITEM_OP', ('ITEM:EXP:ALT', ('ITEM_OP:ITEM:ATOM:VAR', '$SEP'), ('ITEM_OP:ITEM:ATOM:VAR', '$ITM')), ('OP', '*')))), 'BIN_OP': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:STR', '"+"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"-"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"*"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '".*"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"/"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"//"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"^"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"%"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"="'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"!="'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"<"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '">"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"<="'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '">="'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"xor"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"in"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"outof"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"~"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '".."'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"and"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"or"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"/\\"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"\\/"')), 'UNL_OP': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:STR', '"-"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"not"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"!"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"@"')), 'UNR_OP': ('EXP', ('ALT:ITEM_OP:ITEM:ATOM:STR', '"!"'), ('ALT:ITEM_OP:ITEM:ATOM:STR', '"!!"'))}
    for obj in grammar:
        if grammar[obj] != expected[obj]:
            print('grammar changed!')
            print('From:', expected[obj])
            print('To:', grammar[obj], end='\n\n')
    else: print('grammar unchanged', end='\n\n')

def simple_parse_egs():
    print(parse('3'))
    print(parse('x'))
    print(parse('x := 5'))
    print(parse('x := 3 * (4+5)'))
    print(parse('x * (y+2)'))
    # print(parse('f(x):=1/x'))
    # print(parse('[x+f(f(3*6)^2), [2, 6], g(3, 6)]'))

def bad_syntax_egs():
    print(parse('(3'))
    print(parse('[3, f(4])'))

def test():
    # show_grammar(1)
    test_grammar()
    simple_parse_egs()

test()