from myutils import trace, log, interact
from mydecorators import memo
from json import load
from pprint import pprint, pformat
import re
from _builtins import op_list, keywords, all_, any_


log.out = open('grammar/log.yaml', 'w')
interact = lambda: 0

try:
    with open('grammar/grammar.json', 'r') as gf:
        grammar = load(gf)
except:
    from _grammar import grammar

op_starts = ''.join(set(op[0] for op in op_list))


def calc_parse(text, tag='LINE', grammar=grammar):

    whitespace = grammar[' ']
    no_space = False

    def is_tag(s):
        try: return s.split(':', 1)[0] in grammar
        except: return False

    def is_hidden_tag(s):
        return is_tag(s) and s[0] == '_'

    def lstrip(text):
        nonlocal no_space
        if no_space:
            no_space = False
            return text
        else:
            sp = re.match(whitespace, text)
            return text[sp.end():]

    # @memo
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
            if rem is not None:
                return tree, rem
        return None, None

    @trace
    def parse_seq(seq, text):
        tree, rem = [], text

        # precheck if the keywords are in the text
        for item in seq:
            if item[0] == 'STR' and item[1][1:-1] not in text:
                return None, None

        for item in seq:
            tr, rem = parse_tree(item, rem)
            if no_space and type(tr) is str:
                try: tree[-1] += tr; continue
                except: pass
            if rem is None: return None, None
            if tr:
                if tr[0] == '...': # from OP
                    for t in tr[1]: add_to_seq(tree, t)
                else:
                    add_to_seq(tree, tr)

        if len(tree) == 1: tree = tree[0]
        return tree, rem

    def add_to_seq(seq, tr):
        # the tree with a tag beginning with '_' will be 
        # merged into the sequence
        if is_hidden_tag(tr[0]): 
            seq.extend(tr[1:])
        else: 
            seq.append(tr)

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

    must_have = {'DEF': ':=', 'MAP': '->', 'LET': '->', 'GEN_LST': '|', 
                 'MATCH': '->', 'ENV': ':', 'SLICE': ':'}
    @trace
    @memo
    def parse_obj(obj, text):
        # prechecks to speed up parsing
        if obj in must_have and must_have[obj] not in text:
            return None, None
        if obj[-2:] == 'OP':
            text = lstrip(text)
            if text[0] not in op_starts:
                return None, None

        tree, rem = parse_tree(grammar[obj], text)
        if rem is None: 
            return None, None
        if obj == 'NAME' and tree in keywords:
            return None, None
        if tree and tree[0] == '...':  # from an OP that is not in a seq
            tree = tree[1]
        tree = process_tag(obj, tree)
        return tree, rem

    @trace
    def parse_op(item, op, text):
        # if op == '/' and re.match(whitespace, text)[0]:
        #     return None, None  # space at start not allowed
        tree, rem = [], text
        rep, maxrep = 0, (-1 if op in '+*' else 1)

        while maxrep < 0 or rep < maxrep:
            tr, _rem = parse_tree(item, rem)
            if _rem is None: break
            if tr:
                if type(tr[0]) is list:
                    tree.extend(tr)
                else: 
                    tree.append(tr)
            rem = _rem
            rep += 1

        if op in '+/-' and rep == 0:
            return None, None
        elif op == '!':
            if rep: return None, None
            else: return [], text 
        elif op == '-':
            tree = []
        elif op == '/':
            nonlocal no_space
            no_space = True         # force no space in between
        if tree:
            tree = ['...', tree]    # send message to merge the tree
        return tree, rem

    prefixes = ['NUM', 'SYM', 'LST', 'EXT_PAR', 'CMD']
    list_obj = lambda tag:  tag[-3:] == 'LST' or tag in ['DIR']
    @trace
    def process_tag(tag, tree):
        if not tree:
            return [tag]
        elif type(tree) is str:
            return [tag, tree]
        elif type(tree[0]) is str and is_tag(tree[0]):
            if tree[0][0] == '_':
                tree[0] = tag       # remove this tag
            elif list_obj(tag) and tag not in tree[0]:
                tree = [tag, tree]  # keep the list tag
            elif tag in prefixes:
                tree = [tag + ':' + tree[0], *tree[1:]]
            return tree
        elif len(tree) == 1:
            return process_tag(tag, tree[0])
        else:
            return [tag] + tree

    interact()
    return parse_obj(tag, text)


## tests ##

def repl():
    while True:
        exp = input('>>> ')
        if exp == 'q': return
        pprint(calc_parse(exp))

def check_parse(exp, expected, termin=1):
    actual = calc_parse(exp)
    if actual != expected:
        # comp_list(expected, actual)
        print('Wrong Answer of calc_parse(%s)\n'%exp +
                             'Expected: %s\n'%pformat(expected) +
                             'Actual: %s\n'%pformat(actual))
        if termin: raise AssertionError
        
