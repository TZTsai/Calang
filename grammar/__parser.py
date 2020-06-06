from myutils import trace, log, interact
from mydecorators import memo
from json import load
from pprint import pprint, pformat
import re
from __builtins import op_list, keywords


# trace.maxdepth = -1
interact = lambda: 0


try:
    with open('grammar/grammar.json', 'r') as gf:
        grammar = load(gf)
except:
    from __grammar import grammar


op_starts = ''.join(set(op[0] for op in op_list))


def calc_parse(type_, text, grammar=grammar):

    whitespace = grammar[' ']

    def lstrip(text):
        sp = re.match(whitespace, text)
        return text[sp.end():]

    def parse_tree(syntax, text):
        tag, body = syntax[0], syntax[1:]

        if text == '' and tag != 'ITEM_OP':
            return ('', '') if tag == 'RE' else (None, None)

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

    @trace
    def parse_seq(seq, text):
        tree, rem = [], text
        # precheck if the keywords are in the text
        for item in seq:
            if item[0] == 'STR':
                if item[1][1:-1] not in text:
                    return None, None
        nonlocal whitespace
        for item in seq:
            tr, rem = parse_tree(item, rem)
            if whitespace == '': 
                whitespace = grammar[' ']
                if type(tree[-1]) is str and type(tr) is str:
                    tree[-1] += tr
                    continue
            if rem is None: return None, None
            if tr:
                if tr[0] == '/':
                    whitespace = ''
                    tr = tr[1]
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
        if obj == 'DEF' and ':=' not in text:
            return None, None
        if obj in ('MAP', 'SUBS') and '->' not in text:
            return None, None
        if obj[-2:] == 'OP' and lstrip(text)[0] not in op_starts:
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
        rep, maxrep = 0, (1 if op in '?/-' else -1)
        while maxrep < 0 or rep < maxrep:
            tr, _rem = parse_tree(item, rem)
            if _rem is None: break
            if len(tr) > 0 and type(tr[0]) is list: 
                tree.extend(tr)
            else:
                tree.append(tr)
            rem = _rem
            rep += 1
        if op in '+/-' and rep == 0:
            return None, None
        if op == '-' or not tree:
            tree = []
        elif len(tree) == 1:
            tree = tree[0]
        else: 
            tree = ['...', tree]
        if op == '/':
            tree = ['/', tree]
        return tree, rem

    def is_tag(s):
        return s.split(':', 1)[0] in grammar

    prefixes = ['NUM', 'SYM', 'LST', 'OPT_PAR', 'CMD']
    list_obj = lambda tag:  tag[-3:] == 'LST' or tag in ['DIR']
    @memo
    @trace
    def process_tag(tag, tree):
        if not tree:
            return [tag]
        elif type(tree) is str:
            return [tag, tree]
        elif type(tree[0]) is str and is_tag(tree[0]):
            if list_obj(tag) and tag not in tree[0]:
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

def check_parse(exp, expected, termin=1):
    actual = parse(exp)
    if actual != expected:
        # comp_list(expected, actual)
        print('Wrong Answer of parse(%s)\n'%exp +
                             'Expected: %s\n'%pformat(expected) +
                             'Actual: %s\n'%pformat(actual))
        if termin: raise AssertionError
        

