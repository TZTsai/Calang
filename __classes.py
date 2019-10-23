class Stack:
    def __init__(self):
        self.pbtrack = []

    def push(self, obj):
        self.pbtrack.append(obj)
    
    def pop(self):
        assert(not self.empty())
        return self.pbtrack.pop()

    def peek(self):
        assert(not self.empty())
        return self.pbtrack[-1]

    def empty(self):
        return self.pbtrack == []

    def clear(self):
        self.pbtrack = []


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
        elif op.type == 'uni':  # unitary op
            self.vals.push(op(self.vals.pop()))
        else:
            n2 = self.vals.pop()
            n1 = self.vals.pop()
            self.vals.push(op(n1, n2))

    def begin(self):  # mark the beginning of calculation
        self.ops.push(Op('stop', None, -100))  # add a stop_mark in op_stack

    def reset(self):
        self.ops.clear()
        self.vals.clear()

    def calc(self): # calculate the whole stack and return the result
        while not self.ops.empty() and self.__calc() != 'stop':
            pass
        return self.vals.pop() if not self.vals.empty() else None

    def push_val(self, val):
        self.vals.push(val)

    def push_op(self, op):
        while not (self.ops.empty() or op.isStopMark()):
            last_op = self.ops.peek()
            if op.priority > last_op.priority:
                break
            else:
                try: self.__calc()
                except AssertionError:
                    raise SyntaxError
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
                raise KeyError('unbound symbol: %s' % name)

    def make_subEnv(self, args=[], vals=[]):
        return Env(dict(zip(args, vals)), self)
