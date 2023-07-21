"""
There are four types of rules: substitution, evaluation, execution and macro.

A substitution maps a list of values to another value, not requiring an Env.
An evaluation evaluates a syntax tree to a value, requiring an Env.
An execution is a special rule to control or query the state of evaluator.
A macro transforms the syntax tree before evaluation.

Definitions of these rule must adopt the following signatures:
    - substitution: f(tr) or f(tr, env=None)
    - evaluation: f(tr, env) or f(tr, env=None)
    - execution: f(tr)
    - macro: f(tr)
    
The program will examine the signatures of the definitions and classify them.
The names of execution rules and macro rules must be specified manually.
A rule with signature f(tr, env=None) will be classified as both substitution and evaluation.

About the application of these rules:
    - substitution: all items of the syntax tree will be evaluated prior to its application;
        if any item failed to be evaluated (thus remaining a tree), the program will abandon
        the application and keep its tree form.
    - evaluation: the rule will be applied to the full syntax tree instead of a list of values;
        thus features like short-circuit, closure, (macros), etc. are able to be implemented.
    - execution: the rule will be applied to the syntax tree like an evaluation rule, but no
        environment is provided.
"""

from functools import wraps
from copy import deepcopy
import re, json, inspect

from parse import calc_parse, semantics, Parser
from builtin import operators, binary_ops, builtins, shortcircuit_ops
from funcs import Is, iterable, indexable, eq, get_attr, partial
from sympy import Expr, Symbol, Array, Matrix, Eq, solve
from objects import *
from utils.debug import log, trace
from utils.funcs import *
import config


def InitGlobal():
    Global = Env(name='_global_', parent=Builtins)
    Global.ans = []
    return Global

Builtins = Env(name='_builtins_', binds=builtins)
Global = InitGlobal()


def calc_eval(exp, env=None):
    # parse the expression into a syntax tree
    tree, rest = calc_parse(exp)
    if rest: raise SyntaxError(f'syntax error in "{rest}"')
    
    if env is None: env = Global 
    result = eval_tree(tree, env)
    
    if is_tree(result) and result.tag == 'COMMENT':
        result = None

    if result is not None:
        # record and return the result
        Global.ans.append(result)
        return result


# substitution rules

def EVAL(tr):
    if tr[-1] != ';': return tr[-1]


def COMPLEX(tr):
    re, pm, im = tr[1:]
    return re + im*1j if pm == '+' else re - im*1j

def REAL(tr):
    if len(tr) > 2: return eval(tr[1]+'e'+tr[2])
    else: return eval(tr[1])

def BIN(tr): return eval(tr[1])

def HEX(tr): return eval(tr[1])


def VAR(tr):
    field = tr[1]
    for attr in tr[2:]:
        field = get_attr(field, attr)
    return field

def ATTR(tr):
    return Attr(tr[1])


def ANS(tr):
    s = tr[1]
    if all(c == '$' for c in s):
        id = -len(s)
    else:
        try: id = int(s[1:])
        except: raise SyntaxError('invalid history index!')
    return Global.ans[id]

def NOT(tr):
    return 0 if tr[1] else 1


def INFO(tr):
    print(tr[1].__doc__)
    
def LINE(tr):
    if len(tr) == 3:
        if config.test:
            LINE.comment = tr[2][1]
        return tr[1]
    elif len(tr) == 2:
        return tr[1]

LINE.comment = None


class ItemStack(list):
    class substack(list):
        def __init__(self, parent):
            self.parent = parent

        def pop(self, i=-1):
            x = self.parent.pop(i)
            y = super().pop(i)
            assert type(x) == type(y)
            return x
        
        def push(self, x):
            self.parent.append(x)
            self.append(x)
            
    def __init__(self):
        self.ops = ItemStack.substack(self)
        self.vls = ItemStack.substack(self)
        

