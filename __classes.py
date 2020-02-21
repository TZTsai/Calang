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


class calcMachine:
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

    _eval = lambda *args: None  # should be rebound later

    def _default_apply(self, *args):
        if not self._fixed_argc:
            if len(args) < self._least_argc:
                raise TypeError('inconsistent number of arguments!')
            args = args[:self._least_argc] + (args[self._least_argc:],)
        elif len(args) != self._least_argc:
            raise TypeError('inconsistent number of arguments!')
        bindings = dict(zip(self._params, args))
        return function._eval(self._body, self._env.make_subEnv(bindings))

    def __init__(self, params, body, env):
        if params and params[-1][0] == '*':
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

    def __call__(self, *args):
        return self._apply(*args)

    def compose(self, *funcs):
        """ Return a function that compose this function and several functions. """
        def apply(*args):
            return self._default_apply(*map(lambda f: f(*args), funcs))
        g = copy(self)
        g._apply = apply
        return g

    def __str__(self):
        params_str = ' of ' + ', '.join(self._params) + \
            ('' if self._fixed_argc else '... ') if self._params \
            else ''
        return f"function{params_str}: {self._body}"
