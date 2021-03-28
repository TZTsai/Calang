import re
from sympy import Symbol
from utils.debug import log, trace
from utils.funcs import *
import config


class stack(list):
    
    def push(self, obj):
        self.append(obj)
        
    def peek(self, i=-1):
        try: return self[i]
        except: return None
        
        
class SyntaxTree(list):
    tag_pattern = re.compile('[A-Z_:]+')

    def __init__(self, tree):
        assert type(tree) in [list, tuple]
        assert tree and type(tree[0]) is str
        assert self.tag_pattern.match(tree[0])
        self[:] = tree
    
    @property
    def tag(self):
        return self[0]
    
    @property
    def body(self):
        return self[1:]

    def __getitem__(self, index):
        t = super().__getitem__(index)
        if index > 0 and not is_tree(t):
            t = SyntaxTree(t)
            self[index] = t
        return t

    def __setitem__(self, key, value):
        if key == 0:
            raise IndexError('cannot change the tag of a syntax tree')
        super().__setitem__(key, value)
        
    
def is_tree(obj):
    return isinstance(obj, SyntaxTree)

def tree_tag(obj):
    return obj.tag if is_tree(obj) else None


class Function:
    broadcast = lambda f: NotImplemented
    proc_in = lambda x: NotImplemented
    proc_out = lambda y: NotImplemented

    def __init__(self, func):
        self._func = func
        self.broadcast = False
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
                
    def __repr__(self):
        return self.__name__
    
    def func(self, *args):
        args = Function.proc_in(args)
        ret = self._func(*args)
        return Function.proc_out(ret)
    
    def __call__(self, *args):
        try:
            return self.func(*args)
        except TypeError:
            if not self.broadcast: raise
        try:
            return Function.broadcast(self.func)(*args)
        except ValueError:
            return deepmap(self.func, args)
    
    
class Op(Function):
    bindings = {}
    
    def __new__(cls, *args, **kwds):
        if len(args) == 1 and not kwds:
            return cls.bindings[args[0]]
        else:
            return object.__new__(cls)
    
    def __init__(self, *args, amb=None):
        if len(args) == 1: return
        type, symbol, function, priority = args
        super().__init__(function)
        self.type = type
        self.symbol = symbol
        self.priority = priority
        self.amb = amb
        
    def __call__(self, *args):
        try:
            if self.type == 'BOP':
                assert len(args) == 2
            else:
                assert len(args) == 1
        except:
            if self.amb:
                return Function.__call__(self.amb, *args)
            else:
                raise TypeError('incorrect number of arguments')
        return super().__call__(*args)

    def __repr__(self):
        return f"{self.type}({self.symbol}, {self.priority})"
    
    def __eq__(self, other):
        return isinstance(other, Op) and self.__dict__ == other.__dict__

    def __str__(self):
        return self.symbol


class Builtin(Function):
    def __init__(self, func, name):
        super().__init__(func)
        self.__name__ = name
        
    def __call__(self, val):
        try:
            return super()(*val)
        except:
            return super()(val)
        
    
deparse = lambda tree: NotImplemented
# assign it in format.py

class Map(Function):
    bind = lambda form, val, env: NotImplemented
    eval = lambda tree, env, inplace: NotImplemented

    def __init__(self, tree, env):
        _, form, body = tree
        if tree_tag(form) != 'FORM':  # ensure it is evaluated as a form
            form = ['FORM', form]
            
        self.form = Map.eval(form, env)
        self.body = Map.eval(body, None)
        self.env = env
        self._pars = form[-1]
        self._memo = {} if self.check_local() else None
        self.__name__ = None
        self.__doc__ = None
        
        if self.form[0] not in ['LIST', 'NAME']:
            self._form_repr = f'({repr(self.form)})'
        else:
            self._form_repr = repr(self.form)
        self._body_repr = deparse(self.body)
        
    @trace
    def _func(self, val):
        try: return self._memo[val]
        except: pass
        
        local = self.env.child()
        Map.bind(self.form, val, local)
        result = Map.eval(self.body, local, inplace=False)
            
        try: self._memo[val] = result
        except: pass
        return result
    
    def check_local(self):
        "Check whether the map depends on outside variables."
        def collect_vars(tr):
            if is_tree(tr):
                if tr[0] == 'NAME':
                    vars.add(tr[1])
                else:
                    for t in tr[1:]:
                        collect_vars(t)
        vars = set()
        collect_vars(self.body)
        return vars.issubset(self.form.vars)
    
    def __str__(self):
        return '%s → %s' % (self._form_repr, self._body_repr)

    def __repr__(self):
        if self.__name__:
            return self._path_repr()
        else:
            return f'({self})'
    
    def _path_repr(self):
        if self.env.name[0] == '_':
            path = ''
        else:
            path = self.env.dir()
        if self.__name__:
            if path: path += '.'
            path += self.__name__
        elif path:
            path = '@' + path
        return path
    
    