def ITEMS(tr):
    # these are binary ops that can be represented by a space
    get = binary_ops['(get)']
    app = binary_ops['(app)']
    idx = binary_ops['.']
    mul = binary_ops['⋅']

    # binary ops that combine in the reverse order
    backward_bops = [app]
    
    seq = tr[1:]
    stk = ItemStack()
    
    def squeeze():
        "Applies the previous operator."
        if stk.ops[-1].type == 'BOP':
            y, op, x = stk.vls.pop(), stk.ops.pop(), stk.vls.pop()
            t = op(x, y)
        else:
            if stk.ops[-1].type == 'LOP':
                x, op = stk.vls.pop(), stk.ops.pop()
            else:
                op, x = stk.ops.pop(), stk.vls.pop()
            t = op(x)
        stk.vls.push(t)
        
    def stk_top():
        return stk[-1] if stk else None
    
    def top_is_op(*ops):
        return Is.Op(top := stk_top()) and top.type in ops
    
    def push(x):
        if isinstance(x, Op):
            if x.symbol == '':  # a hidden op given by a space
                push.unsure = True
            
            elif not top_is_op('LOP', 'BOP'):
                while stk.ops:
                    op = stk.ops[-1]
                    if (x.priority > op.priority or
                        x == op and op in backward_bops):
                        break
                    else:
                        squeeze()
                    
            stk.ops.push(x)
            
        else:
            if push.unsure:
                push.unsure = False
                    
                while top_is_op('LOP'):
                    stk.vls.push(x)
                    squeeze()
                    x = stk.vls.pop()
                    
                assert stk.ops.pop().symbol == ''
                
                while top_is_op('ROP'):
                    squeeze()
                    
                x2, x1 = x, stk[-1]
                
                if Is.Attr(x2):
                    push(get)
                elif callable(x1):
                    push(app)
                else:
                    try:
                        idx(x1, x2)
                        push(idx)
                    except:
                        push(mul)
                        
            stk.vls.push(x)

    push.unsure = False
    
    for x in seq:
        push(x)
    while stk.ops:
        squeeze()
    
    value = stk.vls.pop()
    assert not stk
    return value


def LIST(tr):
    lst = []
    for it in tr[1:]:
        if tree_tag(it) == 'UNPACK':
            lst.extend(it[1])
        else:
            lst.append(it)
    return _conv_lst_if_has_kwds(lst)


def _conv_lst_if_has_kwds(lst):
    kwds, items = fsplit(lambda t: tree_tag(t) == 'KWD', lst)
    if kwds:
        return Args(tuple(items), kwds)
    else:
        return tuple(items)
    

def tree_tag(tr):
    if isinstance(tr, list) and tr and type(tr[0]) is str:
        return tr[0]


def ARRAY(tr):
    return Array(tr[1]) if len(tr) == 2 else Matrix(tr[1:])


## these are eval rules which require environment

MAP = Map  # the MAP evaluation rule is the same as Map's constructor


def NAME(tr, env=None):
    if env is None:
        return tr
    name = tr[1]
    try:
        return env[name]
    except KeyError:
        if config.symbolic:
            return Symbol(name)
        else:
            raise NameError(f"unbound name '{name}'")


def OR(tr, env):
    _, a, b = tr
    a = eval_tree(a, env)
    return a if a else eval_tree(b, env)

def IF(tr, env):
    _, a, b = tr
    b = eval_tree(b, env)
    return eval_tree(a, env) if b else b

def AND(tr, env):
    _, a, b = tr
    a = eval_tree(a, env)
    return eval_tree(b, env) if a else a


def KWD(tr, env):
    if is_tree(tr[2]):
        tr[2] = eval_tree(tr[2], env)
        return tr
    else:
        return tr[2]


def AT(tr, env=None):
    _, local, body = tr
    local = eval_tree(local, env)
    if not isinstance(local, Env):
        raise TypeError("'@' not followed by an Env")
    # try:
    return eval_tree(body, env=local)
    # except NameError:
    #     if env is None: raise
    #     return eval_tree(body, env=env)


