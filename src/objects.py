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

    def __init__(self, func):
        self.f = func
        # self.bc = True  # whether allow broadcast
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
                
    def __repr__(self):
        return self.__name__
    
    def __call__(self, args):
        try: return self.f(*args)
        except: pass
        try: return self.f(args)
        except TypeError: pass
        try: return tuple(map(self.f, *args))
        except TypeError: pass
        try: return Function.broadcast(self.__call__)(args)
        except TypeError: raise OperationError
    
    
class Op(Function):
    def __init__(self, type, symbol, function, priority):
        super().__init__(function)
        self.type = type
        self.symbol = symbol
        self.priority = priority

    def __repr__(self):
        return f"{self.type}({self.symbol}, {self.priority})"

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
    match  = lambda val, form, parent: NotImplemented
    eval   = lambda tree, parent, mutable: NotImplemented
    check_local = lambda map, lst: NotImplemented

    def __init__(self, tree, env):
        _, form, body = tree
        form = Map.eval(form, env)      # eval optpars
        if body[0] == 'INHERIT':
            self.inherit = body[1]
            body = ['CLOSURE', ..., body[2]]
        else:
            self.inherit = None
            body = Map.eval(body, None)  # simplify the body
            
        self.form = form
        self.body = body
        self.parent = env
        self._pars = form[-1]
        self._repr = tree2str(tree)
        self.__name__ = '(map)'
        self.__doc__ = self._repr
        self._memo = NotImplemented

    def f(self, val):
        try:  # try to return the memoized result
            return self._memo[val]
        except:
            if self._memo is NotImplemented:
                try:
                    self._memo = {}
                    result = Map.check_local(self, val)
                    if type(result) in [Env, Map]:
                        raise RuntimeError  # env dependent result
                    return result
                except RuntimeError:
                    self._memo = None
        
        local = self.parent.child()
        body = self.body
        Map.match(self.form, val, local)
                
        if self.inherit:
            upper = Map.eval(self.inherit, local, mutable=False)
            assert isinstance(upper, Env), "@ not applied to an Env"
            body[1] = local
            env = upper
        else:
            env = local
            
        result = Map.eval(body, env, mutable=False)
        if self.inherit and isinstance(result, Env):
            result.parent = upper
            result.cls = str(self)
            
        # try to memoize result
        try: self._memo[val] = result
        except: pass
        return result
    
    @trace
    def __call__(self, val):
        return super().__call__(val)
    
    def __str__(self):
        path = self.parent.dir()
        if path[0] == '_':  # hidden
            where = ''
        else:
            where = ' in %s' % path
        return '<map%s: %s>' % (where, self._repr)
    
    def __repr__(self):
        if self.__name__[0] != '(':
            return self.__name__
        else:
            return '(%s)' % self._repr
    
    def compose(self, func):
        "Enable arithmetic ops on Map."
        return Map(self.form, ['SEQ', func, self.body])


class Env(dict):
    def __init__(self, val=None, parent=None, name=None, binds=None):
        if val is not None:
            self.val = val
        self.parent = parent
        self.name = name
        if binds:
            self.update(binds)
        self.cls = 'env'
    
    def __getitem__(self, name):
        if name in self:
            return super().__getitem__(name)
        if self.parent:
            return self.parent[name]
        raise KeyError('unbound name: ' + name)

    def dir(self):
        prefix = '' if not self.parent or self.parent.name[0] == '_' \
            else self.parent.dir() + '.'
        suffix = self.name if self.name else '(%s)' % ', '.join(
            f'{log.format(k)} = {log.format(v)}' for k, v in self.items())
        return prefix + suffix

    def delete(self, name):
        try: self.pop(name)
        except: print('%s is unbound' % name)

    def child(self, val=None, name=None, binds=None):
        env = Env(val, self, name, binds)
        return env

    def __str__(self):
        return '<%s: %s>' % (self.cls, self.dir())
    
    def __repr__(self):
        return self.dir().rsplit('.', 1)[-1]
    
    def __bool__(self):
        return True
    

class Attr:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '.'+self.name

    def getFrom(self, env):
        try: return env[self.name]
        except: return getattr(env, self.name)
        

class Range:

    class Iter:
        def __init__(self, first, last, step):
            self.current = first
            self.last = last
            self.step = step

        def __next__(self):
            current = self.current
            if (self.step > 0 and current > self.last) or \
                (self.step < 0 and current < self.last):
                raise StopIteration
            self.current += self.step
            return current

    def __init__(self, first, last, second=None):
        self.first = first
        self.second = second
        self.last = last
        self.step = 1 if second is None else second - first
        if self.step == 0: raise ValueError('the step of this range is 0')

    def __repr__(self):
        items = [self.first, self.second, self.last]
        if self.second is None: items.pop(1)
        return '..'.join(map(str, items))
        
    def __iter__(self):
        return Range.Iter(self.first, self.last, self.step)

    def __eq__(self, other):
        if not isinstance(other, Range): return False
        return (self.first == other.first and self.second == other.second
                and self.last == other.last)


class UnboundName(NameError):
    "An error to indicate that a name is not bound in the environment."
    
class OperationError(RuntimeError):
    "An error to indicate that the interpreted operation cannot be applied."
        
        

if __name__ == "__main__":
    # interact()
    import doctest
    doctest.testmod()
    
