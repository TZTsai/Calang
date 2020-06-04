from myutils import trace, log
from mydecorators import memo
from json import load
from pprint import pprint
import re
from __builtins import op_list


log.out = open('syntax tree/log.txt', 'w')

op_start = ''.join(set(('\\' if op[0] in '-\\' else '') + op[0] 
                       for op in op_list))
obj_pat = re.compile('[A-Z_]+')


def calc_parse(type_, text, grammar):

    whitespace = grammar[' ']
    tokenizer = whitespace + '(%s)'
    global op_start
    op_start = re.compile(f'{whitespace}[{op_start}]')

    @trace
    @memo  # avoid parsing the same atom again
    def parse(syntax, text):

        tag, body = syntax[0], syntax[1:]

        if text == '':
            if tag == 'ITEM_OP': return [], ''
            else: return None, None

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
                    elif tr[0] == ',':
                        tree.extend(tr[1:])
                    else:
                        tree.append(tr)
            if len(tree) == 1: tree = tree[0]
            return tree, rem
        elif tag == 'OBJ':
            obj = body[0]

            ## some pre checks to save computation
            # OP objects requires a lot of search
            if obj[-2:] == 'OP' and op_start.match(text) is None:
                return None, None

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
        elif tag in ('CHARS', 'RE'):
            pattern = body[0]
            if tag == 'RE': pattern = pattern[1:-1]
            m = re.match(tokenizer % pattern, text)
            if not m: return None, None
            else: return m[1], text[m.end():]
        elif tag == 'ITEM_OP':
            item, [_, op] = body
            tree, rem = [], text
            rep, maxrep = 0, (1 if op in '?-' else -1)
            while maxrep < 0 or rep < maxrep:
                tr, _rem = parse(item, rem)
                if _rem is None: break
                if tr: tree.append(tr)
                rem = _rem
            if op in '+-' and rep == 0:
                return None, None
            if op == '-': tree = []
            elif len(tree) == 1: tree = tree[0]
            return tree, rem
        else:
            raise TypeError('unrecognized type: %s' % tag)

    def process_tag(tag, tree):
        prefixes = ['NUM', 'EXP']
        if type(tree) is str:
            tree = [tag, tree]
        if (len(tree) > 1 and type(tree[0]) is str and obj_pat.match(tree[0])):
            if tag in prefixes: tree[0] = tag + ':' + tree[0]
        elif len(tree) > 0:
            tree = [tag] + tree
        return tree

    return parse(grammar[type_], text)


try:
    with open('syntax tree/grammar.json', 'r') as gf:
        grammar = load(gf)
except:
    from __grammar import grammar


def parse(exp):
    return calc_parse('LINE', exp, grammar)



## tests ##

def simple_egs():
    # print(parse('3'))
    # print(parse('x'))
    # print(parse('3+4'))
    # print(parse('4!'))
    # print(parse('[]'))
    # print(parse('[3, 4, 6]'))
    # print(parse('x := 5'))
    pprint(parse('x := 3 * f(3, 5, 7)'))
    # print(parse('(x*(y+2))/3'))
    # print(parse('f(x):=1/x'))
    # print(parse('[x+f(f(3*6)^2), [2, 6], g(3, 6)]'))

def bad_syntax_egs():
    print(parse('(3'))
    print(parse('[3, f(4])'))

def test():
    simple_egs()

test()