def STR(tr, env=None):
    s = tr[1]
    if s[0] == '"':
        mode, s = 's', s[1:-1]
    else:
        mode, s = s[0], s[2:-1]
    
    if mode == 'r':
        s = s.replace('\\', '\\\\')
        
    s = format_string(s, env)
    if mode == 'p':
        print(s)
    elif mode in 'rs':
        return s
    else:
        raise SyntaxError('unknown string mode')


def QUOTE(tr, env=None):
    def traverse(tr):
        if is_tree(tr):
            tag = tree_tag(tr)
            if tag == 'UNQUOTE':
                if env is None:
                    raise NameError
                return eval_tree(tr[1], env)
            elif tag == 'NAME':
                s = format_string(tr[1], env)
                return Symbol(s)
            else:
                for i in range(1, len(tr)):
                    tr[i] = traverse(tr[i])
        return tr
    return eval_tree(traverse(tr)[1])
    

def format_string(s, env):
    def subs(match):
        if env is None:
            raise NameError
        s = match[1].strip()
        if s[-1] == '=':
            s = s[:-1]
            eq = 1
        else:
            eq = 0
        val = calc_eval(s, env)
        ss = log.format(val)
        if eq: ss = '%s = %s' % (s, ss)
        return ss
    brace_pattern = '{(.+?)}'
    return re.sub(brace_pattern, subs, s)


def GENER(tr, env):
    bound_vars = set()

    def generate(exp, constraints):
        if constraints:
            constr = constraints[0]
            tag = tree_tag(constr)
            
            if tag == 'DOM':
                _, var, domain = constr
                form = FORM(var, local)
                domain = eval_tree(domain, local, inplace=False)
                
                if form.vars & bound_vars:
                    if form.vars.issubset(bound_vars):
                        val = eval_tree(form, local)
                        if val in domain:
                            yield from generate(exp, constraints[1:])
                    else:
                        raise KeyError('form not fully bound in the constraint')
                else:
                    bound_vars.update(form.vars)
                    for val in domain:
                        bind(form, val, local)
                        yield from generate(exp, constraints[1:])
            else:
                # actually two cases: BIND and others
                # if BIND, a new variable will be defined, since
                # its return value is an Env, which is True in boolean
                # value, the search will always go deeper;
                # otherwise, simply check the boolean value of the
                # constraint and go deeper only when it's True
                if eval_tree(constr, local, inplace=False):
                    yield from generate(exp, constraints[1:])
        else:
            yield eval_tree(exp, local, inplace=False)
            
    _, exp, *constraints = tr
    local = env.child()
    return generate(exp, constraints)

def GENLS(tr, env):
    return tuple(GENER(tr, env))


def ENV(tr, env):
    local = env.child()
    for t in tr[1:]: BIND(t, local)
    return local


def BIND(tr, env):
    tr.pop(0)  # remove tag
    
    if tree_tag(tr[0]) == 'NS':
        env = eval_tree(tr[0][1], env)
        if not isinstance(env, Env):
            raise ValueError('namespace is not an Env')
        tr.pop(0)
        
    if tree_tag(tr[-1]) == 'DOC':
        doc = tr[-1][1]
        tr.pop()
    else:
        doc = None
        
    form, exp = tr
        
    if len(form) > 2:  # defining a map
        exp = ['MAP', form[2], exp]

    form = form[1]
    val = eval_tree(exp, env)
    
    if tree_tag(form) == 'VAR':
        parent_tree, name = form[:-1], form[-1][1]
        grandparent, parent_name = field_attr(parent_tree, env)
        env = grandparent[parent_name]
        if not isinstance(env, Env):
            env = grandparent.child(val=env, name=parent_name)
        form = ['NAME', name]
            
    if doc and tree_tag(form) == 'NAME':
        if not isinstance(val, Env):
            val = Env(name=form[1], val=val)
        if not val.__doc__:
            val.__doc__ = doc
        else:
            val.__doc__ += '\n' + doc
            
    return bind(form, val, env, retval=True)