def simple_tests():
    check_parse('3', (['NUM:REAL', '3'], ''))
    check_parse('x', (['NAME', 'x'], ''))
    check_parse('2.4e-18', (['NUM:REAL', '2.4', '-18'], ''))
    check_parse('2.4-1e-10I', 
                (['NUM:COMPLEX', ['REAL', '2.4'], '-', ['REAL', '1', '-10']], ''))
    check_parse('1+2*3', 
                (['OP_SEQ', ['NUM:REAL', '1'], ['BOP', '+'], ['NUM:REAL', '2'], ['BOP', '*'], ['NUM:REAL', '3']], ''))
    check_parse('3!+4', (['OP_SEQ', ['TERM', ['NUM:REAL', '3'], ['ROP', '!']], 
                         ['BOP', '+'], ['NUM:REAL', '4']], ''))
    check_parse('4!', (['TERM', ['NUM:REAL', '4'], ['ROP', '!']], ''))
    check_parse('[]', (['LST'], ''))
    check_parse('[2]', (['LST', ['NUM:REAL', '2']], ''))
    check_parse('[3, 4, 6]', (['LST', ['NUM:REAL', '3'], 
                              ['NUM:REAL', '4'], ['NUM:REAL', '6']], ''))
    check_parse('f[]',  (['OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['LST']], ''))
    check_parse('x := 5', (['DEF', ['NAME', 'x'], ['NUM:REAL', '5']], ''))
    check_parse('x := 3 * f[3, 5, 7]',
                (['DEF', ['NAME', 'x'], ['OP_SEQ', ['NUM:REAL', '3'], ['BOP', '*'], ['NAME', 'f'], ['EMPTY'], ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '5'], ['NUM:REAL', '7']]]], ''))
    check_parse('f[x]:=1/x',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST', ['NAME', 'x']]], ['OP_SEQ', ['NUM:REAL', '1'], ['BOP', '/'], ['NAME', 'x']]], ''))
    check_parse('f[]:=1',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST']], ['NUM:REAL', '1']], ''))
    check_parse('f[x, y]:=x*y',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST', ['NAME', 'x'], ['NAME', 'y']]], ['OP_SEQ', ['NAME', 'x'], ['BOP', '*'], ['NAME', 'y']]], ''))
    check_parse('[1,2;3,4]', 
                (['LST:MAT_LST', ['ROW_LST', ['NUM:REAL', '1'], ['NUM:REAL', '2']], ['ROW_LST', ['NUM:REAL', '3'], ['NUM:REAL', '4']]], ''))
    check_parse('when(1: 2, 3: 4, 5)', 
                 (['WHEN', [['CASE', ['NUM:REAL', '1'], ['NUM:REAL', '2']], ['CASE', ['NUM:REAL', '3'], ['NUM:REAL', '4']]], ['NUM:REAL', '5']], ''))
    check_parse('[x, y] -> x+y',
                (['MAP', ['PAR_LST', ['NAME', 'x'], ['NAME', 'y']], ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('[]->1', (['MAP', ['PAR_LST'], ['NUM:REAL', '1']], ''))
    check_parse('[a, *r] -> [a, *r]', 
                (['MAP', ['PAR_LST', ['NAME', 'a'], ['OPT_PAR:NAME', 'r']], ['LST', ['NAME', 'a'], ['LS_ITEM', '*', ['NAME', 'r']]]], ''))
    check_parse('(x:1, y:2) -> x+y',
                (['SUBS', ['BINDS', ['BIND', ['NAME', 'x'], ['NUM:REAL', '1']], ['BIND', ['NAME', 'y'], ['NUM:REAL', '2']]], ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('[x|x in [1,2,3]]',
                (['LST:GEN_LST', ['NAME', 'x'], ['CONSTR', ['NAME', 'x'], ['LST', ['NUM:REAL', '1'], ['NUM:REAL', '2'], ['NUM:REAL', '3']]]], ''))
    check_parse('f[1:]', 
                (['OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['SLICE', ['NUM:REAL', '1'], ['EMPTY']]], ''))
    check_parse('m[1:, :-1]',
                (['OP_SEQ', ['NAME', 'm'], ['EMPTY'], ['SUBSCR', ['SLICE', ['NUM:REAL', '1'], ['EMPTY']], ['SLICE', ['EMPTY'], ['TERM', ['LOP', '-'], ['NUM:REAL', '1']]]]], ''))
    check_parse('dir x', (['CMD:DIR', ['NAME', 'x']], ''))
    check_parse('del x, y', (['CMD:DEL', ['NAME', 'x'], ['NAME', 'y']], ''))
    check_parse('conf LATEX on', (['CMD:CONF', 'LATEX', 'on'], ''))
    check_parse('import gauss_jordan -t', (['IMPORT', 'gauss_jordan', '-t'], ''))
    check_parse('f[x] := x;  # the semicolon hides the output', 
                (['LINE', ['DEF', ['FUNC', ['NAME', 'f'], ['PAR_LST', ['NAME', 'x']]], ['NAME', 'x']], ['HIDE'], ['COMMENT', 'the semicolon hides the output']], ''))

def more_tests():
    check_parse('[3, 4] if x=3 else (x: 2, y: 3) -> x+y',
                (['IF_ELSE', ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '4']], ['OP_SEQ', ['NAME', 'x'], ['BOP', '='], ['NUM:REAL', '3']], ['SUBS', ['BINDS', ['BIND', ['NAME', 'x'], ['NUM:REAL', '2']], ['BIND', ['NAME', 'y'], ['NUM:REAL', '3']]], ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]]], ''))
    check_parse('[x+f[f[3*6]^2], [2, 6], g[3, 6]]',
                (['LST', ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'f'], ['EMPTY'], ['LST', ['OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['LST', ['OP_SEQ', ['NUM:REAL', '3'], ['BOP', '*'], ['NUM:REAL', '6']]], ['BOP', '^'], ['NUM:REAL', '2']]]], ['LST', ['NUM:REAL', '2'], ['NUM:REAL', '6']], ['OP_SEQ', ['NAME', 'g'], ['EMPTY'], ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '6']]]], ''))
    check_parse('[x, [y, *z], *w] -> [x+y+z, w]',
                (['MAP', ['PAR_LST', [['NAME', 'x'], ['PAR_LST', ['NAME', 'y'], ['OPT_PAR:NAME', 'z']]], ['OPT_PAR:NAME', 'w']], ['LST', ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y'], ['BOP', '+'], ['NAME', 'z']], ['NAME', 'w']]], ''))
    check_parse("(x*('y+2))/3",
                (['OP_SEQ', ['OP_SEQ', ['NAME', 'x'], ['BOP', '*'], ['OP_SEQ', ['SYM:NAME', 'y'], ['BOP', '+'], ['NUM:REAL', '2']]], ['BOP', '/'], ['NUM:REAL', '3']], ''))
    check_parse('[x+y | x in 1~10 | y in range[x]]', 
                (['LST:GEN_LST', ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']], ['CONSTRS', ['CONSTR', ['NAME', 'x'], ['OP_SEQ', ['NUM:REAL', '1'], ['BOP', '~'], ['NUM:REAL', '10']]], ['CONSTR', ['NAME', 'y'], ['OP_SEQ', ['NAME', 'range'], ['EMPTY'], ['LST', ['NAME', 'x']]]]]], ''))

def test_ill():
    check_parse('(3', (['EMPTY'], '(3'))
    check_parse('[3, f(4])', (['EMPTY'], '[3, f(4])'))
    check_parse('f[3, [5]', (['NAME', 'f'], '[3, [5]'))
    check_parse('[2, 4] + [6, 7', 
                (['LST', ['NUM:REAL', '2'], ['NUM:REAL', '4']], ' + [6, 7'))
    check_parse('[*a, *b] -> [a; b]', 
                (['LST', ['LS_ITEM', '*', ['NAME', 'a']], ['LS_ITEM', '*', ['NAME', 'b']]], ' -> [a; b]'))

def test():
    simple_tests()
    more_tests()
    test_ill()

test()