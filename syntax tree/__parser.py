from myutils import trace, log
from mydecorators import memo
from json import load
from pprint import pprint, pformat
import re
from __builtins import op_list


log.out = open('syntax tree/log.yaml', 'w')
trace.maxdepth = 5


try:
    with open('syntax tree/grammar.json', 'r') as gf:
        grammar = load(gf)
except:
    from __grammar import grammar


whitespace = re.compile(grammar[' '])
op_start = ''.join(set(('\\' if op[0] in '-\\' else '') + op[0] 
                       for op in op_list))
op_start = re.compile(f'{whitespace}[{op_start}]')
obj_pat = re.compile('[A-Z_]+')


def lstrip(text):
    sp = re.match(whitespace, text)
    return text[sp.end():]


def calc_parse(type_, text):

    @trace
    def parse(syntax, text):
        tag, body = syntax[0], syntax[1:]

        if text == '':
            # only an item decorated by '?' or '*' can be matched to nothing
            if tag == 'ITEM_OP': return [], ''
            else: return None, None

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

    def parse_alts(alts, text):
        for alt in alts:
            tree, rem = parse(alt, text)
            if rem is not None: return tree, rem
        return None, None

    def parse_seq(seq, text):
        tree, rem = [], text
        # precheck if the keywords are in the text
        for item in seq:
            if item[0] == 'STR':
                if item[1][1:-1] not in text:
                    return None, None
        for item in seq:
            tr, rem = parse(item, rem)
            if rem is None: return None, None
            if tr:
                if type(tr[0]) is list:
                    tree.extend(tr)
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
            

    @memo
    def parse_obj(obj, text):
        # precheck for the OP object
        if obj[-2:] == 'OP' and op_start.match(text) is None:
            return None, None
        tree, rem = parse(grammar[obj], text)
        if rem is None: return None, None
        tree = process_tag(obj, tree)
        return tree, rem

    def parse_op(item, op, text):
        tree, rem = [], text
        rep, maxrep = 0, (1 if op in '?-' else -1)
        while maxrep < 0 or rep < maxrep:
            tr, _rem = parse(item, rem)
            if _rem is None: break
            if tr: tree.append(tr)
            rem = _rem
            rep += 1
        if op in '+-' and rep == 0:
            return None, None
        if op == '-': tree = []
        elif len(tree) == 1: tree = tree[0]
        return tree, rem

    def process_tag(tag, tree):
        prefixes = ['NUM', 'EXP']
        if type(tree) is str:
            tree = [tag, tree]
        try:
            assert obj_pat.match(tree[0])
            if tag in prefixes:
                tree[0] = tag + ':' + tree[0]
        except:
            tree = [tag] + tree
        return tree

    return parse(grammar[type_], text)


def parse(exp):
    return calc_parse('LINE', exp)



## tests ##

def check_parse(exp, expected):
    actual = parse(exp)
    if actual != expected:
        raise AssertionError('Wrong Answer of parse(%s)\n'%exp +
                             'Expected: %s\n'%pformat(expected) +
                             'Actual: %s\n'%pformat(actual))

def simple_egs():
    check_parse('3', (['EXP:NUM:INT', '3'], ''))
    check_parse('x', (['EXP:NAME', 'x'], ''))
    check_parse('3!+4', (['EXP:OP_SEQ', ['UOP_IT', ['NUM:INT', '3'], ['RUOP', '!']], 
                         ['BOP', '+'], ['NUM:INT', '4']], ''))
    check_parse('4!', (['EXP:UOP_IT', ['NUM:INT', '4'], ['RUOP', '!']], ''))
    check_parse('()', (['EXP:EXP:OP_SEQ'], ''))
    check_parse('[]', (['EXP:LIST'], ''))
    check_parse('[3, 4, 6]', (['EXP:LIST', ['EXP:NUM:INT', '3'], 
                              ['EXP:NUM:INT', '4'], ['EXP:NUM:INT', '6']], ''))
    check_parse('f()', (['EXP:APPLY', ['NAME', 'f'], ['ARG_LS']], ''))
    check_parse('x := 5', (['DEF', ['NAME', 'x'], ['EXP:NUM:INT', '5']], ''))
    check_parse('x := 3 * f(3, 5, 7)',
                (['DEF', ['NAME', 'x'],
                        ['EXP:OP_SEQ', ['NUM:INT', '3'],
                                        ['BOP', '*'],
                                        ['APPLY', ['NAME', 'f'],
                                                ['ARG_LS',
                                                    ['EXP:NUM:INT', '3'],
                                                    ['EXP:NUM:INT', '5'],
                                                    ['EXP:NUM:INT', '7']]]]],
                ''))
    pprint(parse("(x*('y+2))/3"))
    pprint(parse('f(x):=1/x'))
    # print(parse('[x+f(f(3*6)^2), [2, 6], g(3, 6)]'))

def bad_syntax_egs():
    print(parse('(3'))
    print(parse('[3, f(4])'))

def test():
    simple_egs()

test()