def bind(form, value, env: Env, overwrite=True, retval=False):
    """
    Args:
        overwrite: whether to overwrite existing bindings
        ret: whether to return the value of the form
    """
    
    def bd(name, val):
        if name in binds:
            raise TypeError(f'multiple bindings of var {name} in the form')
        
        if isinstance(val, Env):
            if val.val is not None and env is not Global:
                val = val.val
                
        if isinstance(val, Map):
            if val.__name__ is None:
                val.__name__ = name
                val.env = env
        elif isinstance(val, Env):
            if env is not Global:
                val = env.child(name=name, binds=val)
            elif val.name == Env.default_name:
                val.name = name
                
        binds[name] = val
            
    binds = {}  # to keep track of new bindings
    eqs = []
    
    tag = tree_tag(form)

    if tag in ['NAME', 'KWD']:
        bd(form[1], value)

    elif tag == 'LIST':
        if not iterable(value):
            raise TypeError('the value bound to a list form is not iterable')
        
        if not Is.Form(form):
            form = FORM(form, env)
            
        if not Is.Args(value):
            value = Args(value)
            
        for var, val in value.match(form):
            if is_tree(var):
                bind(var, val, binds, overwrite=0)
                value._vars -= binds.keys()
            else:
                eqs.append(Eq(var, val))
        
    elif tag == 'EXP':
        eqs.append(Eq(form[1], value))
        
    else:
        raise SyntaxError('invalid form')
    
    if eqs:  # solve equations and bind the results
        if sols := solve(eqs, dict=True):
            if len(sols) > 1:
                log('Info: the equation has multiple solutions (%d)' % len(sols))
                sol_dict = {}
                for sol in sols:
                    for sym, val in sol.items():
                        sol_dict.setdefault(sym, []).append(val)
            else:
                sol_dict = sols[0]
            for sym, val in sol_dict.items():
                bd(str(sym), val)

    for name, val in binds.items():
        if name not in env or overwrite:
            env[name] = val
        else:
            raise KeyError("Multiple bindings of '%s'" % name)

    if retval: return eval_tree(form, env, inplace=False)
    # return Env(val=eval_tree(form, env), binds=binds)


def FORM(tr, env, _nested=False):
    has_keyword = False
    has_unpack = False

    def item_vars(t, i):
        nonlocal has_keyword, has_unpack

        item = t[i]
        tag = tree_tag(item)

        if tag == 'KWD':
            has_keyword = True
            _, var, val = item
            var, val = var[1], eval_tree(val, env)
            t[i] = ['KWD', var, val]
            yield var

        elif tree_tag(item) == 'UNPACK':
            if has_unpack:
                raise SyntaxError('multiple unpacks in the form')
            elif tree_tag(var := item[1]) != 'NAME':
                raise SyntaxError('invalid unpack in the form')
            else:
                has_unpack = True
                t[i] = ['UNPACK', var]
                yield var[1]

        else:
            if has_keyword:
                raise SyntaxError('positional var follows keyword var')

            if tag == 'NAME':
                yield item[1]
            elif tag == 'LIST':
                t[i] = FORM(item, env, _nested=True)
                yield from t[i].vars
            else:
                t[i] = ['EXP', eval_tree(item, env)]

    def form_vars(form):
        for i in range(1, len(form)):
            yield from item_vars(form, i)
            
    if not _nested and tree_tag(tr) != 'FORM':
        tr = ['FORM', tr]
        
    varlist = list(form_vars(tr))
    vars = set(varlist)
    if len(varlist) > len(vars):
        raise SyntaxError('duplicate variables in the form')
    
    form = tr[1] if tree_tag(tr) == 'FORM' else tr
    return Form(form, vars)

        
