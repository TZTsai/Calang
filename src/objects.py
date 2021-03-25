from sympy import Symbol
from utils.deco import log, trace
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
        try: return self._func(*args)
        except TypeError: return self._func(args)
        
    
    
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

    def __repr__(self):
        return f'<builtin: {self.__name__}>'

    
tree2str = NotImplemented
# a function to restore syntax tree to an expression
# ASSIGN it in format.py

class Map(Function):
    bind = lambda form, val, env: NotImplemented
    eval = lambda tree, env, mutable: NotImplemented
    builtins = None

    def __init__(self, tree, env):
        _, form, body = tree
        # if body[0] == 'INHERIT':
        #     self.inherit = body[1]
        #     body = ['CLOSURE', ..., body[2]]
        # else:
        #     self.inherit = None
        #     body = Map.eval(body, None)  # simplify the body
        self.form = Form(form, env)
        self.body = Map.eval(body, None)
        self.parent = env
        self._pars = form[-1]
        self._repr = tree2str(tree)
        self.__name__ = None
        self.__doc__ = self._repr
        self._memo = NotImplemented

    @trace
    def _func(self, val):
        try:  # try to return the memoized result
            return self._memo[val]
        except:
            if self._memo is NotImplemented:
                try:
                    self._memo = {}
                    result = self.check_local(val)
                    assert type(result) not in [Env, Map]
                    return result
                except (UnboundName, AssertionError):
                    self._memo = None
        
        local = self.parent.child()
        Map.bind(self.form, val, local)
                
        if self.inherit:
            upper = Map.eval(self.inherit, local, mutable=False)
            assert isinstance(upper, Env), "@ not applied to an Env"
            self.body[1] = local
            env = upper
        else:
            env = local
            
        result = Map.eval(self.body, env, mutable=False)
        # if self.inherit and isinstance(result, Env):
        #     result.parent = upper
        #     result.cls = str(self)
            
        # try to memoize result
        try: self._memo[val] = result
        except: pass
        return result
    
    def check_local(self, val):
        "Try to apply on $val to test if self does not depend on outside variables."
        local = Map.builtins.child()
        local[self.__name__] = self
        Map.bind(self.form, val, local)
        # if self.inherit: self.body[1] = local
        return Map.eval(self.body, local, False)
    
    def __str__(self):
        path = self.parent.dir()
        if not path or path[0] == '_':  # hidden
            where = ''
        else:
            where = ' in %s' % path
        return '<map%s: %s>' % (where, self._repr)
    
    def __repr__(self):
        if self.__name__:
            return self.__name__
        else:
            return '(%s)' % self._repr
    
    def compose(self, func):
        "Enable arithmetic ops on Map."
        return Map(self.form, ['SEQ', func, self.body])
    
    
class Form(list):
    getvars = lambda form, env: NotImplemented
    
    def __init__(self, form, env=None):
        if form[0] == 'FORM':
            assert len(form) == 2
        else:
            form = ['FORM', form]
            
        self[:] = form[1]
        
        if env is not None:
            self.set_vars(Form.getvars(form, env))

        self.unpack_pos = self.find_first_tag('UNPACK')
        self.kwd_start = self.find_first_tag('KWD')
        
    def set_vars(self, vars):
        vars = list(vars)
        self.vars = set(vars)
        if len(vars) > len(self.vars):
            raise SyntaxError('duplicate variables in the form')
        
    def find_first_tag(self, tag):
        if self[0] == 'LIST':
            for i, item in enumerate(self):
                if type(item) is list and item[0] == tag:
                    return i
        return None
    

class Env(dict):
    default_name = '(loc)'
    
    def __init__(self, val=None, parent=None, name=None, binds=None):
        self.val = val
        if parent:
            if name is not None:
                parent[name] = self
            if parent.name[0] != '_':
                self.parent = parent
            else:
                self.parent = None
        if name is None:
            self.name = self.default_name
        else:
            self.name = name
        if binds:
            self.update(binds)
        # self.cls = 'env'
    
    def __getitem__(self, name):
        if name in self:
            return super().__getitem__(name)
        if name == 'upper':
            return self.parent
        if self.parent:
            return self.parent[name]
        raise KeyError('unbound name: ' + name)
    
    def __iter__(self):
        raise TypeError('Env is not iterable')
    
    def dir(self):
        return (self.parent.dir() + '.' if self.parent else '') + self.name
    
    def dict_str(self):
        return '(%s)' % ', '.join(f'{k} = {log.format(v)}'
                                  for k, v in self.items())

    def delete(self, name):
        try: self.pop(name)
        except: print('%s is unbound' % name)

    def child(self, val=None, name=None, binds=None):
        return Env(val, self, name, binds)

    def __str__(self):
        # return '<%s: %s>' % (self.cls, self.dir())
        if self.name == self.default_name:
            return self.dir()[:-len(self.default_name)] + self.dict_str()
        else:
            return self.dir() + ':' + self.dict_str()
    
    def __repr__(self):
        return self.dict_str()
    
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

    def __eq__(self, other):
        if not isinstance(other, Range): return False
        return all(getattr(self, a) == getattr(other, a)
                   for a in ['first', 'last', 'step'])
        

class Enum:
    def __init__(self, iterable):
        self.it = iterable
        
    def __iter__(self):
        return enumerate(self.it)
    
    def __repr__(self):
        return '<enum: %s>' % self.it


class UnboundName(NameError):
    "An error to indicate that a name is not bound in the environment."
    
# class OperationError(RuntimeError):
#     "An error to indicate that the interpreted operation cannot be applied."
        
        

if __name__ == "__main__":
    # interact()
    import doctest
    doctest.testmod()
    
