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
        return f"{self.type}_OP({self.func.__name__}, {self.prior})"


class Env(dict):
    def __init__(self, val=None, binds=None, parent=None):
        if binds: self.update(binds)
        self._this = self if val is None else val
        self._super = parent
        self._depth = 0 if parent is None else parent._depth + 1

    def __getattr__(self, name):
        if name in self: 
            return self[name]
        if self._super: 
            return getattr(self._super, name)
        raise KeyError

    def __setattr__(self, name, value):
        if name[0] == '_':
            super().__setattr__(name, value)
        else:
            self[name] = value

    def delete(self, name):
        self.pop(name)

    def __call__(self, val=None, binds=None):
        return Env(val, binds, self)


class function:

    eval = lambda *args: None  # to be set later
    vararg_char = "'"

    def _default_apply(self, *args):
        if not self._fixed_argc:
            if len(args) < self._least_argc:
                raise TypeError('inconsistent number of arguments!')
            args = args[:self._least_argc] + (args[self._least_argc:],)
        elif len(args) != self._least_argc:
            raise TypeError('inconsistent number of arguments!')

        bindings = dict(zip(self._params, args))
        env = self._env.make_subEnv(bindings)
        result = function.eval(self._body, env)

        if config.debug and self._name:
            print(f"{'  '*env.frame}{self._name}({', '.join(map(str, args))}) = {result}")

        return result

    def __init__(self, params, body, env, name=None):
        if params and params[-1][0] == function.vararg_char:
            params[-1] = params[-1][1:].strip()
            self._least_argc = len(params) - 1
            self._fixed_argc = False
        else:
            self._least_argc = len(params)
            self._fixed_argc = True
        self._params = tuple(s for s in params if s and s[0].isalpha())
        if len(self._params) != len(params):
            raise SyntaxError('invalid parameters:', ', '.join(params))
        self._body = body.strip()
        self._env = env
        self._apply = self._default_apply
        self._name = name

    def __call__(self, *args):
        result = self._apply(*args)
        return result

    def compose(self, *funcs):
        """ Return a function that compose this function and several functions. """
        def apply(*args):
            return self._apply(*map(lambda f: f(*args), funcs))
        g = function(self._params, self._body, self._env)
        g._apply = apply
        return g

    @classmethod
    def operator(cls, sym, fallback=None):
        def apply(a, b):
            if callable(a) and callable(b):
                f = function(('a', 'b'), 'a '+sym+' b', Env())
                return f.compose(a, b)
            if callable(a):
                body = sym+' x' if b is None else f'x {sym} {str(b)}'
                return function(['x'], body, Env()).compose(a)
            if callable(b):
                return function(['x'], f'{str(a)} {sym} x', Env()).compose(b)
            return fallback(a, b)
        return apply

    def __repr__(self):
        params = list(self._params)
        if not self._fixed_argc: 
            params[-1] = function.vararg_char + params[-1]
        params = ', '.join(params)
        if self._name: 
            return f'{self._name}({params})'
        elif params:
            return f'function of {params}'
        else:
            return f"function"

    def __str__(self):
        return repr(self) + ': ' + self._body


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


class config:
    "This class holds all configs for the calculator."
    tolerance = 1e-12
    precision = 6
    latex = False
    symbolic = True
    debug = __debug__