def field_attr(tr, env):
    if type(tr[1]) is str:
        parent, attr = env, tr[1]
    else:
        parent, attr = tr[:-1], tr[-1][1]
        parent = eval_tree(parent, env) if len(parent) > 1 else env
    return parent, attr


# macro rules

def PHRASE(tr):
    def convert_seq(seq):
        "Converts the phrase into a tree based on its shortcircuit operations."
        for op in shortcircuit_ops:
            opt = ['OP', op]
            if opt in seq:
                i = seq.index(opt)
                lt = convert_seq(seq[:i])
                rt = convert_seq(seq[i+1:])
                return [op.upper(), lt, rt]
            
        seq = parse_op(seq)
        if is_tree(seq): seq = [seq]
        return ['ITEMS'] + seq
    
    def match_unknowns():
        unknowns = set()
        for i, t in enumerate(tr):
            if tree_tag(t) == 'UNKNOWN':
                var = t[1]
                if var != '?':
                    assert '?' not in unknowns
                    # '?' must be the only unknown
                    if not var[1:].isdigit():  # a keyword variable
                        var = var[1:]  # remove the preceding '?'
                unknowns.add(var)
                tr[i] = ['NAME', var]
        return unknowns
        
    def convert_unknown():
        if '?' in unknowns:
            form = ['NAME', '?']
        else:
            ids = [int(x) for x in unknowns if x.isdigit()]
            assert not ids or min(ids) == 1 and max(ids) == len(ids)
            form = ['LIST'] + [['NAME', x] for x in sorted(unknowns)]
        return ['MAP', form, tr]

    unknowns = match_unknowns()
    
    if unknowns:
        return convert_unknown()
    else:
        return convert_seq(tr[1:])
    

def UNKNOWN(tr):
    return PHRASE(['PHRASE', tr])


class OpParser(Parser):
    grammar = semantics
    tests = {'ITEM': lambda tr: tr.tag != 'OP'}
    
    def __init__(self):
        super().__init__()
        for op in ['LOP', 'BOP', 'ROP']:
            self.tests[op] = partial(self.op_test, op)
            
    def op_test(self, op, tr):
        return tr.tag == 'OP' and tr[1] in operators[op]
    
    def parse_atom(self, _tag, tag, phrase):
        if tag == '':
            return binary_ops[''], phrase
        elif tag in self.tests:
            tr = phrase[0]
            if self.tests[tag](tr):
                if tr.tag == 'OP' and \
                    (op := operators[tag].get(tr[1], 0)):
                        tr = op
                return tr, phrase[1:]
            else:
                return self.failed
        else:
            raise SyntaxError('unknown atom %s' % tag)
        
op_parser = OpParser()


def parse_op(seq):
    """
    Check if the seq is in correct syntax, disambiguate operators and add
    hidden binary operators if necessary (representing multiplication etc.).
    """
    def flatten(tree):
        tag = tree_tag(tree)
        if tag in semantics or tag in OpParser.tests:
            return cat(*map(flatten, tree[1:]))
        else:
            return tree

    def cat(*args):
        l = []
        for arg in args:
            l.extend(arg) if type(arg) is list else l.append(arg)
        return l

    tree, rem = op_parser.parse_tag('SEQ', seq)
    if rem or not tree: raise ValueError
    return flatten(tree)


# calc commands
    
def DEL(tr, env=None):
    if env is None:
        env = Global
    for t in tr[1:]:
        field, attr = field_attr(t, env)
        field.delete(attr)

def DIR(tr):
    if tr[-1] == '*':
        items = 'all_items'
        tr.pop()
    else:
        items = 'items'

    if len(tr) == 1:
        field = Global
    else:
        field = tr[1]
        print(f"(dir): {field.dir()}")

    for name, val in getattr(field, items)():
        print(f"{name}: {log.format(val)}")

