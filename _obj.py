class stack(list):
    def push(self, obj):
        self.append(obj)
    def peek(self, i=-1):
        try: return self[i]
        except: return None


class Op:
    def __init__(self, type, function, priority):
        self.type = type
        self.func = function
        self.prior = priority
        self.__name__ = self.func.__name__

    def __call__(self, *args):
        return self.func(*args)

    def __repr__(self):
        return f"{self.type}({self.__name__}, {self.prior})"


class Env(dict):
    def __init__(self, val=None, parent=None, name='', **binds):
        if val is not None:
            self.val = val
        self.parent = parent
        self.name = name
        for name in binds:
            self[name] = binds[name]
    
    def __getitem__(self, name):
        if name in self:
            return super().__getitem__(name)
        if self.parent:
            return self.parent[name]
        raise KeyError('unbound name: ' + name)

    # def define(self, name, value, overwrite=True):
    #     if name in self and not overwrite:
    #         raise AssertionError('name conflict in ' + repr(self))
    #     self[name] = value
    #     if isinstance(value, Env) and value is not self:
    #         value.parent = self
    #         value.name = name
            
    def dir(self):
        if not self.parent or not self.parent.name:
            return self.name
        else:
            return self.parent.dir() + '.' + self.name

    def delete(self, name):
        try: self.pop(name)
        except: raise NameError('unbound name:', name)

    def child(self, val=None, name='(local)', **binds):
        env = Env(val, self, name, **binds)
        return env

    def __repr__(self):
        return '<env: %s>' % self.dir()
    
    def __str__(self):
        content = ', '.join(f'{k}: {v}' for k, v in self.items())
        return f'({content})'
    
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
        return env[self.name]

    @classmethod
    def adjoin(cls, env, attr):
        assert isinstance(env, Env)
        assert isinstance(attr, Attr)
        return env[attr.name]


class Map:
    match = lambda val, form, env: NotImplemented
    eval  = lambda tree, env=None: NotImplemented

    def __init__(self, form, body, env):
        self.form = form
        self._form_str = Map.form_str(form)
        self.body = Map.eval(body, env=None)  # simplify the body
        self.env = env
        self.__name__ = repr(self)
    
    def __call__(self, val):
        local = self.env.child()
        Map.match(self.form, val, local)
        return Map.eval(self.body, local)

    def __repr__(self):
        return f"{self._form_str} => {self.body}"

    @staticmethod
    def form_str(form):
        _, pars, optpars, extpar = form
        pars = [Map.form_str(par) if type(par) is list else par
                for par in pars]
        optpars = [f'{optpar}: {default}' for optpar, default in optpars]
        extpar = ['*'+extpar] if extpar else []
        return f"[{', '.join(pars + optpars + extpar)}]"

    # def composed(self, func):
    #     body = ['SEQ', func, self.body]
    #     return Map(self.form, body)


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



if __name__ == "__main__":
    # interact()
    import doctest
    doctest.testmod()
    
