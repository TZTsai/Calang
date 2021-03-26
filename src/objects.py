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
        
        
class Function:
    broadcast = lambda f: NotImplemented
    compose = lambda f, g: NotImplemented

    def __init__(self, func):
        self._func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
                
    def __repr__(self):
        return self.__name__
    
    def __call__(self, *args):
        return self._func(*args)
    
    
class Op(Function):
    def __init__(self, type, symbol, function, priority):
        super().__init__(function)
        self.type = type
        self.symbol = symbol
        self.priority = priority
        self.broadcast = True
        
    def __call__(self, *args):
        try:
            return super().__call__(*args)
        except TypeError:
            if not self.broadcast: raise
            
        call = self.__call__
        
        try: return tuple(map(call, *args))
        except TypeError: pass
        
        try: return Function.broadcast(call)(*args)
        except TypeError: raise

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
        
    def __call__(self, args):
        try:
            return self._func(*args)
        except TypeError:
            return self._func(args)
        
    
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
                    for it in tr[1:]:
                        collect_vars(it)
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
        try: self[:] = form
        except: self[:] = ['EXP', form]
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
    default_name = '(loc)'
    
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
    
