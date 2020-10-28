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
        self.priority = priority
        self.sym = self.func.__name__

    def __call__(self, *args):
        return self.func(*args)

    def __repr__(self):
        return f"{self.type}({self.sym}, {self.priority})"
    
    def __str__(self):
        return self.sym


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

    def __init__(self, tree, env):
        _, form, body = tree
        split_pars(form)
        self.form = form
        self.body = Map.eval(body, env=None)  # simplify the body
        self._str = remake_str(tree)
        self.env = env
    
    def __call__(self, val):
        local = self.env.child()
        Map.match(self.form, val, local)
        return Map.eval(self.body, local)

    def __repr__(self):
        return self._str

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
        
        
def remake_str(tree):
    def rec(tr):
        tag = tr[0]
        if 'DELAY' in tag:
            _, tag = tag.split(':', 1)
        if tag in ('NAME', 'SYM', 'PAR'):
            return tr[1]
        elif tag == 'SEQ':
            return ''.join(map(rec, tr[1:]))
        elif tag[-2:] == 'OP':
            return str(tr[1])
        elif tag[:3] == 'NUM':
            return str(tr[1])
        elif tag == 'FORM':
            _, pars, optpars, extpar = tr
            pars = [rec(par) for par in pars]
            optpars = [f'{rec(optpar)}: {default}' for optpar, default in optpars]
            extpar = [extpar+'~'] if extpar else []
            return "[%s]" % ', '.join(pars + optpars + extpar)
        elif tag == 'PAR_LST':
            split_pars(tr)
            return rec(tr)
        elif tag[-3:] == 'LST':
            return '[%s]' % ', '.join(map(rec, tr[1:]))
        elif tag == 'MAP':
            _, form, exp = tr
            return '%s => %s' % (rec(form), rec(exp))
        elif tag == 'ENV':
            if tr[1][0] == 'MATCH':
                _, form, exp = tr
                return '%s :: %s' % (rec(form), rec(exp))
            else:
                binds = ['%s: %s' % (rec(k), rec(v)) for _, k, v in tr[1:]]
                return '(%s)' % ', '.join(binds)
        elif tag == 'FUNC':
            _, name, form = tr
            return '%s%s' % (rec(name), rec(form))
        else:
            return str(tr)
    return rec(tree)


def split_pars(form):
    pars, opt_pars = [], []
    ext_par = None
    lst = [form] if len(form) == 2 and \
        type(form[1]) is str else form[1:]
    for t in lst:
        if t[0] == 'PAR':
            pars.append(t[1])
        elif t[0] == 'PAR_LST':
            pars.append(split_pars(t))
        elif t[0] == 'OPTPAR':
            opt_pars.append([t[1], Map.eval(t[2])])
        else:
            ext_par = t[1]
    form[:] = ['FORM', pars, opt_pars, ext_par]



if __name__ == "__main__":
    # interact()
    import doctest
    doctest.testmod()
    