def simple_tests():
    check_parse('3', (['NUM:REAL', '3'], ''))
    check_parse('x', (['NAME', 'x'], ''))
    check_parse('2*.4', (['SEQ', ['NUM:REAL', '2'], ['BOP', '*.'], ['NUM:REAL', '4']], ''))
    check_parse('2.4e-18', (['NUM:REAL', '2.4', '-18'], ''))
    check_parse('2.4-1e-10I', 
                (['NUM:COMPLEX', ['REAL', '2.4'], '-', ['REAL', '1', '-10']], ''))
    check_parse('1+2*3', 
                (['SEQ', ['NUM:REAL', '1'], ['BOP', '+'], ['NUM:REAL', '2'], ['BOP', '*'], ['NUM:REAL', '3']], ''))
    check_parse('3!+4', (['SEQ', ['NUM:REAL', '3'], ['ROP', '!'], ['BOP', '+'], ['NUM:REAL', '4']], ''))
    check_parse('[]', (['LST'], ''))
    check_parse('[2]', (['LST', ['NUM:REAL', '2']], ''))
    check_parse('[3, 4, 6]', (['LST', ['NUM:REAL', '3'], 
                            ['NUM:REAL', '4'], ['NUM:REAL', '6']], ''))
    check_parse('f[]',  (['SEQ', ['NAME', 'f'], ['LST']], ''))
    check_parse('x := 5', (['DEF', ['NAME', 'x'], ['NUM:REAL', '5']], ''))
    check_parse('x := 3 * f[3, 5, 7]',
                (['DEF', ['NAME', 'x'], ['SEQ', ['NUM:REAL', '3'], ['BOP', '*'], ['NAME', 'f'], ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '5'], ['NUM:REAL', '7']]]], ''))
    check_parse('f[x]:=1/x',
                (['DEF', ['PATTERN', ['NAME', 'f'], ['NAME', 'x']], ['SEQ', ['NUM:REAL', '1'], ['BOP', '/'], ['NAME', 'x']]], ''))
    check_parse('f[]:=1',
                (['DEF', ['PATTERN', ['NAME', 'f'], ['FORM']], ['NUM:REAL', '1']], ''))
    check_parse('f[x, y]:=x*y',
                (['DEF', ['PATTERN', ['NAME', 'f'], ['FORM', ['NAME', 'x'], ['NAME', 'y']]], ['SEQ', ['NAME', 'x'], ['BOP', '*'], ['NAME', 'y']]], ''))
    check_parse('[1,2;3,4]', 
                (['LST:MAT_LST', ['ROW_LST', ['NUM:REAL', '1'], ['NUM:REAL', '2']], ['ROW_LST', ['NUM:REAL', '3'], ['NUM:REAL', '4']]], ''))
    check_parse('when(1: 2, 3: 4, 5)', 
                (['WHEN', [['CASE', ['NUM:REAL', '1'], ['NUM:REAL', '2']], ['CASE', ['NUM:REAL', '3'], ['NUM:REAL', '4']]], ['NUM:REAL', '5']], ''))
    check_parse('[x, y] -> x+y',
                (['MAP', ['FORM', ['NAME', 'x'], ['NAME', 'y']], ['SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('[]->1', (['MAP', ['FORM'], ['NUM:REAL', '1']], ''))
    check_parse('[a, *r] -> [a, *r]', 
                (['MAP', ['FORM', ['NAME', 'a'], ['EXT_PAR:NAME', 'r']], ['LST', ['NAME', 'a'], ['LS_ITEM', '*', ['NAME', 'r']]]], ''))
    check_parse('(x: 2)', (['BIND', ['NAME', 'x'], ['NUM:REAL', '2']], ''))
    check_parse('(x:1, y:2) -> x+y',
                (['LET', ['ENV', ['BIND', ['NAME', 'x'], ['NUM:REAL', '1']], ['BIND', ['NAME', 'y'], ['NUM:REAL', '2']]], ['SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]], ''))
    check_parse('l[x:2]', 
                (['SEQ', ['NAME', 'l'], ['LST', ['SLICE', ['NAME', 'x'], ['NUM:REAL', '2']]]], ''))
    check_parse('[x|x in [1,2,3]]',
                (['LST:GEN_LST', ['NAME', 'x'], ['CONSTR', ['NAME', 'x'], ['LST', ['NUM:REAL', '1'], ['NUM:REAL', '2'], ['NUM:REAL', '3']]]], ''))
    check_parse('f[1:]', 
                (['SEQ', ['NAME', 'f'], ['LST', ['SLICE', ['NUM:REAL', '1'], ['EMPTY']]]], ''))
    check_parse('m[1:, :-1]',
                (['SEQ', ['NAME', 'm'], ['LST', ['SLICE', ['NUM:REAL', '1'], ['EMPTY']], ['SLICE', ['EMPTY'], ['NUM:REAL', '-1']]]], ''))
    check_parse('dir x', (['CMD:DIR', ['NAME', 'x']], ''))
    check_parse('del x, y', (['CMD:DEL', ['NAME', 'x'], ['NAME', 'y']], ''))
    check_parse('conf LATEX on', (['CMD:CONF', 'LATEX', 'on'], ''))
    check_parse('import gauss_jordan -t', (['CMD:IMPORT', 'gauss_jordan', '-t'], ''))
    check_parse('f[x] := x;  # the semicolon hides the output', 
                (['LINE', ['DEF', ['PATTERN', ['NAME', 'f'], ['NAME', 'x']], ['NAME', 'x']], ['HIDE'], ['COMMENT', 'the semicolon hides the output']], ''))

def more_tests():
    check_parse('2~~.-3', (['SEQ', ['NUM:REAL', '2'], ['BOP', '~'], ['LOP', '~.'], ['NUM:REAL', '-3']], ''))
    check_parse('[1,2,3]->[a,*b]', 
                 (['MATCH', ['LST', ['NUM:REAL', '1'], ['NUM:REAL', '2'], ['NUM:REAL', '3']], ['FORM', ['NAME', 'a'], ['EXT_PAR:NAME', 'b']]], ''))
    check_parse('x .f', (['FIELD', ['NAME', 'x'], ['NAME', 'f']], ''))
    check_parse('f.a.b[x] := f[x]', 
                (['DEF', ['PATTERN', ['FIELD', ['NAME', 'f'], ['NAME', 'a'], ['NAME', 'b']], ['NAME', 'x']], ['SEQ', ['NAME', 'f'], ['LST', ['NAME', 'x']]]], ''))
    check_parse('f[x, y, z: 0, *w] := 1', 
                (['DEF', ['PATTERN', ['NAME', 'f'], ['FORM', ['NAME', 'x'], ['NAME', 'y'], ['BIND', ['NAME', 'z'], ['NUM:REAL', '0']], ['EXT_PAR:NAME', 'w']]], ['NUM:REAL', '1']], ''))
    check_parse('[3, 4] if x=3 else (x: 2, y: 3) -> x+y',
                (['IF_ELSE', ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '4']], ['SEQ', ['NAME', 'x'], ['BOP', '='], ['NUM:REAL', '3']], ['LET', ['ENV', ['BIND', ['NAME', 'x'], ['NUM:REAL', '2']], ['BIND', ['NAME', 'y'], ['NUM:REAL', '3']]], ['SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']]]], ''))
    check_parse('[x+f[f[3*6]^2], [2, 6], g[3, 6]]',
                (['LST', ['SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'f'], ['LST', ['SEQ', ['NAME', 'f'], ['LST', ['SEQ', ['NUM:REAL', '3'], ['BOP', '*'], ['NUM:REAL', '6']]], ['BOP', '^'], ['NUM:REAL', '2']]]], ['LST', ['NUM:REAL', '2'], ['NUM:REAL', '6']], ['SEQ', ['NAME', 'g'], ['LST', ['NUM:REAL', '3'], ['NUM:REAL', '6']]]], ''))
    check_parse('[x, [y, *z], *w] -> [x+y+z, w]',
                (['MAP', ['FORM', ['NAME', 'x'], ['FORM', ['NAME', 'y'], ['EXT_PAR:NAME', 'z']], ['EXT_PAR:NAME', 'w']], ['LST', ['SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y'], ['BOP', '+'], ['NAME', 'z']], ['NAME', 'w']]], ''))
    check_parse("(x*('y+2))/3",
                (['SEQ', ['SEQ', ['NAME', 'x'], ['BOP', '*'], ['SEQ', ['SYM:NAME', 'y'], ['BOP', '+'], ['NUM:REAL', '2']]], ['BOP', '/'], ['NUM:REAL', '3']], ''))
    check_parse('[x+y | x in 1~10 | y in range[x]]', 
                (['LST:GEN_LST', ['SEQ', ['NAME', 'x'], ['BOP', '+'], ['NAME', 'y']], ['CONSTR', ['NAME', 'x'], ['SEQ', ['NUM:REAL', '1'], ['BOP', '~'], ['NUM:REAL', '10']]], ['CONSTR', ['NAME', 'y'], ['SEQ', ['NAME', 'range'], ['LST', ['NAME', 'x']]]]], ''))

def test_ill():
    check_parse('a . b', (['NAME', 'a'], ' . b'))
    check_parse('x : 2', (['NAME', 'x'], ' : 2'))
    check_parse('(3', (['EMPTY'], '(3'))
    check_parse('[3, f(4])', (['EMPTY'], '[3, f(4])'))
    check_parse('f[3, [5]', (['NAME', 'f'], '[3, [5]'))
    check_parse('[2, 4] + [6, 7', 
                (['SEQ', ['LST', ['NUM:REAL', '2'], ['NUM:REAL', '4']], ['BOP', '+']], ' [6, 7'))
    check_parse('[*a, *b] -> [a; b]', 
                (['LST', ['LS_ITEM', '*', ['NAME', 'a']], ['LS_ITEM', '*', ['NAME', 'b']]], ' -> [a; b]'))
                
def test():
    simple_tests()
    more_tests()
    test_ill()
    print('all tests passed')

if __name__ == "__main__":
    # repl()
    test()
