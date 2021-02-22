import sys
import os
import re
import msvcrt
import time
from utils.debug import log


spaces = ' \t\n'          # invokes a substitution if possible
cancel_signal = '\x1a'    # cancels the current input, here ^Z
exit_signal = '\x03\x04'  # exits the program, here ^C or ^D

arrow_map = dict(zip('HPMK', 'ABCD'))  # moves the cursor
arrow_dir = dict(zip('ABCD', 'UDRL'))  # corresponding directions


putch = msvcrt.putwch
getch = msvcrt.getwch


buffer = []
caret = 0  # position of insertion from the end of buffer

def insp():  # insertion position from the beginning
    return len(buffer) - caret


def write(s, track=False):
    for ch in s:
        putch(ch)
        if track:
            ins = insp()
            buffer.insert(ins, ch)
            for ch in buffer[ins+1:]:
                putch(ch)
            for _ in buffer[ins+1:]:
                putch('\b')
    
        
def delete(n=1):
    write('\b' * n)
    write(' ' * n)
    write('\b' * n)
    for _ in range(n):
        buffer.pop(-caret-1)
        

def resetbuffer():
    global caret
    caret = 0
    buffer.clear()


def read(end='\n'):
    """Reads the input; supports writing LaTeX symbols by typing a tab
    at the end of a string beginning with a backslash.
    """
    assert end in spaces
    resetbuffer()

    while True:
        end_ch = _read()

        ins = insp()
        i = rfind('\\')
            
        if i is not None:
            # the part to be replaced
            t = buffer[i:ins]
            
            # remove substituted chars from the input
            delete(ins - i)

            # substitute the expression into its latex symbol
            t = read.subst(''.join(t))
            
            write(t, True)
            
        if end_ch != '\t':  # still print the last char
            write(end_ch, True)
            
        if end_ch in end:
            return ''.join(buffer)

read.subst = None

def rfind(x):
    i = insp() - 1
    while i >= 0:
        if buffer[i] == x:
            return i
        else:
            i -= 1

def _read():
    c = -1
    
    while c:
        c = getch()

        if c == '\r': c = '\n'

        if c in exit_signal:
            raise KeyboardInterrupt
        elif c in cancel_signal:
            raise IOError("input cancelled")
        elif c in spaces:
            return c
        elif c == '\b':  # backspace
            if caret < len(buffer):
                delete()
        elif c in '\x00\xe0':  # arrow key
            if (d := getch()) in 'KHMP':
                move_cursor(d)
            else:
                write(c + d, True)
        else:
            write(c, True)
    
    raise IOError("failed to read input")


def move_cursor(code):
    global caret
    
    c = arrow_map[code]
    d = arrow_dir[c]
    cs = '\x1b[' + c
    
    write(cs)
    if d in 'UD':  # up or down
        return  # TODO
    else:
        if d == 'L' and caret < len(buffer):
            caret += 1
            # write(cs, False)
        elif d == 'R' and caret > 0:
            caret -= 1
            # write(cs, False)


class StdIO:
    write = write  
    read = read

    
def input(prompt=''):
    write(prompt)
    return read()


def print(*msgs, end='\n', indent='default'):
    "Overrides the builtin print."
    log(*msgs, sep=' ', end=end, indent=indent, debug=False, file=StdIO)


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
