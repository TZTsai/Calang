import re, json, ast
import config
from builtin import operators
from objects import Form, Op
from utils.funcs import *
from utils.debug import trace, check, check_record, pprint


try:
    assert not config.debug
    with open('src/utils/grammar.json', encoding='utf8') as f:
        grammar = json.load(f)
    with open('utils/semantics.json') as f:
        semantics = json.load(f)
except:
    from grammar import grammar, semantics


keywords = {'dir', 'load', 'config', 'import', 'del', 'info', 'exit'}

synonyms = {
    '×': ['*'],         '÷': ['/'],         'in': ['∈'],
    '∨': ['/\\'],      '∧': ['\\/'],       '⊗': ['xor'],
    '->': ['→'],        '<-': ['←']
}

trace = disabled  # for logging


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
                    if is_name(tr):
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
            
    def try_synonyms(parse):
        def wrapped(tag, pattern, text):
            tr, rem = parse(tag, pattern, text)
            if tr is None:
                if tag in ('STR', 'MARK') and pattern in synonyms:
                    for altpat in synonyms[pattern]:
                        tr, rem = parse(tag, altpat, text)
                        if tr is not None:
                            return pattern if tag == 'STR' else [], rem
            return tr, rem
        return wrapped

    @try_synonyms
    def parse_atom(tag, pattern, text):
        text = lstrip(text)
        # if tag in ('STR', 'RE'):
        #     pattern = pattern[1:-1]
        if tag == 'RE':
            m = re.match(pattern, text)
            if not m: return None, None
            else: return m[0], text[m.end():]
        else:  # STR or MARK
            if tag == 'MARK':
                pattern = ast.literal_eval('"%s"' % pattern)
            try:
                pre, rem = text.split(pattern, 1)
                assert not pre
                return pattern if tag == 'STR' else [], rem
            except:
                return None, None
           
    # @trace
    # Caution: must not add @memo decorator!
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

    must_have = {'BIND': '=', 'MAP': '->', 'AT': '@',
                 'GENER': '@', 'GENLS': '@'}
    @trace
    @memo
    def parse_tag(tag, text):
        # allow OBJ:ALTNAME; changes the tag to ALTNAME
        alttag = None
        if ':' in tag: alttag, tag = tag.split(':')

        # prechecks to speed up parsing
        if not text and tag != 'LINE':
            return None, None
        if tag in must_have and must_have[tag] not in text:
            return None, None
        if tag == 'OP':
            text = lstrip(text)

        tree, rem = parse_tree(grammar[tag], text)
        if rem is None:
            return None, None
        if tag == 'NAME' and tree in keywords:
            return None, None
        # if tag == 'OP' and tree in synonym_ops:
        #     tree = synonym_ops[tree]
        if tree and tree[0] == '(merge)':
            tree = tree[1:]
        tree = process_tag(alttag if alttag else tag, tree)
        return tree, rem

    kept_tags = lambda tag: tag in {
        'DIR', 'DEL', 'QUOTE', 'UNQUOTE', 'INFO',
        'ENV', 'LIST', 'ARRAY', 'FORM', 'NS', 'UNPACK'
    }
    # @trace
    def process_tag(tag, tree):
        if tag[0] == '_':
            tag = '(merge)'
        # if tag == 'BIND':  # special syntax for inheritance
        #     convert_if_inherit(tree)

        if not tree:
            return [tag]
        elif is_name(tree):
            return [tag, tree]
        elif is_tree(tree):
            if kept_tags(tag):
                tree = [tag, tree]  # keep the list tag
            # elif tag == 'FORM':  # special case: split the pars
            #     tree = split_pars(tree)
            return tree
        elif len(tree) == 1:
            return process_tag(tag, tree[0])
        else:
            return [tag] + tree

    return parse_tag(tag, text)


# def split_pars(form):
#     "Split a FORM syntax tree into 4 parts: pars, opt-pars, ext-par, all-pars."

#     def check_par(par):
#         if par in all_pars:
#             raise NameError('duplicate variable name')
#         else:
#             all_pars.add(par)
            
