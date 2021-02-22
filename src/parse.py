import re, json
import config
from builtin import operators
from utils.deco import memo, trace, disabled
from utils.debug import check, check_record, pprint


try:
    assert not config.debug
    grammar = json.load(open('src/utils/grammar.json', 'r'))
    trace = disabled
except:
    from grammar import grammar


keywords = {'if', 'else', 'in', 'dir', 'for', 'with', 'load',
            'config', 'import', 'del', 'info'}

trace = disabled


# functions dealing with tags
def is_name(s):
    return type(s) is str and s

tag_pattern = re.compile('[A-Z_:]+')
def is_tag(s):
    return is_name(s) and tag_pattern.match(s)

def is_tree(t):
    return type(t) is list and t and is_tag(t[0])

def tree_tag(t):
    return t[0].split(':')[0] if is_tree(t) else None


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

    must_have = {'BIND': '=', 'MAP': '->', 'MATCH': '::', 'GEN_LST': 'for', 
                 '_EXT': '..', 'SLICE': ':', '_DLST': ';'}
    @trace
    @memo
    def parse_tag(tag, text):
        # allow OBJ:ALTNAME; changes the tag to ALTNAME
        alttag = None
        if ':' in tag: alttag, tag = tag.split(':')

        # prechecks to speed up parsing
        if not text and tag not in ('LINE', 'EMPTY'):
            return None, None
        if tag in must_have and must_have[tag] not in text:
            return None, None
        if tag[-2:] == 'OP':
            text = lstrip(text)

        tree, rem = parse_tree(grammar[tag], text)
        if rem is None:
            return None, None
        if tag == 'NAME' and tree in keywords:
            return None, None
        if tree and tree[0] == '(merge)':
            tree = tree[1:]
        tree = process_tag(alttag if alttag else tag, tree)
        return tree, rem

    kept_tags = lambda tag: tag in {'DIR', 'DEL', 'NM_SP', 'QUOTE', 'INFO'}
    # @trace
    def process_tag(tag, tree):
        if tag[0] == '_':
            tag = '(merge)'
        if tag == 'BIND':  # special syntax for inheritance
            convert_if_inherit(tree)

        if not tree:
            return [tag]
        elif is_name(tree):
            return [tag, tree]
        elif is_tree(tree):
            if kept_tags(tag):
                tree = [tag, tree]  # keep the list tag
            elif tag == 'FORM':  # special case: split the pars
                tree = split_pars(tree)
            return tree
        elif len(tree) == 1:
            return process_tag(tag, tree[0])
        else:
            return [tag] + tree

    text = lstrip(text)
    if not text: return ['EMPTY'], ''
    return parse_tag(tag, text)


def split_pars(form):
    "Split a FORM syntax tree into 4 parts: pars, opt-pars, ext-par, all-pars."

    def check_par(par):
        if par in all_pars:
            raise NameError('duplicate variable name')
        else:
            all_pars.add(par)
            
    if tree_tag(form) == 'PAR':
        return form
    else:
        pars, opt_pars = ['PARS'], ['OPTPARS']
        ext_par = None
        all_pars = set()
        for t in form[1:]:
            if t[0] == 'PAR':
                check_par(t[1])
                pars.append(t[1])
            elif t[0] == 'PAR_LST':
                pars.append(split_pars(t))
            elif t[0] == 'OPTPAR':
                check_par(t[1][1])
                opt_pars.append(t[1:])
            else:
                check_par(t[1])
                ext_par = t[1]
    return ['FORM', pars, opt_pars, ext_par]


def convert_if_inherit(bind):
    "Transform the BIND tree if it contains an inheritance from PARENT."
    if tree_tag(bind[1]) == 'PARENT':
        parent = bind.pop(1)[1]
        body = bind[1]
        tag = 'INHERIT' if tree_tag(bind[0]) == 'FUNC' else 'CLOSURE'
        bind[1] = [tag, parent, body]
    

def rev_parse(tree):
    "Reconstruct a readable string from the syntax tree."
    
    def rec(tr, in_seq=False):
        "$in_seq: whether it is in a sequence"
        
        if not is_tree(tr):
            if type(tr) is tuple:
                 tr = list(map(rec, tr))
            return str(tr)
        
        def group(s): return '(%s)' if in_seq else s
        # if in an operation sequence, add a pair of parentheses
        
        tr = tr.copy()
        tag = tree_tag(tr)
        if tag in ('NAME', 'SYM', 'PAR', 'VAR'):
            return tr[1]
        elif tag == 'FIELD':
            return ''.join(map(rec, tr[1:]))
        elif tag == 'ATTR':
            return '.' + tr[1]
        elif tag == 'SEQ':
            return ''.join(rec(t, True) for t in tr[1:])
        elif tag[-2:] == 'OP':
            op = tr[1]
            if type(op) is str:
                op = operators[tag][op]
            template = ' %s ' if op.priority < 4 else '%s'
            return template % str(tr[1])
        elif tag == 'NUM':
            return str(tr[1])
        elif tag == 'FORM':
            _, pars, optpars, extpar = tr
            pars = [rec(par) for par in pars[1:]]
            optpars = [f'{rec(optpar)}: {default}' for optpar, default in optpars[1:]]
            extpar = [extpar+'..'] if extpar else []
            return "[%s]" % ', '.join(pars + optpars + extpar)
        elif tag == 'IF_ELSE':
            return group("%s if %s else %s" % tuple(map(rec, tr[1:])))
        elif tag[-3:] == 'LST':
            return '[%s]' % ', '.join(map(rec, tr[1:]))
        elif tag == 'MAP':
            _, form, exp = tr
            return group('%s -> %s' % (rec(form), rec(exp)))
        elif tag == 'DICT':
            return '(%s)' % ', '.join(map(rec, tr[1:]))
        elif tag == 'BIND':
            if tree_tag(tr[-1]) == 'DOC': tr = tr[1:]
            tup = tuple(rec(t) for t in tr[1:])
            if tree_tag(tr[2]) == 'AT':
                return '%s %s = %s' % tup
            else:
                return '%s = %s' % tup
        elif tag == 'MATCH':
            _, form, exp = tr
            return group('%s::%s' % (rec(form), rec(exp)))
        elif tag == 'CLOSURE':
            _, local, exp = tr
            return '%s %s' % (rec(local), rec(exp))
        elif tag == 'FUNC':
            _, name, form = tr
            return '%s%s' % (rec(name), rec(form))
        elif tag == 'AT':
            return '@' + rec(tr[1])
        elif tag == 'DELAY':
            return rec(tr[1], in_seq)
        elif tag in ('PRINT', 'DOC'):
            return ''
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
