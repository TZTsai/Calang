import re, json, ast
import config
from builtin import operators
from objects import Form, Op
from utils.funcs import *
from utils.debug import trace, interact, check, check_record, pprint


try:
    assert not config.debug
    with open('utils/grammar.json', encoding='utf8') as f:
        grammar = json.load(f)
    with open('utils/semantics.json') as f:
        semantics = json.load(f)
except:
    from grammar import grammar, semantics


class Parser:
    failed = None, None
    grammar = None
    held_tags = set()
    
    def __init__(self):
        self.to_merge = []
    
    def parse_tree(self, rule, text):
        tag, body = rule[0], rule[1:]

        if not text and tag not in ('ITEM_OP', 'RE'):
            return self.failed

        if tag == 'EXP':
            return self.parse_alts(body, text)
        elif tag in ('ALT', 'ITEMS', 'VARS'):
            return self.parse_seq(body, text)
        elif tag in ('OBJ', 'PAR'):
            return self.parse_tag(body[0], text)
        elif tag == 'ITEM_OP':
            item, [_, op] = body
            return self.parse_op(item, op, text)
        else:
            return self.parse_atom(tag, body[0], text)
        
    def parse_alts(self, alts, text):
        for alt in alts:
            tree, rem = self.parse_tree(alt, text)
            if rem is not None:
                return tree, rem
        return self.failed

    def parse_seq(self, seq, text):
        tree, rem = [], text

        # precheck if the keywords are in the text
        for item in seq:
            if type(text) is not str: break
            if item[0] in ['STR', 'MARK'] and item[1] not in text:
                return self.failed
            
        for item in seq:
            tr, rem = self.parse_tree(item, rem)
            if tr is None: return self.failed
            self.add_to_seq(tree, tr)
            
        if len(tree) == 1: tree = tree[0]
        return tree, rem
    
    def add_to_seq(self, seq, tr):
        if not tr: return
        # if tr[0] == '(merge)':  # (merge) is a special tag to merge into seq
        #     tr.pop(0)
        if tr in self.to_merge:
            for t in tr: self.add_to_seq(seq, t)
            self.to_merge.remove(tr)
        else:
            seq.append(tr)
    
    def parse_atom(self, tag, pattern, text):
        if tag == 'RE':
            m = re.match(pattern, text)
            if not m: return self.failed
            else: return m[0], text[m.end():]
        else:  # STR or MARK
            try:
                pre, rem = text.split(pattern, 1)
                assert not pre
                mat = pattern if tag == 'STR' else []
                return mat, rem
            except:
                return self.failed
           
    # Caution: must not add @memo decorator!
    def parse_op(self, item, op, text):
        seq, rem = [], text
        rep, maxrep = 0, (-1 if op in '+*' else 1)

        while maxrep < 0 or rep < maxrep:
            tr, _rem = self.parse_tree(item, rem)
            if _rem is None: break
            if tr:
                if type(tr[0]) is list: seq.extend(tr)
                else: seq.append(tr)
            rem = _rem
            rep += 1

        if op in '+/-' and rep == 0:
            return self.failed
        elif op == '!':
            if rep: return self.failed
            else: return [], text 
        elif op == '-':
            seq = []
            
        self.to_merge.append(seq)
        return seq, rem
        # tree = ['(merge)'] + seq
    
    @trace
    @memo
    def parse_tag(self, tag, text):
        alttag = None
        if ':' in tag:  # ALTTAG:TAG
            alttag, tag = tag.split(':')

        tree, rem = self.parse_tree(self.grammar[tag], text)
        if tree is None: return self.failed
        if alttag: tag = alttag
        tree = self.process_tag(tag, tree)
        return tree, rem

    def process_tag(self, tag, tree):
        # if tag[0] == '_':
        #     tag = '(merge)'
        # if tree and tree[0] == '(merge)':
        #     tree = tree[1:]

        if not tree:
            return [tag]
        elif is_name(tree):
            return [tag, tree]
        elif is_tree(tree):
            if tag in self.held_tags:
                tree = [tag, tree]
            if tag[0] == '_':
                tree = tree[1:]
                self.to_merge.append(tree)
            return tree
        elif len(tree) == 1:
            return self.process_tag(tag, tree[0])
        else:
            return [tag] + tree


class CalcParser(Parser):
    grammar = grammar

    held_tags = {
        'DIR', 'DEL', 'QUOTE', 'UNQUOTE', 'INFO',
        'ENV', 'LIST', 'ARRAY', 'FORM', 'NS', 'UNPACK'
    }

    keywords = {'dir', 'load', 'config', 'import', 'del',
                'info', 'exit', 'if', 'and', 'or'}

    synonyms = {
        '×': ['*'],         '÷': ['/'],         'in': ['∈'],
        '∨': ['/\\'],      '∧': ['\\/'],      '⊗': ['xor'],
        '→': ['->'],        '←': ['<-']
    }

    @classmethod
    def try_synonyms(cls, parse):
        synonyms = cls.synonyms
        
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

    def __init__(self):
        super().__init__()
        self.catstr = None
        self.whitespace = self.grammar[' ']
        self.parse_atom = CalcParser.try_synonyms(self.parse_atom)
        
    def add_to_seq(self, seq, tr):
        if not tr: return
        if self.catstr:
            assert tr == self.catstr
            seq[-1] += tr
            self.catstr = None
        else:
            super().add_to_seq(seq, tr)
        
    def lstrip(self, text):
        if self.catstr: return text
        sp = re.match(self.whitespace, text)
        return text[sp.end():]
        
    def parse_atom(self, tag, pattern, text):
        text = self.lstrip(text)
        tree, rem = super().parse_atom(tag, pattern, text)
        if is_name(tree) and tree in self.keywords:
            return self.failed
        else:
            return tree, rem
        
    def parse_op(self, item, op, text):
        tree, rem = super().parse_op(item, op, text)
        if tree and op == '/':
            assert type(tree) is str
            self.no_space.append(tree)
        return tree, rem
    
    def parse_tag(self, tag, text):
        # prechecks to speed up parsing
        if not text and tag != 'LINE':
            return self.failed
        if tag == 'OP':
            text = self.lstrip(text)
            
        tree, rem = super().parse_tag(tag, text)
        
        return tree, rem
    

calc_parser = CalcParser()

def calc_parse(text):
    return calc_parser.parse_tag('LINE', text)

        
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


if __name__ == "__main__":
    testfile = 'utils/syntax_tests.json'
    interact_record = interact(calc_parse)
    check_record(testfile, calc_parse, interact_record)
