import re, json
from .builtins import op_list, keywords, all_, any_
from utils.deco import memo, trace, disabled
from utils.debug import interact, check_record


trace = disabled

try:
    grammar = load(open('utils/grammar.json', 'r'))
except:
    from .grammar import grammar

op_starts = ''.join(set(op[0] for op in op_list if op))

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

    must_have = {'BIND': '=', 'MAP': '=>', 'MATCH': '::', 'GEN_LST': 'for', '_EXT': '~',
                 'SLICE': ':', '_DLST': ';'}
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

    prefixes = {'NUM', 'DELAY', 'AT'}
    list_obj = lambda tag: tag[-3:] == 'LST' or \
        tag in ['DIR', 'DEL', 'VARS', 'DICT']
    # @trace
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



if __name__ == "__main__":
    testfile = 'utils/parser_tests.json'
    testcases, passed = check_record(testfile, calc_parse)
    interact_record = interact(calc_parse)
    if not passed or interact_record:
        rewrite = input('rewrite? (y/N) ') == 'y'
    if rewrite:
        testcases.update(interact_record)
        json.dump(testcases, open(testfile, 'w'))