#     if tree_tag(form) == 'PAR':
#         return form
#     else:
#         pars, opt_pars = ['PARS'], ['OPTPARS']
#         ext_par = None
#         all_pars = set()
#         for t in form[1:]:
#             if t[0] == 'PAR':
#                 check_par(t[1])
#                 pars.append(t[1])
#             elif t[0] == 'PAR_LST':
#                 pars.append(split_pars(t))
#             elif t[0] == 'OPTPAR':
#                 check_par(t[1][1])
#                 opt_pars.append(t[1:])
#             else:
#                 check_par(t[1])
#                 ext_par = t[1]
#     return ['FORM', pars, opt_pars, ext_par]


# def convert_if_inherit(bind):
#     "Transform the BIND tree if it contains an inheritance from PARENT."
#     if tree_tag(bind[1]) == 'PARENT':
#         parent = bind.pop(1)[1]
#         body = bind[1]
#         tag = 'INHERIT' if tree_tag(bind[0]) == 'FUNC' else 'CLOSURE'
#         bind[1] = [tag, parent, body]

        
def deparse(tree):
    "Reconstruct the expression from the syntax tree."
    
    def rec(tr):
        tag = tree_tag(tr)
        
        if tag is None:
            if type(tr) is tuple:
                 tr = list(map(rec, tr))
            else:
                return str(tr)
        
        if tag == 'NAME':
            return tr[1]
        elif tag == 'VAR':
            return ''.join(map(rec, tr[1:]))
        elif tag == 'ATTR':
            return '.' + tr[1]
        elif tag in ['PHRASE', 'ITEMS']:
            return ''.join(map(rec, tr[1:]))
        elif tag == 'OP':
            op = tr[1]
            if op in operators['BOP']:
                if op in '×*': return ' '
                else: return ' %s ' % op
            else: return op
        elif tag == 'APP':
            _, f, *args = tr
            args = map(rec, args)
            if isinstance(f, Op):
                if f.type == 'BOP':
                    x, y = args
                    return '%s %s %s' % (x, f, y)
                else:
                    x, = args
                    pair = (f, x) if f.type == 'LOP' else (x, f)
                    return '%s%s' % pair
            else:
                x, = args
                s = '%s%s' if x[0] in '([{' else '%s %s'
                return s % (f, x)
        elif tag[:3] == 'GEN':
            _, exp, *cs = tr
            s = '(%s @ %s)' if tag == 'GENER' else '[%s @ %s]'
            return s % (rec(exp), ', '.join(map(rec, cs)))
        elif tag == 'DOM':
            return '%s ∈ %s' % tuple(map(rec, tr[1:]))
        elif tag == 'NUM':
            return str(tr[1])
        elif tag == 'LIST':
            return '[%s]' % ', '.join(map(rec, tr[1:]))
        elif tag == 'MAP':
            _, form, exp = tr
            return '%s -> %s' % (rec(form), rec(exp))
        elif tag in ['BIND', 'KWD']:
            if tree_tag(tr[-1]) == 'DOC':
                tr = tr[1:]
            tup = tuple(map(rec, tr[1:]))
            if tree_tag(tr[2]) == 'SP':
                return '%s %s = %s' % tup
            else:
                return '%s = %s' % tup
        elif tag == 'UNPACK':
            return '%s..' % rec(tr[1])
        elif tag == 'AT':
            _, local, exp = tr
            return '%s %s' % (rec(local), rec(exp))
        else:
            return str(list(map(rec, tr)))
    return rec(tree)


# for testing
def interact(func):
    print('interactive testing of calc_parse:')
    record = {}
    while True:
        exp = input('>>> ')
        if exp in 'qQ':
            return record
        else:
            result = func(exp)
            pprint(result)
            record[exp,] = None  # for writing to testfile


if __name__ == "__main__":
    testfile = 'utils/syntax_tests.json'
    interact_record = interact(calc_parse)
    check_record(testfile, calc_parse, interact_record)