class Form(list):
    def __init__(self, form, vars):
        self[:] = form
        self.vars = vars
        self.unpack_pos = self.find_first_tag('UNPACK')
        self.kwd_start = self.find_first_tag('KWD')
        self._repr = None
        
    def find_first_tag(self, tag):
        if self[0] == 'LIST':
            for i, item in enumerate(self[1:]):
                if tree_tag(item) == tag:
                    return i
        return None
    
    def __repr__(self):
        return deparse(self) if self._repr is None else self._repr
    

class Env(dict):
    default_name = '(env)'
    
    def __init__(self, val=None, parent=None, name=None,
                 binds=None, hide_parent=True):
        self.val = val
        if parent:
            if name: parent[name] = self
            self.parent = parent
        else:
            self.parent = None
        if name:
            self.name = name
        else:
            self.name = self.default_name
        if binds:
            self.update(binds)
    
    def __getitem__(self, name):
        if isinstance(name, Symbol):
            name = str(name)
        if name in self:
            return super().__getitem__(name)
        if name == 'upper':
            return self.parent
        if self.parent:
            return self.parent[name]
        raise KeyError('unbound name: ' + name)
    
    def __iter__(self):
        raise TypeError('Env is not iterable')
    
    def all_items(self):
        yield from self.items()
        if self.parent:
            yield from self.parent.all_items()
    
    def dir(self):
        try:
            assert self.parent.name[0] != '_'
            return self.parent.dir() + '.' + self.name
        except:
            return self.name
    
    def delete(self, name):
        try: self.pop(name)
        except: print('%s is unbound' % name)

    def child(self, val=None, name=None, binds=None):
        return Env(val, self, name, binds)

    def __str__(self):
        return '(%s)' % ', '.join(f'{k} = {log.format(v)}'
                                  for k, v in self.items())
    
    def __repr__(self):
        return self.dir()
    
    def __bool__(self):
        return True
    
    
class Args(Env):
    
    def __init__(self, args, kwds=None):
        if kwds is None: kwds = {}
        self._vars = set()
        super().__init__(val=args, binds=kwds)
        
    def match(self, form: Form):
        vars = form[1:]
        args = self.val
        
        kwd_start = form.kwd_start or len(vars)
        min_items = kwd_start
            
        if (k := form.unpack_pos) is not None:
            min_items -= 1
            unpack_len = len(args) - max(min_items, k)
        else: k = -1
        
        if min_items > len(args):
            raise TypeError('not enough arguments')
        
        # remove the unbound vars in self._vars after each yield
        self._vars.update(form.vars)
        
        i = j = 0  # index of the current var and current arg
        
        while j < len(args) or i <= k:
            if i == k:  # UNPACK
                j = i + unpack_len
                yield vars[i][1], args[i:j]
            else:  # NAME or LIST
                yield vars[i], args[j]
                j += 1
            i += 1
        
        # bind default keywords if necessary
        for kwd in vars[kwd_start:]:
            _, var, defval = kwd  # not good: leaky abstraction
            if var in self._vars:
                yield kwd, defval
                
        if self._vars:
            if len(self._vars) == 1:
                raise NameError("unbound variable %s in the list form" % self._vars.pop())
            else:
                raise NameError("unbound variables %s in the list form" % self._vars)


class Type(type):
    def __init__(self, object_or_name, bases, dict):
        super().__init__(object_or_name, bases, dict)
    

class Attr:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '.'+self.name


class Range:
    def __init__(self, first, last, step=None, second=None):
        self.first = first
        self.second = second
        self.last = last
        self._step = step
        
        # some checks
        assert step is None or second is None
        if self.step == 0: raise ValueError('range step is 0')
        
    @property
    def step(self):
        if self.second:
            return self.second - self.first
        elif self._step is None:
            return 1 if self.first < self.last else -1
        else:
            return self._step
        
    def __new__(cls, first, last, step=None, second=None):
        obj = super().__new__(cls)
        obj.__init__(first, last, step, second)
        if (obj.last - obj.first) * obj.step <= 0:
            return ()  # empty range
        else:
            return obj

    def __repr__(self):
        items = [self.first, self.last, self.step]
        if self.step in (1, -1): items.pop()
        return ':'.join(map(str, items))
        
    def __iter__(self):
        step = self.step
        first, stop = self.first, self.last + step
        return iter(range(first, stop, step))
    
    def __getitem__(self, i):
        return self.first + i * self.step
    
    def __hasitem__(self, x):
        if self.step > 0:
            if x < self.first or x > self.last:
                return False
        else:
            if x > self.first or x < self.last:
                return False
        return (x - self.first) % self.step == 0

    def __eq__(self, other):
        if not isinstance(other, Range): return False
        return all(getattr(self, a) == getattr(other, a)
                   for a in ['first', 'last', 'step'])


if __name__ == "__main__":
    # interact()
    import doctest
    doctest.testmod()
    
