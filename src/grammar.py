from pprint import pprint
import re
import json
from builtin import op_symbols
from utils.deco import memo, trace, disabled
from utils.debug import check_record

trace = disabled


def split(text: str, sep=None, maxsplit=-1):
    return [t.strip() for t in text.split(sep, maxsplit) if t]


MetaGrammar = split(r"""
DEF     := PAR := EXP | OBJ := EXP | MACRO := EXP
OBJ     := [A-Z][A-Z_:]*
PAR     := _[A-Z_]+
MACRO   := @[A-Z_]+ VARS | @[A-Z_]+ ITEMS
VARS    := VAR VARS | VAR
VAR     := \$[A-Z_]+
EXP     := ALT [|] EXP | ALT
ALT     := ITEM_OP ALT | ITEM_OP
ITEM_OP := ITEM OP | ITEM
OP      := [*?!/+-](?=\s|$)
ITEM    := GROUP | MACRO | ATOM
ITEMS   := ITEM ITEMS | ITEM
GROUP   := [(] EXP [)]
ATOM    := PAR | OBJ | STR | RE | VAR | MARK
STR     := ".*?"
RE      := /.*?/
MARK    := [^>|)\s]\S*
""", '\n')
###  COMMENTS ON METAGRAMMAR  ###
# OBJ:      OBJ is a tag of the syntax tree to identify its type, 
#           only consisting of 'A-Z' and '_'.
#           Optionally, it can have a suffix beginning with ':' , in which case the
#           parse should change the tag of the matched tree into that after ':',
#           very useful for the evaluator to modify its way of evaluation
# PAR:      Similar to OBJ but begins with _ . The tree it matches will not be 
#           tagged, but instead merged into the OBJ at its upper level
# OP:       '*' for 0 or more matches, '+' for 1 or more, '?' for 0 or 1, 
#           '-' for 1 match but it will not be included in the result,
#           '!' for prechecking and forbidding 1 match
#           '/' for no space between its prev and its next items
#           if more than one items are matched, merge them into the seq
# MARK:     a token in the grammar that will be matched but not included in the result
#           be cautious of conflicts with other symbols in MetaGrammar
# MACRO:    a macro will be substituted by its evaluated expression 


Grammar = open('grammar.txt', 'r').read().splitlines()
Semantics = open('semantics.txt', 'r').read().splitlines()

# add the grammar rule of operators
ops = sorted(op_symbols, reverse=1, key=len)
Grammar.append('OP := "%s"' % '" | "'.join(ops))


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
            if not m: return (None, None)
            else: return (m[1], text[m.end():])

    return parse_atom(type_, ' '+text)


def calc_grammar(rules, whitespace=r'[ \n]*'):
    G = {' ': whitespace}
    M = {}
    for rule in rules:
        rule = rule.split('##', 1)[0].strip()
        if not rule: continue
        tree, rem = parse_grammar('DEF', rule)
        assert tree[0] == 'DEF' and not rem
        name, body = tree[1][1], refactor_tree(tree[3])
        if name[0] == '@': 
            pars = tree[1][2]
            flatten_nested(pars)
            M[name] = [pars, body]  # MACRO
        else: G[name] = body
    post_process(G, M)
    return G


def prune(tree):
    if type(tree) is list:
        if tree[0] == 'GROUP':
            tree[:] = tree[2]
        if tree[0] == 'EXP' and len(tree) > 2:  # pop '|'
            tree.pop(2)
        elif tree[0] in ('STR', 'RE'):
            tree[1] = tree[1][1:-1]
        for t in tree: prune(t)

def flatten_nested(tree):
    if type(tree) is list:
        while tree[-1][0] == tree[0]:
            last = tree.pop(-1)
            tree.extend(last[1:])
        for t in tree: flatten_nested(t)            

# @trace
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


def post_process(grammar, macros):

    def apply_macro(tree):
        name, args = tree[1], tree[2]
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
            tag = tree[1].split(':')[-1]
            if tag not in grammar:
                return 'MARK', tree[1]
            else:
                return tree
        else:
            return tuple(proc_tree(t) for t in tree)

    for obj, tree in grammar.items():
        grammar[obj] = proc_tree(tree)


grammar = calc_grammar(Grammar)
semantics = simple_grammar(Semantics)
del semantics[' ']

json.dump(grammar, open('utils/grammar.json', 'w'), indent=2)
json.dump(semantics, open('utils/semantics.json', 'w'), indent=2)


if __name__ == "__main__":
    pprint(grammar)
    for func in [parse_grammar, calc_grammar, refactor_tree]:
        check_record('utils/syntax_tests.json', func)
