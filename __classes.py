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


class calcMachine:
    def __init__(self):
        self.vals = Stack()
        self.ops = Stack()

    def __calc(self):  # carry out a single operation
        op = self.ops.pop()
        if op[0] is None: return 'stop'
        elif op[1] == 4:  # unitary op
            self.vals.push(op[0](self.vals.pop()))
        else:
            n2 = self.vals.pop()
            n1 = self.vals.pop()
            self.vals.push(op[0](n1, n2))

    def set_out(self):  # mark the beginning of calculation
        self.ops.push((None, -10))  # add a stop_mark in op_stack

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
        while not (self.ops.empty() or op[0] is None):
            last_op = self.ops.peek()
            if op[1] > last_op[1]: break
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