def LOAD(tr):
    test = '-t' in tr
    verbose = '-v' in tr
    overwrite = '-w' in tr
    path = '%s.cal' % '/'.join(tr[1].split('.'))

    global Global
    current_global = Global
    Global = InitGlobal()  # a new global env
    log.indent += 2
    LOAD.run(path, test, start=0, verbose=verbose)
    log.indent -= 2
    
    for name, val in Global.items():
        if name not in current_global or overwrite:
            current_global[name] = val
        else:
            print(f'name "{name}" not loaded because it is already bound')
    Global = current_global

def IMPORT(tr):
    modname = tr[1]
    verbose = '-v' in tr
    overwrite = '-w' in tr
    env = definitions = {}
    try:
        exec('from modules.%s import export'%modname, env)
        definitions = env['export']
    except ModuleNotFoundError:
        exec('from sympy import %s'%modname, definitions)
    
    for name, val in definitions.items():
        if name not in Global or overwrite:
            if verbose:
                print(f'imported: {name}')
            if callable(val):
                val = Function(val)
            Global[name] = val

def CONF(tr):
    conf = tr[1]
    if conf in ('prec', 'precision'):
        if len(tr) == 2:
            return config.precision
        else:
            config.precision = max(1, tr[2])
    elif conf == 'tolerance':
        if len(tr) == 2:
            return config.tolerance
        else:
            config.tolerance = float(tr[2])
    elif hasattr(config, conf):
        if len(tr) == 2:
            return getattr(config, conf)
        else:
            val = tr[2]
            if val == 'off': val = False
            setattr(config, conf, val)
    else:
        raise ValueError('no such field in the config')
    
def EXIT(tr): raise KeyboardInterrupt

def PYTHON(tr): interact()
    
    
# def hold_tree(eval):
#     @wraps(eval)
#     def wrapped(tree, env=None, *args, **kwds):
#         try:
#             return eval(tree, env, *args, **kwds)
#         except NameError:
#             if env is None: return tree
#             else: raise
#     return wrapped

# @hold_tree
def eval_tree(tree: SyntaxTree, env=None, inplace=True):
    if not is_tree(tree):
        return tree
    if not inplace:
        tree = deepcopy(tree)
        
    tag = tree.tag
    
    if tag in macro_rules:
        tree = macro_rules[tag](tree)
        return eval_tree(SyntaxTree(tree), env)
    
    # simplify subtrees not containing unbound names
    if tag not in eval_rules:
        partial_flag = 0
        for i, t in enumerate(tree):
            if i == 0: continue
            tree[i] = eval_tree(t, env)
            if is_tree(tree[i]) and tag not in delayed_rules:
                partial_flag = 1
        if partial_flag:
            return tree
        
    if tag in eval_rules and (env or tag in subs_rules):
        return eval_rules[tag](tree, env)
    elif tag in subs_rules:
        return subs_rules[tag](tree)
    elif tag in exec_rules:
        return exec_rules[tag](tree)
    else:
        return tree
        # raise TypeError('unknown syntax tree type')


NAME.force_symbol = False
# assign LOAD.run in 'calc.py'
LOAD.run  = NotImplemented
Map.bind = bind
Map.eval  = eval_tree


exec_rules = {name: eval(name) for name in [
    'DIR',      'LOAD',     'IMPORT',   'CONF',
    'EXIT',     'PYTHON'
]}

macro_rules = {name: eval(name) for name in [
    'PHRASE',   'UNKNOWN'
]}

# subs rules that allow application when the evaluation is partial
delayed_rules = {'LIST', 'LINE'}

all_rules = {name: rule for name, rule in
             globals().items() if name.isupper()}

subs_rules, eval_rules = {}, {}

for tag, rule in all_rules.items():
    if tag in exec_rules or tag in macro_rules:
        continue
    
    sig = str(inspect.signature(rule))
    if ',' in sig:
        eval_rules[tag] = rule
        if '=' in sig:
            subs_rules[tag] = rule
    else:
        subs_rules[tag] = rule


if __name__ == "__main__":
    # import doctest
    # doctest.testmod()
    
    while 1:
        exp = input()
        print(calc_eval(exp))