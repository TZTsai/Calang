import sys
import os
import re
import psutil
import msvcrt
from objects import stack
from utils.debug import log
from utils.backslash import subst

putch = msvcrt.putch
getch = msvcrt.getch
write = sys.stdout.write

exit_signal = b'\x03\x04'
tab_space = 2

def input(end='\n', sub='\t', ccl='\x1a'):
    "Overrides the builtin input."
    s = []
    
    while True:
        read(s)

        if s[-1] == sub:  # substitute backslash if it exists
            i = findlast(s, '\\')
            if i is None: continue
            
            n_del = len(s) - i + tab_space - 1
            backspace(n_del)  # remove substituted chars from console
            s, t = s[:i], s[i:-1]
            
            t = subst(''.join(t))
            write(t)
            s.extend(t)
            
        elif s[-1] == ccl:  # cancel input
            raise IOError("input cancelled")

        elif s[-1] == end:
            return ''.join(s[:-1])
        
def findlast(l: list, x):
    i = len(l) - 1
    while i >= 0:
        if l[i] == x:
            return i
        else:
            i -= 1
    
def read(s=[]):
    c = 1
    while c and not is_ctrl_char(c):
        c = getch()

        if c == b'\r':
            c = b'\n'

        if c in exit_signal:
            raise KeyboardInterrupt

        if c == b'\t':
            write('  ')
        elif c == b'\x08':  # backspace
            backspace()
            if s: s.pop()
            continue
        else:
            putch(c)

        c = c.decode()
        s.append(c)

    return s

def backspace(n=1):
    write('\b' * n)
    write(' ' * n)
    write('\b' * n)

ctrlchar_pat = re.compile(r'^[\x00-\x1f\x7f-\x9f]$')
def is_ctrl_char(ch):
    return type(ch) is str and ctrlchar_pat.match(ch)

def print(*msgs, end='\n', indent='default', flush=True):
    "Overrides the builtin print."
    log(*msgs, sep=' ', end=end, indent=indent, out=sys.stdout, debug=False)
    if flush: sys.stdout.flush()


class BracketTracker:
    stk = stack()

    @classmethod
    def _push(cls, par, pos):
        cls.stk.push((par, pos))

    @classmethod
    def _pop(cls, par):
        if cls.stk and cls.stk.peek()[0] == cls.par_map[par]:
            cls.stk.pop()
        else:
            cls.stk.clear()
            raise SyntaxError('invalid parentheses')

    parentheses = ')(', '][', '}{'
    close_pars, open_pars = zip(*parentheses)
    par_map = dict(parentheses)

    @classmethod
    def next_insertion(cls, line):
        "Track the brackets in the line and return the appropriate pooint of the nest insertion."
        for i, c in enumerate(line):
            if c in cls.open_pars:
                cls._push(c, i)
            elif c in cls.close_pars:
                cls._pop(c)
        return cls.stk.peek()[1] + 1 if cls.stk else 0


input()
