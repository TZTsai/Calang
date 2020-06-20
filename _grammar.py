from mydecorators import memo, disabled
from myutils import trace, log
from pprint import pprint
from json import dump
import re
from _builtins import binary_ops, unary_l_ops, unary_r_ops


# log.out = open('log.yaml', 'w', encoding='utf8')
trace = disabled


def split(text: str, sep=None, maxsplit=-1):
    return [t.strip() for t in text.split(sep, maxsplit) if t]


MetaGrammar = split(r"""
DEF     := PAR := EXP | OBJ := EXP | MACRO := EXP
OBJ     := [A-Z][A-Z_:]*
PAR     := _[A-Z_:]+
MACRO   := %[A-Z_]+ < VARS > | %[A-Z_]+ < ITEMS >
VARS    := VAR VARS | VAR
VAR     := \$[A-Z_]+
EXP     := ALT [|] EXP | ALT
ALT     := ITEM_OP ALT | ITEM_OP
ITEM_OP := ITEM OP | ITEM
OP      := [*?!/+-](?=\s|$)
ITEM    := GROUP | MACRO | ATOM
ITEMS   := ITEM ITEMS | ITEM
GROUP   := [(] EXP [)]
ATOM    := PAR | OBJ | STR | RE | CHARS | VAR | MARK
STR     := ".*?"
RE      := /.*?/
CHARS   := \[.*?\]
MARK    := [^>|)\s]\S*
""", '\n')

###  COMMENTS ON METAGRAMMAR  ###
# OBJ:      OBJ is a tag of the syntax tree to identify its type
#           it consists of A-Z and _
#           Optionally, it can have a suffix beginning with : , in which case the
#           parser should change the tag of the matched tree into that after : ,
#           very useful for the evaluator to determine its way of eval
# PAR:      Similar to OBJ but begins with _ . The tree it matches will not be 
#           tagged, but merged into the OBJ at its upper level instead
# OP:       * for 0 or more matches, + for 1 or more, ? for 0 or 1, 
#           - for 1 match but it will not be included in the result,
#           ! for prechecking and forbidding 1 match
#           / for no space between its prev and its next items
#           if more than one items are matched, merge them into the seq
# MARK:     a token in the grammar that will be matched but not included in the result
#           be cautious of conflicts with other symbols in MetaGrammar
# MACRO:    used for sub_macro; will not exist in the processed grammar


GrammarStr = open('grammar.txt', 'r').read()
GrammarStr = GrammarStr.split('#####', 1)[0]   # remove the comment below
Grammar = split(GrammarStr, '\n')
# add syntax for operations
bin_op, unl_op, unr_op = ['"' + '" | "'.join(sorted(ops, reverse=1, key=len)) + '"' 
                          for ops in (binary_ops, unary_l_ops, unary_r_ops)]
Grammar.append('BOP := ' + bin_op)
Grammar.append('LOP := ' + unl_op)
Grammar.append('ROP := ' + unr_op)


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
            if not m: return (None, None)
            else: return (m[1], text[m.end():])

    return parse_atom(type_, ' '+text)


def calc_grammar(rules, whitespace=r'\s*'):
    G = {' ': whitespace}
    M = {}
    for rule in rules:
        rule = rule.split('##', 1)[0].strip()
        if not rule: continue
        tree, rem = parse_grammar('DEF', rule)
        assert tree[0] == 'DEF' and not rem
        name, body = tree[1][1], refactor_tree(tree[3])
        if name[0] == '%': 
            pars = tree[1][3]
            flatten_nested(pars)
            M[name] = [pars, body]  # MACRO
        else: G[name] = body
    post_process(G, M)
    return G


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

@trace
def simplify_tag(tree):  # also convert the tree into a pure tuple
    if type(tree) is list:
        while len(tree) == 2 and type(tree[1]) is list and tree[0] != 'ITEMS':
            tree = tree[1]
        return tuple(simplify_tag(t) for t in tree)
    return tree

def refactor_tree(tree: list):
    prune(tree)
    flatten_nested(tree)
    return simplify_tag(tree)


