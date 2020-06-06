from myutils import trace, log, interact
from mydecorators import memo
from json import load
from pprint import pprint, pformat
import re
from __builtins import op_list, keywords, all_, any_


log.out = open('grammar/log.yaml', 'w')


try:
    with open('grammar/grammar.json', 'r') as gf:
        grammar = load(gf)
except:
    from __grammar import grammar


op_starts = ''.join(set(op[0] for op in op_list))


def calc_parse(type_, text, grammar=grammar):

    whitespace = grammar[' ']
    no_space = False

    def lstrip(text):
        if no_space: return text
        sp = re.match(whitespace, text)
        return text[sp.end():]

    def parse_tree(syntax, text):
        tag, body = syntax[0], syntax[1:]

        if text == '' and tag not in ('ITEM_OP', 'RE'):
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

    @trace
    def parse_seq(seq, text):
        tree, rem = [], text

        # precheck if the keywords are in the text
        for item in seq:
            if item[0] == 'STR' and item[1][1:-1] not in text:
                return None, None

        nonlocal no_space
        for item in seq:
            tr, rem = parse_tree(item, rem)
            if no_space:
                no_space = False
                if tree and type(tree[-1]) is str and type(tr) is str:
                    tree[-1] += tr; continue
            if rem is None: return None, None
            if tr and tr[0] == '++':   # from OP '/'
                no_space = True
                tr = tr[1]
            if tr:
                if tr[0] == '...':      # from OP '*'/'+'
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

    obj_marks = {'DEF': ':=', 'MAP': '->', 'ENV': '::'}
    @trace
    @memo
    def parse_obj(obj, text):
        # prechecks to speed up parsing
        if obj in obj_marks and obj_marks[obj] not in text:
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
        # if op == '/' and re.match(whitespace, text)[0]:
        #     return None, None  # space at start not allowed
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
            tree = ['...', tree]    # merge the tree
        if op == '/':
            tree = ['++', tree]     # force no space in between
        return tree, rem

    def is_tag(s):
        return s.split(':', 1)[0] in grammar

    prefixes = ['NUM', 'SYM', 'LST', 'EXT_PAR', 'CMD']
    list_obj = lambda tag:  tag[-3:] == 'LST' or tag in ['DIR', 'PARS']
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

    return parse_obj(type_, text)


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
                (['DEF', ['FUNC', ['NAME', 'f'], ['PARS', ['NAME', 'x']]], ['OP_SEQ', ['NUM:REAL', '1'], ['BOP', '/'], ['NAME', 'x']]], ''))
    check_parse('f[]:=1',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PARS']], ['NUM:REAL', '1']], ''))
    check_parse('f[x, y]:=x*y',
                (['DEF', ['FUNC', ['NAME', 'f'], ['PARS', ['NAME', 'x'], ['NAME', 'y']]], ['OP_SEQ', ['NAME', 'x'], ['BOP', '*'], ['NAME', 'y']]], ''))
    check_parse('[1,2;3,4]', 
                (['LST:MAT_LST', ['ROW_LST', ['NUM:REAL', '1'], ['NUM:REAL', '2']], ['ROW_LST', ['NUM:REAL', '3'], ['NUM:REAL', '4']]], ''))
    check_parse('when(1: 2, 3: 4, 5)', 
                (['WHEN', [['CASE', ['NUM:REAL', '1'], ['NUM:REAL', '2']], ['CASE', ['NUM:REAL', '3'], ['NUM:REAL', '4']]], ['NUM:REAL', '5']], ''))
    check_parse('[x, y] -> x+y',
                (['MAP', ['PARS', ['NAME', 'x'], ['NAME', 'y']], ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('[]->1', (['MAP', ['PARS'], ['NUM:REAL', '1']], ''))
    check_parse('[a, *r] -> [a, *r]', 
                (['MAP', ['PARS', ['NAME', 'a'], ['EXT_PAR:NAME', 'r']], ['LST', ['NAME', 'a'], ['LS_ITEM', '*', ['NAME', 'r']]]], ''))
    check_parse('(x: 2)', (['BIND', ['NAME', 'x'], ['NUM:REAL', '2']], ''))
    check_parse('(x:1, y:2) :: x+y',
                (['ENV', ['BINDS', ['BIND', ['NAME', 'x'], ['NUM:REAL', '1']], ['BIND', ['NAME', 'y'], ['NUM:REAL', '2']]], ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('l[x:2]', 
                (['OP_SEQ', ['NAME', 'l'], ['EMPTY'], ['LST', ['SLICE', ['NAME', 'x'], ['NUM:REAL', '2']]]], ''))
    check_parse('[x|x in [1,2,3]]',
                (['LST:GEN_LST', ['NAME', 'x'], ['CONSTR', ['NAME', 'x'], ['LST', ['NUM:REAL', '1'], ['NUM:REAL', '2'], ['NUM:REAL', '3']]]], ''))
    check_parse('f[1:]', 
                (['OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['LST', ['SLICE', ['NUM:REAL', '1'], ['EMPTY']]]], ''))
    check_parse('m[1:, :-1]',
                (['OP_SEQ', ['NAME', 'm'], ['EMPTY'], ['LST', ['SLICE', ['NUM:REAL', '1'], ['EMPTY']], ['SLICE', ['EMPTY'], ['TERM', ['LOP', '-'], ['NUM:REAL', '1']]]]], ''))
    check_parse('dir x', (['CMD:DIR', ['NAME', 'x']], ''))
    check_parse('del x, y', (['CMD:DEL', ['NAME', 'x'], ['NAME', 'y']], ''))
    check_parse('conf LATEX on', (['CMD:CONF', 'LATEX', 'on'], ''))
    check_parse('import gauss_jordan -t', (['CMD:IMPORT', 'gauss_jordan', '-t'], ''))
    check_parse('f[x] := x;  # the semicolon hides the output', 
                (['LINE', ['DEF', ['FUNC', ['NAME', 'f'], ['PARS', ['NAME', 'x']]], ['NAME', 'x']], ['HIDE'], ['COMMENT', 'the semicolon hides the output']], ''))

def more_tests():
    check_parse('x .f', (['FIELD', ['NAME', 'x'], ['NAME', 'f']], ''))
    check_parse('f.a.b[x] := f[x]', 
                (['DEF', ['FUNC', ['FIELD', ['NAME', 'f'], ['NAME', 'a'], ['NAME', 'b']], ['PARS', ['NAME', 'x']]], ['OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['LST', ['NAME', 'x']]]], ''))
    check_parse('f[x, y, z: 0, *w] := 1', 
                (['DEF', ['FUNC', ['NAME', 'f'], ['PARS', ['NAME', 'x'], ['NAME', 'y'], ['BIND', ['NAME', 'z'], ['NUM:REAL', '0']], ['EXT_PAR:NAME', 'w']]], ['NUM:REAL', '1']], '') )
    check_parse('[3, 4] if x=3 else (x: 2, y: 3) :: x+y',
                (['IF_ELSE', ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '4']], ['OP_SEQ', ['NAME', 'x'], ['BOP', '='], ['NUM:REAL', '3']], ['ENV', ['BINDS', ['BIND', ['NAME', 'x'], ['NUM:REAL', '2']], ['BIND', ['NAME', 'y'], ['NUM:REAL', '3']]], ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]]], ''))
    check_parse('[x+f[f[3*6]^2], [2, 6], g[3, 6]]',
                (['LST', ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'f'], ['EMPTY'], ['LST', ['OP_SEQ', ['NAME', 'f'], ['EMPTY'], ['LST', ['OP_SEQ', ['NUM:REAL', '3'], ['BOP', '*'], ['NUM:REAL', '6']]], ['BOP', '^'], ['NUM:REAL', '2']]]], ['LST', ['NUM:REAL', '2'], ['NUM:REAL', '6']], ['OP_SEQ', ['NAME', 'g'], ['EMPTY'], ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '6']]]], ''))
    check_parse('[x, [y, *z], *w] -> [x+y+z, w]',
                (['MAP', ['PARS', ['NAME', 'x'], ['PARS', ['NAME', 'y'], ['EXT_PAR:NAME', 'z']], ['EXT_PAR:NAME', 'w']], ['LST', ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y'], ['BOP', '+'], ['NAME', 'z']], ['NAME', 'w']]], ''))
    check_parse("(x*('y+2))/3",
                (['OP_SEQ', ['OP_SEQ', ['NAME', 'x'], ['BOP', '*'], ['OP_SEQ', ['SYM:NAME', 'y'], ['BOP', '+'], ['NUM:REAL', '2']]], ['BOP', '/'], ['NUM:REAL', '3']], ''))
    check_parse('[x+y | x in 1~10 | y in range[x]]', 
                (['LST:GEN_LST', ['OP_SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']], ['CONSTRS', ['CONSTR', ['NAME', 'x'], ['OP_SEQ', ['NUM:REAL', '1'], ['BOP', '~'], ['NUM:REAL', '10']]], ['CONSTR', ['NAME', 'y'], ['OP_SEQ', ['NAME', 'range'], ['EMPTY'], ['LST', ['NAME', 'x']]]]]], ''))

def test_ill():
    check_parse('a . b', (['NAME', 'a'], ' . b'))
    check_parse('x : 2', (['NAME', 'x'], ' : 2'))
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