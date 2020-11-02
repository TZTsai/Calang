from utils.deco import log, trace
import config


class stack(list):
    def push(self, obj):
        self.append(obj)
    def peek(self, i=-1):
        try: return self[i]
        except: return None


class Op:
    def __init__(self, type, symbol, function, priority):
        self.type = type
        self.sym = symbol
        self.func = function
        self.priority = priority

    def __call__(self, *args):
        return self.func(*args)

    def __repr__(self):
        return f"{self.type}({self.sym}, {self.priority})"
    
    def __str__(self):
        return self.sym


class Env(dict):
    def __init__(self, val=None, parent=None, name=None, binds=None):
        if val is not None:
            self.val = val
        self.parent = parent
        if not name:
            name = '(%s)' % hex(id(self))[-3:]
        self.name = name
        if binds:
            self.update(binds)
        self.cls = 'env'
    
    def __getitem__(self, name):
        if name == 'this':
            return self
        if name in self:
            return super().__getitem__(name)
        if self.parent:
            return self.parent[name]
        raise KeyError('unbound name: ' + name)

    def dir(self):
        if not self.parent or self.parent.name[0] == '_':
            return self.name
        else:
            return self.parent.dir() + '.' + self.name

    def delete(self, name):
        try: self.pop(name)
        except: print('%s is unbound' % name)

    def child(self, val=None, name=None, binds=None):
        env = Env(val, self, name, binds)
        return env

    def __str__(self):
        return '<%s: %s>' % (self.cls, self.dir())
    
    def __repr__(self):
        content = ', '.join(f'{k} = {v}' for k, v in self.items())
        return f'({content})'
    
    def __bool__(self):
        return True
    
    def all(self):
        d = {'(parent)': self.parent}
        env = self
        while env:
            for k in env:
                if k not in d:
                    d[k] = env[k]
            env = env.parent
        return d


class Attr:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '.'+self.name

    def getFrom(self, env):
        assert isinstance(env, Env), 'not an Env'
        try: return env[self.name]
        except: return getattr(env, self.name)


tree2str = NotImplemented
# a function to restore syntax tree to an expression
# ASSIGN it in format.py

class Map:
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

    # def _all_local(self):
    #     tmp_local = {var: 0 for }
    #     def search(tr):
    #         if type(tr) is list and tr:
    #             if tr[0] == 'NAME':
    #                 return tr[1] in self._vars
    #             else:
    #                 return all(search(t) for t in tr)
    #         else:
    #             return True
    #     return search(self.body)
    
    
    @trace
    def __call__(self, *lst):
        try:  # try to return the memoized result
            return self._memo[lst]
        except:
            if self._memo is NotImplemented:
                try:
                    result = Map.check_local(self, lst)
                    log('Memoizing ', str(self))
                    self._memo = {lst: result}
                    return result
                except:
                    self._memo = None
        
        local = self.parent.child()
        body = self.body
        Map.match(self.form, lst, local)
                
        if self.inherit:
            upper = Map.eval(self.inherit, local, mutable=False)
            assert isinstance(upper, Env), "@ not applied to an Env"
            # local['super'] = upper.parent
            body[1] = local
            env = upper
        else:
            env = local
            
        result = Map.eval(body, env, mutable=False)
        if self.inherit and isinstance(result, Env):
            result.parent = upper
            result.cls = str(self)
            
        # try to memoize result
        try: self._memo[lst] = result
        except: pass
        return result
    
    def __str__(self):
        parent_field = self.parent.dir() + '.' \
            if self.parent.name[0] != '_' else ''
        return parent_field + self.__name__
    
    def __repr__(self):
        return self._repr
    
    def compose(self, func):
        "Enable arithmetic ops on Map."
        return Map(self.form, ['SEQ', func, self.body])


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
    "My own class to indicate that a name is not bound in the environment."
        
        

if __name__ == "__main__":
    # interact()
    import doctest
    doctest.testmod()
    
