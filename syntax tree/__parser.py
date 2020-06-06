from myutils import trace, log, interact
from mydecorators import memo
from json import load
from pprint import pprint, pformat
import re
from __builtins import op_list, keywords


log.out = open('syntax tree/log.yaml', 'w')
# trace.maxdepth = -1
interact = lambda: 0


try:
    with open('syntax tree/grammar.json', 'r') as gf:
        grammar = load(gf)
except:
    from __grammar import grammar


whitespace = grammar[' ']
op_start = ''.join(set(('\\' if op[0] in '-\\' else '') + op[0] 
                       for op in op_list))
op_start = re.compile(f'{whitespace}[{op_start}]')


def lstrip(text):
    sp = re.match(whitespace, text)
    return text[sp.end():]


def calc_parse(type_, text):

    def parse_tree(syntax, text):
        tag, body = syntax[0], syntax[1:]

        if text == '' and tag != 'ITEM_OP':
            # only an item decorated by '?' or '*' can be matched to nothing
            return None, None

        if tag == 'EXP':
            return parse_alts(body, text)
        elif tag in ('ALT', 'ITEMS', 'VARS'):
            return parse_seq(body, text)
        elif tag == 'OBJ':
            return parse_obj(body[0], text)
        elif tag == 'ITEM_OP':
            item, [_, op] = body
            return parse_op(item, op, text)
        else:
            return parse_atom(tag, body[0], text)

    # @trace
    def parse_alts(alts, text):
        for alt in alts:
            tree, rem = parse_tree(alt, text)
            if rem is not None: return tree, rem
        return None, None

    # @trace
    def parse_seq(seq, text):
        tree, rem = [], text
        # precheck if the keywords are in the text
        for item in seq:
            if item[0] == 'STR':
                if item[1][1:-1] not in text:
                    return None, None
        for item in seq:
            tr, rem = parse_tree(item, rem)
            if rem is None: return None, None
            if tr:
                if tr[0] == '...':  # resulted from OP; merge the tree
                    tree.extend(tr[1])
                else:
                    tree.append(tr)
        if len(tree) == 1: tree = tree[0]
        return tree, rem

    @memo
    def parse_atom(tag, pattern, text):
        text = lstrip(text)
        if tag in ('STR', 'RE'):
            pattern = pattern[1:-1]
        if tag in ('RE', 'CHARS'):
            m = re.match(pattern, text)
            if not m: return None, None
            else: return m[0], text[m.end():]
        else:  # STR or MARK
            try:
                pre, rem = text.split(pattern, 1)
                assert not pre
            except:
                return None, None
            return pattern if tag == 'STR' else [], rem

    @trace
    @memo
    def parse_obj(obj, text):
        # prechecks to speed up parsing
        if obj[-2:] == 'OP' and op_start.match(text) is None:
            return None, None
        if obj in ('LAMBDA', 'LOCAL') and '->' not in text:
            return None, None

        tree, rem = parse_tree(grammar[obj], text)
        if obj == 'NAME' and tree in keywords:
            return None, None
        if rem is None: return None, None
        tree = process_tag(obj, tree)
        return tree, rem

    # @trace
    def parse_op(item, op, text):
        tree, rem = [], text
        rep, maxrep = 0, (1 if op in '?-' else -1)
        while maxrep < 0 or rep < maxrep:
            tr, _rem = parse_tree(item, rem)
            if _rem is None: break
            if type(tr[0]) is list: 
                tree.extend(tr)
            else:
                tree.append(tr)
            rem = _rem
            rep += 1
        if op in '+-' and rep == 0:
            return None, None
        if op == '-' or not tree:
            tree = []
        elif len(tree) == 1:
            tree = tree[0]
        else: 
            tree = ['...', tree]
        return tree, rem

    def is_tag(s):
        return s.split(':', 1)[0] in grammar

    prefixes = ['NUM', 'EXP', 'SYM', 'LST', 'OPT_PAR']
    @memo
    @trace
    def process_tag(tag, tree):
        if not tree:
            return [tag]
        elif type(tree) is str:
            return [tag, tree]
        elif type(tree[0]) is str and is_tag(tree[0]):
            if tag[-3:] == 'LST' and tag not in tree[0]:
                tree = [tag, tree]
            elif tag in prefixes:
                tree = [tag + ':' + tree[0], *tree[1:]]
            return tree
        elif len(tree) == 1:
            return process_tag(tag, tree[0])
        else:
            return [tag] + tree

    interact()
    return parse_obj('LINE', text)


