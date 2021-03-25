"""
There are four types of rules: substitution, evaluation, execution and macro.

A substitution maps a list of values to another value, not requiring an Env.
An evaluation evaluates a syntax tree to a value, requiring an Env.
An execution is a special rule to control or query the state of the calc.
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
from my_utils.utils import interact

from parse import calc_parse, is_name, is_tree, tree_tag, semantics
from builtin import operators, binary_ops, builtins, shortcircuit_ops
from funcs import is_list, iterable, indexable, apply, Fraction, eq, get_attr
from sympy import Expr, Symbol, Array, Eq, solve
from objects import Env, stack, Op, Attr, Function, Map, Form
from utils import debug
from utils.deco import trace
import config


def InitGlobal():
    Global = Env(name='_global_', parent=Builtins)
    Global.ans = []
    return Global

Builtins = Env(name='_builtins_', binds=builtins)
Global = InitGlobal()


def calc_eval(exp, env=None):
    # suppress output (and recording) if the last character is ';'
    suppress = exp and exp[-1] == ';'
    if suppress: exp = exp[:-1]
    
    # parse the expression into a syntax tree
    tree, rest = calc_parse(exp)
    if rest: raise SyntaxError(f'syntax error in "{rest}"')
    
    if env is None: env = Global 
    result = eval_tree(tree, env)
    # try:  # evaluate the syntax tree
    #     result = eval_tree(tree, Global)
    # except NameError:  # there is an unbound name in exp
    #     if config.symbolic:
    #         # force unbound names to be evaluated to symbols
    #         NAME.force_symbol = True
    #         result = eval_tree(tree, Global)  # retry
    #         NAME.force_symbol = False
    #     else: raise
    
    if result is not None and not suppress:
        # record and return the result
        Global.ans.append(result)
        return result


# substitution rules

def EMPTY(tr): return None

def EVAL(tr): return tr[-1]

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

def ATTR(tr): return Attr(tr[1])

def ANS(tr):
    s = tr[1]
    if all(c == '$' for c in s):
        id = -len(s)
    else:
        try: id = int(s[1:])
        except: raise SyntaxError('invalid history index!')
    return Global.ans[id]
        
def INFO(tr):
    print(tr[1].__doc__)
    
def LINE(tr):
    LINE.comment = tr[2][1]
    return tr[1]

LINE.comment = None


def ITEMS(tr):
    if any(is_tree(t) and tree_tag(t) != 'OP'
           for t in tr[1:]): return tr

    ops = stack()
    vals = stack()
    
    backward_bops = ['(app)']
    
    def squeeze():
        op = ops.pop()
        
        if op.type == 'BOP':
            x = ['APP', op, vals.pop(-2), vals.pop(-1)]
        else:
            x = ['APP', op, vals.pop()]
            
        vals.push(x)
                
    def push(x):
        if isinstance(x, Op):
            while ops:
                op = ops.peek()
                if (x.priority > op.priority or
                    x == op and op.symbol in backward_bops or
                    push.prev is op and op.type in ['BOP', 'LOP']):
                        break
                else: squeeze()
            ops.push(x)
        else:
            vals.push(x)
        push.prev = x

    push.prev = None
    seq = match_ops_in_seq(tr[1:])
    
    for x in seq: push(x)
    while ops: squeeze()
    
    tree = vals.pop()
    assert not vals
    return eval_tree(tree)


def match_ops_in_seq(seq):
    failed = None, None

    tests = {
        'ATTR': lambda x: isinstance(x, Attr),
        'FUNC': callable,
        'LIST': is_list,
        'SEQ': indexable,
        'ITEM': lambda x: not callable(x)
    }

    def parse_seq(seq, phrase):
        result = []
        for atom in seq:
            tree, phrase = parse_atom(atom, phrase)
            if tree is None: return failed
            result.append(tree)
        return result, phrase

    def parse_atom(atom, phrase):
        if not phrase:
            return failed
        elif atom in semantics:
            for alt in semantics[atom]:
                tree, rest = parse_seq(alt, phrase)
                if tree is not None:
                    return [atom]+tree, rest
            return failed
        elif atom in ['LOP', 'BOP', 'ROP']:
            try:
                op = phrase[0]
                assert tree_tag(op) == 'OP'
                sym = op[1]
                ops = operators[atom]
                assert sym in ops
                return ops[sym], phrase[1:]
            except:
                return failed
        elif atom in tests:
            if tests[atom](phrase[0]):
                return phrase[0], phrase[1:]
            else:
                return failed
        else:
            raise SyntaxError

    get = binary_ops['(get)']
    app = binary_ops['(app)']
    ind = binary_ops['.']
    mul = binary_ops['⋅']

    def flatten(tree):
        if tree_tag(tree) in semantics:
            if len(tree) == 2:
                return flatten(tree[1])

            tag = tree_tag(tree)
            args = map(flatten, tree[1:])

            if [tag] in semantics['COMB']:
                return cat(*args)
            elif [tag] in semantics['PAIR']:
                nonlocal get, app, ind, mul
                lv, rv = args
                return cat(lv, eval(tag.lower()), rv)
            else:
                raise SyntaxError
        else:
            return [tree]

    def cat(*args):
        l = []
        for arg in args:
            if type(arg) is list:
                l.extend(arg)
            else:
                l.append(arg)
        return l

    tree, rest = parse_atom('VAL', seq)
    assert not rest
    return flatten(tree)

def APP(tr):  # apply a function
    return tr[1](*tr[2:])

def LIST(tr):
    lst = []
    for it in tr[1:]:
        if is_tree(it):
            tag = tree_tag(it)
            if tag == 'UNPACK':
                lst.extend(it[1])
            elif tag == 'KWD':
                lst.append(it)
            else:
                raise NameError
        else:
            lst.append(it)
    return tuple(lst)

def ARRAY(tr):
    return Array(tr[1:])

SUBARR = LIST


## these are eval rules which require environment

def NAME(tr, env):
    name = tr[1]
    try:
        return env[name]
    except KeyError:
        # if NAME.force_symbol:
        if config.symbolic:
            return Symbol(name)
        else:
            raise NameError(f"unbound symbol '{name}'")

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
    tr[2] = eval_tree(tr[2], env)
    return tr

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
        ss = debug.log.format(val)
        if eq: ss = '%s = %s' % (s, ss)
        return ss
    brace_pattern = '{(.+?)}'
    return re.sub(brace_pattern, subs, s)


def GENER(tr, env):
    def generate(exp, constraints):
        if constraints:
            constr = constraints[0]
            tag = tree_tag(constr)
            
            if tag == 'DOM':
                _, var, domain = constr
                domain = eval_tree(domain, local, inplace=False)
                
                if var[1] in local:
                    # already bound, check if it's in the domain
                    val = local[var[1]]
                    if val in domain:
                        yield from generate(exp, constraints[1:])
                        
                else:  # free variable, traverse all possible values
                    for val in domain:
                        bind(var, val, local)
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
    # place all domain constraints in the front
    # constraints.sort(key=lambda tr: tree_tag(tr) == 'DOM', reverse=True)
    local = env.child()
    return tuple(generate(exp, constraints))


def ENV(tr, env):
    local = env.child()
    for t in tr[1:]: BIND(t, local)
    return local

MAP = Map  # the MAP evaluation rule is the same as Map's constructor


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
            
    form = FORM(form, env)
    return bind(form, val, env)


def bind(form: Form, value, env: Env):
    def bd(name, val):
        if name in binds:
            raise TypeError(f'multiple bindings of var {name} in the form')
        
        if isinstance(val, Env) and val.val is not None:
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
            
    binds = {}
    eqs = []
    tag = tree_tag(form)

    if tag == 'NAME':
        bd(form[1], value)
        
    elif tag == 'LIST':
        if not iterable(value):
            raise TypeError('the value bound to a list form is not iterable')
        
        items = list(value)
        forms = form[1:]
        
        if form.kwd_start is None:
            min_items = len(forms)
        else:
            min_items = form.kwd_start
            
        if min_items > len(items):
            raise ValueError('not enough items to be bound')
        
        if form.unpack_pos is not None:
            min_items -= 1
            unpack_len = len(items) - max(min_items, form.unpack_pos)
        
        i = 0  # variable index
        im = len(forms)
        unpack = []
        
        for item in items:
            if tree_tag(item) == 'KWD':
                _, [_, var], val = item
                assert var in form.vars, f'keyword "{var}" does not exist in the form"'
                bd(var, val)
                unpack_len -= 1
                im -= 1
                
            else:  # the item is a value
                try: tr = forms[i]
                except: raise ValueError('too many items to be bound')
                
                tag = tree_tag(tr)
                if tag == 'UNPACK':
                    assert i == form.unpack_pos
                    if len(unpack) < unpack_len:
                        unpack.append(item)
                    if len(unpack) == unpack_len:
                        bd(tr[1], unpack)
                    else: continue
                elif tag == 'KWD':
                    bd(tr[1], item)
                elif tag is not None:
                    bind(tr, item, binds)
                else:
                    eqs.append(Eq(var, item))
                i += 1
        
        # bind the remaining variables
        for i in range(i, im):
            tr = forms[i]
            tag = tree_tag(tr)
            if tag == 'UNPACK':
                assert i == form.unpack_pos
                bd(tr[1], ())
            elif tag == 'KWD':  # keyword var
                _, var, val = tr
                bd(var, val)
            else:
                raise TypeError
                
    elif tag == 'EXP':
        eqs.append(Eq(form[1], value))
    else:
        raise SyntaxError('invalid form')

    if eqs:  # solve equations and bind the results
        sols = solve(eqs, dict=True)
        if sols:
            if len(sols) > 1:
                debug.log('Info: the equation has %d solutions' % len(sols))
                sol_dict = {}
                for sol in sols:
                    for sym, val in sol.items():
                        sol_dict.setdefault(sym, []).append(val)
            else:
                sol_dict = sols[0]
            for sym, val in sol_dict.items():
                bd(str(sym), val)
            
    env.update(binds)
    return Env(binds=binds)


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
                t[i] = ['UNPACK', var[1]]
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
                t[i] = eval_tree(item, env)

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
    if is_name(tr[1]):
        parent, attr = env, tr[1]
    else:
        parent, attr = tr[:-1], tr[-1][1]
        parent = eval_tree(parent, env) if len(parent) > 1 else env
    return parent, attr


# macro rules

def PHRASE(tr):
    def convert_shortcirc(phrase):
        "Converts the phrase into a tree based on its shortcircuit operations."
        for op in shortcircuit_ops:
            opt = ['OP', op]
            if opt in phrase:
                i = phrase.index(opt)
                lt = convert_shortcirc(phrase[:i])
                rt = convert_shortcirc(phrase[i+1:])
                return [op.upper(), lt, rt]
        return ['ITEMS'] + phrase

    unknowns = set()
    for i, t in enumerate(tr):
        if tree_tag(t) == 'UNKNOWN':
            var = t[1]
            if var != '?':
                # '?' must be the only unknown
                assert '?' not in unknowns
                if not var[1:].isdigit():  # a keyword variable
                    var = var[1:]  # remove the preceding '?'
            unknowns.add(var)
            tr[i] = ['NAME', var]
    if unknowns:
        if '?' in unknowns:
            form = ['NAME', '?']
        else:
            ids = [int(x) for x in unknowns if x.isdigit()]
            assert not ids or min(ids) == 1 and max(ids) == len(ids)
            form = ['LIST'] + [['NAME', x] for x in sorted(unknowns)]
        return ['MAP', form, tr]

    return convert_shortcirc(tr[1:])


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
        print(f"{name}: {debug.log.format(val)}")

def LOAD(tr):
    test = '-t' in tr
    verbose = '-v' in tr
    overwrite = '-w' in tr
    path = '%s.cal' % '/'.join(tr[1].split('.'))

    global Global
    current_global = Global
    Global = InitGlobal()  # a new global env
    debug.log.indent += 2
    LOAD.run(path, test, start=0, verbose=verbose)
    debug.log.indent -= 2
    
    if overwrite:
        current_global.update(Global)
    else:
        for name in Global:
            if name not in current_global:
                current_global[name] = Global[name]
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
    
    
def hold_tree(eval):
    @wraps(eval)
    def wrapped(tree, env=None, *args, **kwds):
        try:
            return eval(tree, env, *args, **kwds)
        except NameError:
            if env is None: return tree
            else: raise
    return wrapped

@hold_tree
def eval_tree(tree, env=None, inplace=True):
    if not is_tree(tree):
        return tree
    if not inplace:
        tree = deepcopy(tree)
        
    tag = tree_tag(tree)
    
    if tag in macro_rules:
        tree = macro_rules[tag](tree)
        return eval_tree(tree, env)
    
    if tag not in eval_rules:
        partial_flag = False
        for i, t in enumerate(tree):
            tree[i] = eval_tree(t, env)
            if is_tree(tree[i]) and tag not in delayed_rules:
                partial_flag = True
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
    'PHRASE'
]}

# subs rules that allow application when there is partial evaluation
delayed_rules = {'LIST', 'ITEMS'}

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
    import doctest
    doctest.testmod()
