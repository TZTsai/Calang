import re, json, ast
import config
from builtin import operators
from objects import Form, Op, SyntaxTree, tree_tag, is_tree
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

    
def compile_grammar(grammar):
    def compile(tree):
        if type(tree) in [list, tuple]:
            if tree[0] == 'RE':
                return ('RE', re.compile(tree[1]))
            else:
                return tuple(compile(t) for t in tree)
        else:
            return tree
    for tag, tree in grammar.items():
        grammar[tag] = compile(tree)
    return grammar


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
        elif tr in self.to_merge:
            self.to_merge.remove(tr)
            for t in tr: self.add_to_seq(seq, t)
        else:
            seq.append(tr)
    
    def parse_atom(self, tag, pattern, text):
        if tag == 'RE':
            m = pattern.match(text)
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
    
    # @trace
    @memo
    def parse_tag(self, tag, text):
        alttag = None
        if ':' in tag:  # ALTTAG:TAG
            alttag, tag = tag.split(':')

        tree, rem = self.parse_tree(self.grammar[tag], text)
        if tree is None: return self.failed
        
        if alttag: tag = alttag
        tree = self.process_tag(tag, tree)
        
        if type(tree[0]) is str:
            return SyntaxTree(tree), rem
        else:
            return tree, rem

    def process_tag(self, tag, tree):
        if not tree:
            return [tag]
        elif isinstance(tree, list):
            if tag in self.held_tags:
                if is_tree(tree):
                    tree = [tag, tree]
                else:
                    tree = [tag] + tree
            elif not is_tree(tree):
                if len(tree) == 1:
                    tree = tree[0]
                elif tag[0] == '_':
                    self.to_merge.append(tree)
                else:
                    tree = [tag] + tree
            return tree
        else:
            return [tag, tree]


class CalcParser(Parser):
    grammar = compile_grammar(grammar)

    held_tags = {
        'DIR', 'DEL', 'QUOTE', 'UNQUOTE', 'INFO', 'ENV',
        'LIST', 'ARRAY', 'FORM', 'NS', 'UNPACK'
    }

    keywords = {'dir', 'load', 'config', 'import', 'del',
                'info', 'exit', 'if', 'and', 'or'}

    synonyms = str.maketrans({
        '×': '*',         '÷': '/',         '∈': 'in',
        '∨': '/\\',      '∧': '\\/',      '⊗': 'xor',
        '→': '->',        '←': '<-'
    })

    def __init__(self):
        super().__init__()
        self.catstr = None
        self.whitespace = self.grammar[' ']
        
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
        if type(tree) is str and tree in self.keywords:
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
    text = text.translate(CalcParser.synonyms)
    tree, rem = calc_parser.parse_tag('LINE', text)
    return tree, rem

        
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
            if tr[-1][0] == 'DOC':
                tr = tr[:-1]
            tup = tuple(map(rec, tr[1:]))
            if tr[2][0] == 'SP':
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
