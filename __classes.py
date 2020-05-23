from copy import copy


class Stack:
    def __init__(self):
        self.lst = []

    def push(self, obj):
        self.lst.append(obj)

    def pop(self):
        assert(not self.empty())
        return self.lst.pop()

    def peek(self):
        assert(not self.empty())
        return self.lst[-1]

    def empty(self):
        return self.lst == []

    def clear(self):
        self.lst = []


class Op:
    def __init__(self, type, function, priority):
        self.type = type
        self.function = function
        self.priority = priority

    def isStopMark(self):
        return self.type == 'stop'

    def __call__(self, *args):
        return self.function(*args)


class CalcMachine:
    def __init__(self):
        self.vals = Stack()
        self.ops = Stack()

    def __calc(self):  # carry out a single operation
        op = self.ops.pop()
        if op.isStopMark():
            return 'stop'
        elif op.type == 'uni_l':
            self.vals.push(op(self.vals.pop()))
        else:
            n2 = self.vals.pop()
            n1 = self.vals.pop()
            self.vals.push(op(n1, n2))

    def begin(self):
        self.ops.push(Op('stop', None, -99))
        # add a stop_mark in op_stack

    def reset(self):
        self.ops.clear()
        self.vals.clear()

    def calc(self):
        # calculate until the stack is empty or reaches a stop_mark
        while not self.ops.empty() and self.__calc() != 'stop':
            pass
        if not self.vals.empty():
            return self.vals.pop()

    def push_val(self, val):
        self.vals.push(val)

    def push_op(self, op):
        if op.type == 'uni_r':
            if self.vals.empty():
                raise SyntaxError
            self.vals.push(op(self.vals.pop()))
            return
        while not (self.ops.empty() or op.isStopMark()):
            last_op = self.ops.peek()
            if op.priority <= last_op.priority:
                try:
                    self.__calc()
                except AssertionError:
                    raise SyntaxError
            else:
                break
        self.ops.push(op)


class Env:
    def __init__(self, bindings={}, parent=None):
        self.bindings = bindings
        self.parent = parent

    def __setitem__(self, name, val):
        self.bindings[name] = val

    def __getitem__(self, name):
        try:
            return self.bindings[name]
        except KeyError:
            if self.parent:
                return self.parent[name]
            else:
                raise KeyError

    def __contains__(self, name):
        return name in self.bindings

    def remove(self, name):
        self.bindings.pop(name)

    def update(self, other):
        self.bindings.update(other.bindings)

    def define(self, bindings):
        self.bindings.update(bindings)

    def make_subEnv(self, bindings={}):
        return Env(bindings, self)


class function:

    evaluator = lambda *args: None  # to be set later

    def _default_apply(self, *args):
        if not self._fixed_argc:
            if len(args) < self._least_argc:
                raise TypeError('inconsistent number of arguments!')
            args = args[:self._least_argc] + (args[self._least_argc:],)
        elif len(args) != self._least_argc:
            raise TypeError('inconsistent number of arguments!')
        bindings = dict(zip(self._params, args))
        return function.evaluator(self._body, self._env.make_subEnv(bindings))

    def __init__(self, params, body, env, name=None):
        if params and params[-1][0] == '%':
            params[-1] = params[-1][1:]
            self._least_argc = len(params) - 1
            self._fixed_argc = False
        else:
            self._least_argc = len(params)
            self._fixed_argc = True
        params = [s.strip() for s in params]
        self._params = [s for s in params if s and s[0].isalpha()]
        if len(self._params) != len(params):
            raise SyntaxError('invalid parameters:', ', '.join(params))
        self._body = body.strip()
        self._env = env
        self._apply = self._default_apply
        self._name = name

    def __call__(self, *args):
        result = self._apply(*args)
        if __debug__:
            print(f"{self._name}({', '.join(map(str, args))}) = {result}")
        return result

    def compose(self, *funcs):
        """ Return a function that compose this function and several functions. """
        def apply(*args):
            return self._default_apply(*map(lambda f: f(*args), funcs))
        g = copy(self)
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
        params = self._params
        if not self._fixed_argc: params[-1] = '%' + params[-1]
        params = ', '.join(params)
        if self._name: 
            return f'{self._name}({params})'
        elif params:
            return f'function of {params}'
        else:
            return f"function"

    def __str__(self):
        return repr(self) + ': ' + self._body


class config:
    "This class holds all configs for the calculator."
    tolerance = 1e-12
    precision = 6
    latex = False
    all_symbol = True


# class GeneralSet(set):  # but disabled - no operations

#     def __init__(self, vars, constraint):
#         self._vars = vars
#         self._constr = constraint

#     def __contains__(self, el):
#         if len(self._vars) > 1:
#             assert(len(self._vars) == len(el))
#         mapping = zip(self._vars, el)
#         for var, val in mapping:
#             if var[1] and val not in var[1]:
#                 return False
#         return self._constr(el)

#     def __str__(self):
#         def withfield(var):
#             v = var[0]
#             if var[1]:
#                 v += ' in ' + str(var[1])
#             return v
#         left = ', '.join(map(withfield, self._vars))
#         return f"{{{left} | {self._constr._body}}}"
