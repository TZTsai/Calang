from myutils import trace, log, interact
from mydecorators import memo, disabled
from json import load, dump
from pprint import pprint, pformat
import re
from _builtins import op_list, keywords, all_, any_


log.out = open('log.yaml', 'w')
interact = lambda: 0
# trace = disabled


# try:
#     with open('grammar.json', 'r') as gf:
#         grammar = load(gf)
# except:
#     from _grammar import grammar
from _grammar import grammar
op_starts = ''.join(set(op[0] for op in op_list))
tag_pat = re.compile('[A-Z_:]+')
def is_tag(s):
    try: return tag_pat.match(s.split(':', 1)[0])
    except: return False


def calc_parse(text, tag='LINE', grammar=grammar):

    whitespace = grammar[' ']
    no_space = False

    def lstrip(text):
        if no_space: return text
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
        elif tag in ('OBJ', 'PAR'):
            return parse_tag(body[0], text)
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

    # @trace
    def parse_seq(seq, text):
        tree, rem = [], text

        # precheck if the keywords are in the text
        for item in seq:
            if item[0] == 'STR' and item[1][1:-1] not in text:
                return None, None

        nonlocal no_space
        for item in seq:
            tr, rem = parse_tree(item, rem)
            if rem is None: return None, None
            if tr:
                if tr[0] == '(nospace)':
                    no_space = True
                    tr.pop(0)
                elif no_space:
                    no_space = False
                    if type(tr) is str:
                        try: tree[-1] += tr; continue
                        except: pass
                add_to_seq(tree, tr)

        if len(tree) == 1: tree = tree[0]
        return tree, rem

    def add_to_seq(seq, tr):
        if not tr: return
        if tr[0] == '(merge)':  # (merge) is a special tag to merge into seq
            tr.pop(0)
            for t in tr: add_to_seq(seq, t)
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

    # @trace
    # Caution: must not add memo decorator!
    def parse_op(item, op, text):
        seq, rem = [], text
        rep, maxrep = 0, (-1 if op in '+*' else 1)

        while maxrep < 0 or rep < maxrep:
            tr, _rem = parse_tree(item, rem)
            if _rem is None: break
            if tr:
                if type(tr[0]) is list: seq.extend(tr)
                else: seq.append(tr)
            rem = _rem
            rep += 1

        if op in '+/-' and rep == 0:
            return None, None
        elif op == '!':
            if rep: return None, None
            else: return [], text 
        elif op == '-':
            seq = []
        tree = ['(merge)'] + seq
        if op == '/':
            tree = ['(nospace)'] + tree
        return tree, rem

    must_have = {'DEF': '=', 'MAP': '->', 'LET': '->', 'GEN_LST': '|', 
                 'SLICE': ':', '_DLST': ';', 'BIND': ':', 'PRINT': '"'}
    @trace
    @memo
    def parse_tag(tag, text):
        # allow OBJ:ALTNAME; changes the tag to ALTNAME
        alttag = None
        if ':' in tag: tag, alttag = tag.split(':')

        # prechecks to speed up parsing
        if not text and tag not in ('LINE', 'EMPTY'):
            return None, None
        if tag in must_have and must_have[tag] not in text:
            return None, None
        if tag[-2:] == 'OP':
            text = lstrip(text)
            if text[0] not in op_starts:
                return None, None

        tree, rem = parse_tree(grammar[tag], text)
        if rem is None:
            return None, None
        if tag == 'NAME' and tree in keywords:
            return None, None
        if tree and tree[0] == '(merge)':
            tree = tree[1:]
        tree = process_tag(alttag if alttag else tag, tree)
        return tree, rem

    prefixes = {'NUM', 'DELAY', 'UNPACK', 'VAR'}
    list_obj = lambda tag: tag[-3:] == 'LST' or tag in ['DIR', 'ENV', 'DEL']
    @trace
    def process_tag(tag, tree):
        if tag[0] == '_': tag = '(merge)'

        if not tree:
            return [tag]
        elif type(tree) is str:
            return [tag, tree]
        elif is_tag(tree[0]):
            if list_obj(tag):
                tree = [tag, tree]  # keep the list tag
            elif tag in prefixes:
                tree = [tag + ':' + tree[0], *tree[1:]]
            return tree
        elif len(tree) == 1:
            return process_tag(tag, tree[0])
        else:
            return [tag] + tree

    text = lstrip(text)
    if not text: return ['EMPTY'], ''
    return parse_tag(tag, text)


## tests ##

def repl():
    prev_exp = None
    while True:
        exp = input('>>> ')
        if exp == 'q':
            return
        elif exp == 'W': 
            check_parse(prev_exp, None)
        else:
            pprint(calc_parse(exp))
            prev_exp = exp


testfile = 'tests/parser_tests.json'
testcases = load(open(testfile, 'r'))
rewrite = False

def test():
    for case in testcases.items(): check_parse(*case)

def check_parse(exp, expected):
    # print('testing: '+exp)
    # print('expecting: '+str(expected))
    if exp not in testcases:
        testcases[exp] = expected
    actual = calc_parse(exp)
    if not rec_comp(expected, actual):
        print('Wrong Answer of calc_parse(%s)\n'%exp +
                             'Expected: %s\n'%pformat(expected) +
                             'Actual: %s\n'%pformat(actual))
        testcases[exp] = actual
        global rewrite
        rewrite = True

def rec_comp(l1, l2):
    if type(l1) not in (tuple, list):
        if l1 != l2:
            print(l1, 'VS', l2)
            return False
        else:
            return True
    elif len(l1) != len(l2):
        print(l1, 'VS', l2)
        return False
    else:
        return all(rec_comp(i1, i2) for i1, i2 in zip(l1, l2))


if __name__ == "__main__":
    repl()
    test()
    if rewrite:
        rewrite = input('rewrite? ') == 'y'
    if rewrite:
        dump(testcases, open(testfile, 'w'))