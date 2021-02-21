import sys
import os
import re
import psutil
import msvcrt
from utils.debug import log


putch = msvcrt.putwch
getch = msvcrt.getwch


tab_space = 2
exit_signal = '\x03\x04'
ctrl_chars = re.compile(r'^[\x00-\x1f\x7f-\x9f]$')
subst = None


def write(s: str):
    for c in s: putch(c)


def input(prompt='', *, end='\n', sub='\t', cancel='\x1a'):
    """Reads the input; supports writing LaTeX symbols by typing a tab
    at the end of a string beginning with a backslash.
    
    Args:
      prompt: The string to print before input.
      end: Keys indicating the end of input, default Enter.
      sub: Keys indicating a backslashed substitution, default Tab.
      cancel: Keys indicating cancellation of the current input, default Ctrl-Z.
      """
    write(prompt)

    s = []
    while True:
        _read(s)

        if s[-1] in sub:  # substitute backslash if it exists
            i = rfind(s, '\\')
            if i is None:
                continue

            n_del = len(s) - i + tab_space - 1
            backspace(n_del)  # remove substituted chars from console
            s, t = s[:i], s[i:-1]

            t = input.subst(''.join(t))
            write(t)
            s.extend(t)

        elif s[-1] in cancel:  # cancel input
            raise IOError("input cancelled")

        elif s[-1] in end:
            return ''.join(s[:-1])
        
input.subst = None


def _read(s=[]):
    c = 1
    while c and not is_ctrl_char(c):
        c = getch()

        if c == '\r': c = '\n'

        if c in exit_signal:
            raise KeyboardInterrupt

        if c == '\t':
            write('  ')
        elif c == '\x08':  # backspace
            backspace()
            if s:
                s.pop()
            continue
        else:
            putch(c)

        s.append(c)

    return s


def rfind(l: list, x):
    i = len(l) - 1
    while i >= 0:
        if l[i] == x:
            return i
        else:
            i -= 1


def backspace(n=1):
    write('\b' * n)
    write(' ' * n)
    write('\b' * n)


def is_ctrl_char(ch):
    return type(ch) is str and ctrl_chars.match(ch)


def print(*msgs, end='\n', indent='default'):
    "Overrides the builtin print."
    log(*msgs, sep=' ', end=end, indent=indent, debug=False)


class BracketTracker:

    parentheses = ')(', '][', '}{'
    close_pars, open_pars = zip(*parentheses)
    par_map = dict(parentheses)

    def __init__(self):
        self.stk = []

    def push(self, par, pos):
        self.stk.append((par, pos))

    def pop(self, par):
        if self.stk and self.stk[-1][0] == self.par_map[par]:
            self.stk.pop()
        else:
            self.stk.clear()
            raise SyntaxError('bad parentheses')

    def next_insertion(self, line):
        "Track the brackets in the line and return the appropriate pooint of the nest insertion."
        for i, c in enumerate(line):
            if c in self.open_pars:
                self.push(c, i)
            elif c in self.close_pars:
                self.pop(c)
        return self.stk[-1][1] + 1 if self.stk else 0