def parse(exp):
    return calc_parse('LINE', exp)



## tests ##

def comp_list(l1, l2):
    if type(l1) not in (tuple, list):
        if l1 != l2: print(l1, l2)
    elif len(l1) != len(l2):
        print(l1, '\n', l2)
    else:
        for i1, i2 in zip(l1, l2):
            comp_list(i1, i2)

def check_parse(exp, expected, termin=False):
    actual = parse(exp)
    if actual != expected:
        # comp_list(expected, actual)
        print('Wrong Answer of parse(%s)\n'%exp +
                             'Expected: %s\n'%pformat(expected) +
                             'Actual: %s\n'%pformat(actual))
        if termin: raise AssertionError
        

def simple_tests():
    check_parse('3', (['EXP:NUM:INT', '3'], ''))
    check_parse('x', (['EXP:NAME', 'x'], ''))
    check_parse('1+2*3', 
                (['EXP:OP_SEQ', ['NUM:INT', '1'], ['BOP', '+'], ['NUM:INT', '2'], ['BOP', '*'], ['NUM:INT', '3']], ''))
    check_parse('3!+4', (['EXP:OP_SEQ', ['OP_ITEM', ['NUM:INT', '3'], ['ROP', '!']], 
                         ['BOP', '+'], ['NUM:INT', '4']], ''))
    check_parse('4!', (['EXP:OP_ITEM', ['NUM:INT', '4'], ['ROP', '!']], ''))
    check_parse('[]', (['EXP:LST'], ''))
    check_parse('[2]', (['EXP:LST', ['EXP:NUM:INT', '2']], ''))
    check_parse('[3, 4, 6]', (['EXP:LST', ['EXP:NUM:INT', '3'], 
                              ['EXP:NUM:INT', '4'], ['EXP:NUM:INT', '6']], ''))
    check_parse('f[]',  (['EXP:OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['LST']], ''))
    check_parse('x := 5', (['DEF', ['NAME', 'x'], ['EXP:NUM:INT', '5']], ''))
    check_parse('x := 3 * f[3, 5, 7]',
                (['DEF', ['NAME', 'x'], ['EXP:OP_SEQ', ['NUM:INT', '3'], ['BOP', '*'], ['NAME', 'f'], ['EMPTY'], ['LST', ['EXP:NUM:INT', '3'], ['EXP:NUM:INT', '5'], ['EXP:NUM:INT', '7']]]], ''))
    check_parse('f[x]:=1/x',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST', ['NAME', 'x']]], ['EXP:OP_SEQ', ['NUM:INT', '1'], ['BOP', '/'], ['NAME', 'x']]], ''))
    check_parse('f[]:=1',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST']], ['EXP:NUM:INT', '1']], ''))
    check_parse('f[x, y]:=x*y',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST', ['NAME', 'x'], ['NAME', 'y']]], ['EXP:OP_SEQ', ['NAME', 'x'], ['BOP', '*'], ['NAME', 'y']]], ''))
    check_parse('[1,2;3,4]', 
                (['EXP:LST:MAT_LST', ['ROW_LST', ['EXP:NUM:INT', '1'], ['EXP:NUM:INT', '2']], ['ROW_LST', ['EXP:NUM:INT', '3'], ['EXP:NUM:INT', '4']]], ''))
    check_parse('when(1: 2, 3: 4, 5)', 
                 (['EXP:WHEN', [['CASE', ['EXP:NUM:INT', '1'], ['EXP:NUM:INT', '2']], ['CASE', ['EXP:NUM:INT', '3'], ['EXP:NUM:INT', '4']]], ['EXP:NUM:INT', '5']], ''))
    check_parse('[x, y] -> x+y',
                (['EXP:LAMBDA', ['PAR_LST', ['NAME', 'x'], ['NAME', 'y']], ['EXP:OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('[]->1', (['EXP:LAMBDA', ['PAR_LST'], ['EXP:NUM:INT', '1']], ''))
    check_parse('[a, *r] -> [a, *r]', 
                (['EXP:LAMBDA', ['PAR_LST', ['NAME', 'a'], ['OPT_PAR:NAME', 'r']], ['EXP:LST', ['EXP:NAME', 'a'], ['LS_ITEM', '*', ['EXP:NAME', 'r']]]], ''))
    check_parse('(x:1, y:2) -> x+y',
                (['EXP:LOCAL', ['BINDS', ['BIND', ['NAME', 'x'], ['EXP:NUM:INT', '1']], ['BIND', ['NAME', 'y'], ['EXP:NUM:INT', '2']]], ['EXP:OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('[x|x in [1,2,3]]', 0)
    check_parse('ENV', (['CMD', 'ENV'], ''))
    check_parse('del x, y', (['CMD', 'del', [['NAME', 'x'], ['NAME', 'y']]], ''))
    check_parse('conf LATEX on', (['CONF', 'LATEX', 'on'], ''))
    check_parse('import gauss_jordan -t', (['IMPORT', 'gauss_jordan', '-t'], ''))
    check_parse('f[x] := x;  # the semicolon hides the output', 
                (['LINE', ['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST', ['NAME', 'x']]], ['EXP:NAME', 'x']], ['HIDE'], ['COMMENT', 'the semicolon hides the output']], ''))

def more_tests():
    check_parse('[3, 4] if x=3 else (x: 2, y: 3) -> x+y',
                (['EXP:IF_ELSE', ['LST', ['EXP:NUM:INT', '3'], ['EXP:NUM:INT', '4']], ['OP_SEQ', ['NAME', 'x'], ['BOP', '='], ['NUM:INT', '3']], ['EXP:LOCAL', ['BINDS', ['BIND', ['NAME', 'x'], ['EXP:NUM:INT', '2']], ['BIND', ['NAME', 'y'], ['EXP:NUM:INT', '3']]], ['EXP:OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]]], ''))
    check_parse('[x+f[f[3*6]^2], [2, 6], g[3, 6]]',
                (['EXP:LST', ['EXP:OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'f'], ['EMPTY'], ['LST', ['EXP:OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['LST', ['EXP:OP_SEQ', ['NUM:INT', '3'], ['BOP', '*'], ['NUM:INT', '6']]], ['BOP', '^'], ['NUM:INT', '2']]]], ['EXP:LST', ['EXP:NUM:INT', '2'], ['EXP:NUM:INT', '6']], ['EXP:OP_SEQ', ['NAME', 'g'], ['EMPTY'], ['LST', ['EXP:NUM:INT', '3'], ['EXP:NUM:INT', '6']]]], ''))
    check_parse('[x, [y, *z], *w] -> [x+y+z, w]',
                (['EXP:LAMBDA', ['PAR_LST', [['NAME', 'x'], ['PAR_LST', ['NAME', 'y'], ['OPT_PAR:NAME', 'z']]], ['OPT_PAR:NAME', 'w']], ['EXP:LST', ['EXP:OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y'], ['BOP', '+'], ['NAME', 'z']], ['EXP:NAME', 'w']]], ''))
    check_parse("(x*('y+2))/3",
                (['EXP:OP_SEQ', ['EXP:OP_SEQ', ['NAME', 'x'], ['BOP', '*'], ['EXP:OP_SEQ', ['SYM:NAME', 'y'], ['BOP', '+'], ['NUM:INT', '2']]], ['BOP', '/'], ['NUM:INT', '3']], ''))

def test_ill():
    check_parse('(3', (['EMPTY'], '(3'))
    check_parse('[3, f(4])', (['EMPTY'], '[3, f(4])'))
    check_parse('f[3, [5]', (['EXP:NAME', 'f'], '[3, [5]'))
    check_parse('[2, 4] + [6, 7', 
                (['EXP:LST', ['EXP:NUM:INT', '2'], ['EXP:NUM:INT', '4']], ' + [6, 7'))
    check_parse('[*a, *b] -> [a; b]', 
                (['EXP:LST', ['LS_ITEM', '*', ['EXP:NAME', 'a']], ['LS_ITEM', '*', ['EXP:NAME', 'b']]], ' -> [a; b]'))

def test():
    simple_tests()
    more_tests()
    # test_ill()

test()