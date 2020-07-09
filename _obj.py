from myutils import interact


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
    '''
    >>> G = Env(name='global')
    >>> G.e = Env(1)
    >>> G.e
    <env: global.e>
    >>> G.e.a = 3
    >>> G.e.a
    3
    >>> f = G.e.child([2], f=5)
    >>> f
    <env: global.e.(local)>
    >>> f.a
    3
    >>> f.all()
    {'_parent_': <env: global.e>, 'f': 5, 'a': 3, 'e': <env: global.e>}
    >>> str(f)
    '(f: 5)'
    '''
    def __init__(self, val=None, parent=None, name:str='(local)', **binds):
        if val is not None: self._val = val
        self._parent = parent
        self._name = name

        for key in binds:
            assert key not in ('val', 'parent', 'name'), 'invalid kwarg'
        for name in binds:
            self.define(name, binds[name])
    
    def __getattr__(self, name):
        if name in self:
            return self[name]
        if self._parent:
            return getattr(self._parent, name)
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name[0] == '_':
            super().__setattr__(name, value)
        else:
            self.define(name, value)

    def define(self, name, value, overwrite=True):
        if name in self and not overwrite:
            raise AssertionError('name conflict in '+repr(self))
        self[name] = value
        if isinstance(value, Env) and value is not self:
            value._parent = self
            value._name = name

    @property
    def name(self):
        if not self._parent or not self._parent.name:
            return self._name
        else:
            return self._parent.name + '.' + self._name

    def delete(self, name):
        try: self.pop(name)
        except: pass

    def child(self, val=None, **binds):
        env = Env(val, self, **binds)
        return env

    def __repr__(self):
        return '<env: %s>' % self.name
    
    def __str__(self):
        content = ', '.join(str(k)+': '+repr(v) for k, v in self.items())
        return '('+content+')'
    
    def all(self):
        d = {'_parent_': self._parent}
        env = self
        while env:
            for k in env:
                if k not in d: d[k] = env[k]
            env = env._parent
        return d


class Attr:
    '''
    >>> attr = Attr('aa')
    >>> f = lambda: 0
    >>> f.aa = 'zero'
    >>> attr.getFrom(f)
    'zero'
    >>> e = Env()
    >>> e.aa = 'evil'
    >>> attr.getFrom(e)
    'evil'
    '''
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '.'+self.name

    def getFrom(self, obj):
        return getattr(obj, self.name)

    @classmethod
    def adjoin(cls, obj, attr):
        assert isinstance(attr, cls)
        return getattr(obj, attr.name)


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
        Map.match(val, self.form, local)
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

    def composed(self, func):
        body = ['SEQ', func, self.body]
        return Map(self.form, body)


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
    