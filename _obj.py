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

    def __call__(self, *args):
        return self.func(*args)

    def __repr__(self):
        return f"{self.type}({self.func.__name__}, {self.prior})"


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
    {'_parent_': <env: global.e>, 'VAL': [2], 'f': 5, 'a': 3, 'e': <env: global.e>}
    >>> str(f)
    '(VAL: [2], f: 5)'
    '''
    def __init__(self, val=None, parent=None, name:str='(local)', **binds):
        if val is not None: self.VAL = val
        self._parent = parent
        self._name = name
        self.update(binds)
    
    def __getattr__(self, name):
        if name in self:
            return self[name]
        if self._parent:
            return getattr(self._parent, name)
        return super().__getattribute__(name)

    def define(self, name, value, overwrite=True):
        if name[0] == '_':      # attrs beginning with '_' is hidden
            setattr(self, name, value)
        else:
            if name in self and not overwrite:
                raise AssertionError('name conflict in '+repr(self))
            self[name] = value
            if isinstance(value, Env) and value is not self:
                value._parent = self
                value._name = name

    @property
    def name(self):
        if not self._parent: return self._name
        return self._parent.name + '.' + self._name

    def delete(self, name):
        self.pop(name)

    def child(self, val=None, **binds):
        env = Env(val, self)
        env.update(binds)
        return env

    def __repr__(self):
        return '<env: %s>' % self.name
    
    def __str__(self):
        content = ', '.join(repr(k)+': '+repr(v) for k, v in self.items())
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
        self.body = Map.eval(body, env=None)  # simplify the body
        self.env = env
        self.__name__ = repr(self)
    
    def __call__(self, val):
        local = self.env.child()
        Map.match(val, self.form, local)
        return Map.eval(self.body, local)

    def __repr__(self):
        return f"{self.form} -> {self.body}"

    def composed(self, func):
        body = ['SEQ', func, self.body]
        return Map(self.form, body)


class Range:
    def __init__(self, first, last, second=None):
        self.first = first
        self.second = second
        self.last = last
        step = 1 if second is None else second - first
        self._range = range(first, last+1, step)

    def __repr__(self):
        if self.second is None:
            return f'{self.first}~{self.last}'
        else:
            return '..'.join(map(str, [self.first, self.second, self.last]))
        
    def __iter__(self):
        return iter(self._range)

    def __eq__(self, other):
        if not isinstance(other, Range): return False
        return (self.first == other.first and self.second == other.second
                and self.last == other.last)


class config:
    "This class holds all configs for the calculator."
    tolerance = 1e-12
    precision = 6
    latex = False
    symbolic = False
    debug = 0



if __name__ == "__main__":
    import doctest
    doctest.testmod()
    