# @trace
def post_process(grammar, macros):

    def apply_macro(tree):
        name, args = tree[1], tree[3]
        pars, body = macros[name]
        args = args[1:]
        pars = [p[1] for p in pars[1:]]
        if len(pars) != len(args):
            raise SyntaxError(f'macro arity mismatch when applying {name}')
        bindings = dict(zip(pars, args))
        body = substitute(body, bindings)
        return proc_tree(body)
        
    def substitute(tree, bindings):
        if type(tree) is not tuple:
            return tree
        elif tree[0] == 'VAR':
            var = tree[1]
            try: return bindings[var]
            except KeyError: raise SyntaxError('unbound macro var: '+var)
        else:
            return tuple(substitute(t, bindings) for t in tree)

    def proc_tree(tree):
        if type(tree) is not tuple:
            return tree
        elif tree[0] == 'MACRO':
            return apply_macro(tree)
        elif tree[0] in ('OBJ', 'PAR'):
            tag = tree[1].split(':')[0]
            if tag not in grammar:
                return 'MARK', tree[1]
            else:
                return tree
        else:
            return tuple(proc_tree(t) for t in tree)

    for obj, tree in grammar.items():
        grammar[obj] = proc_tree(tree)


## tests
def check(f, args, expected):
    actual = f(*args)
    if actual != expected:
        rec_comp(expected, actual)
        raise AssertionError(f'Wrong Answer of {f.__name__}{tuple(args)}\n' +
                             f'Expected: {expected}\n' +
                             f'Actual: {actual}\n')

def rec_comp(l1, l2):
    if type(l1) not in (tuple, list, dict):
        if l1 != l2: print(l1, l2)
    elif len(l1) != len(l2):
        print(l1, l2)
    else:
        for i1, i2 in zip(l1, l2):
            if type(l1) is dict: rec_comp(l1[i1], l2[i2])
            else: rec_comp(i1, i2)

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
        ('DEF', 'LC := ( BLIST | BIND * ) ? "=>" EXP'),
        (['DEF', ['OBJ', 'LC'], ':=', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['GROUP', '(', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BLIST']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BIND']]], ['OP', '*']]]]], ')']], ['OP', '?']], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['STR', '"=>"']]]], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'EXP']]]]]]]]], ''))
        check(parse_grammar,
        ('DEF', '%M < $A > := $A $A +'),
        (['DEF', ['MACRO', '%M', '<', ['VARS', ['VAR', '$A']], '>'], ':=', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['VAR', '$A']]]], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['VAR', '$A']]], ['OP', '+']]]]]], ''))

    def test_refactor():
        check(refactor_tree, 
        [['DEF', ['OBJ', 'EXP'], ':=', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'LOCAL']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'LAMBDA']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'IF_ELSE']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'OP_SEQ']]]]]]]]]]], 
        ('DEF', ('OBJ', 'EXP'), ':=', ('EXP', ('OBJ', 'LOCAL'), ('OBJ', 'LAMBDA'), ('OBJ', 'IF_ELSE'), ('OBJ', 'OP_SEQ'))))
        check(refactor_tree, 
        [['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['GROUP', '(', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BLIST']]]]], '|', ['EXP', ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'BIND']]], ['OP', '*']]]]], ')']], ['OP', '?']], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['STR', '"=>"']]]], ['ALT', ['ITEM_OP', ['ITEM', ['ATOM', ['OBJ', 'EXP']]]]]]]]],
        ('ALT', ('ITEM_OP', ('EXP', ('OBJ', 'BLIST'), ('ITEM_OP', ('OBJ', 'BIND'), ('OP', '*'))), ('OP', '?')), ('STR', '"=>"'), ('OBJ', 'EXP')))

    def test_macro():    
        rules = ['LIST    := %LST < "[" "]" ; %SEQ < , /.*/ > >',
                '%LST < $OPN $CLS $SEP $ITM > := $OPN $CLS | $OPN $ITM ( $SEP $ITM ) * $CLS',
                '%SEQ < $SEP $ITM >           := $ITM ? ( $SEP $ITM ) *']
        check(calc_grammar, [rules],
              {' ': '\\s*', 'LIST': ('EXP', ('ALT', ('STR', '"["'), ('STR', '"]"')), ('ALT', ('STR', '"["'), ('ALT', ('ITEM_OP', ('RE', '/.*/'), ('OP', '?')), ('ITEM_OP', ('ALT', ('MARK', ','), ('RE', '/.*/')), ('OP', '*'))), ('ITEM_OP', ('ALT', ('MARK', ';'), ('ALT', ('ITEM_OP', ('RE', '/.*/'), ('OP', '?')), ('ITEM_OP', ('ALT', ('MARK', ','), ('RE', '/.*/')), ('OP', '*')))), ('OP', '*')), ('STR', '"]"')))})

    test_parse()
    test_refactor()
    test_macro()


grammar = calc_grammar(Grammar)
dump(grammar, open('grammar.json', 'w', encoding='utf8'), indent=2)

if __name__ == "__main__":
    test_grammar()
    pprint(grammar)