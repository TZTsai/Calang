import sys
import os
import re
import msvcrt
import time
from .debug import log


getch = msvcrt.getwch

spaces = ' \t\r\n'        # invokes a substitution if possible
esc = '\x1b'
cancel_signal = '\x1a'    # cancels the current input, here ^Z
exit_signal = '\x03\x04'  # exits the program, here ^C or ^D

arrow_map = dict(zip('HPMK', 'ABCD'))  # moves the cursor
arrow_dir = dict(zip('ABCD', 'UDRL'))  # corresponding directions


buffer = []
caret = 0           # position of insertion from the end of buffer
esc_pos = None      # position of the last esc_pos from the end


def ins():  # insertion position from the beginning
    return len(buffer) - caret


def write(s, track=1):
    if s == '\t':
        sp = 4 - ins() % 4
        sys.stdout.write(sp * ' ')
    else:
        sys.stdout.write(s)
    sys.stdout.flush()
    
    if track:
        for ch in s:
            buffer.insert(ins(), ch)
        if tail := ''.join(buffer[ins():]):
            sys.stdout.write(tail)
            sys.stdout.write('\b' * caret)  # move back the caret
            sys.stdout.flush()
        
        
def delete(n=1):
    write('\b' * n, 0)
    write(' ' * n, 0)
    write('\b' * n, 0)
    for _ in range(n):
        buffer.pop(-caret-1)
        

def resetbuffer():
    global caret
    caret = 0
    buffer.clear()


def read(end='\r\n', indent=0):
    """Reads the input; supports writing LaTeX symbols by typing a tab
    at the end of a string beginning with a esc_pos.
    """
    assert end in spaces
    global esc_pos
    
    resetbuffer()
    read.index = len(read.history)
    read.history.append(buffer)
    
    text = ''
    while True:
        end_ch = _read()
        i, j = esc_pos, ins()
            
        if i is not None:
            # replace the expression with its latex symbol
            s = read.subst(''.join(buffer[i+1:j]))
            
            # remove substituted chars from the input
            delete(j - i)
            
            if s[0] == 'x':  # a decorator, 'x' is a placeholder
                write(s[1:])
                move_cursor('K')  # move to the left of the decorator
            else:
                write(s)

            esc_pos = None
            
        write(end_ch)
            
        if end_ch in end:
            line = ''.join(buffer[:-1])
            text += line
            indent = BracketTracker.next_insertion(' '*indent + line)
            if indent or line[-1] == '\\':  # incomplete line
                resetbuffer()
                write(' ' * indent, 0)
            else:
                read.history[-1] = text
                return text

# assign read.subst in 'calc.py'
read.subst = lambda s: s
read.history = []
read.index = 0


def _read():
    global esc_pos
    c = -1
    
    while c:
        c = getch()

        if c == '\r':
            c += '\n'
        elif c == esc:
            if esc_pos is None:
                esc_pos = ins()
                c = '»'
            else:
                return esc
        elif c == '`':
            c = '⋅'  # used in dot product

        if c in exit_signal:
            raise KeyboardInterrupt
        elif c in cancel_signal:
            raise IOError("input cancelled")
        elif c in spaces:
            return c[-1]  # '[-1]' removes '\r' from '\r\n'
        elif c == '\b':  # backspace
            if caret < len(buffer):
                delete()
        elif c in '\x00\xe0':  # arrow key
            if (d := getch()) in 'KHMP':
                move_cursor(d)
                continue
            else:
                write(c + d, 1)
        else:
            write(c, 1)
            
        # set the latest history to the current buffer
        read.history[-1] = list(buffer)
        read.index = len(read.history) - 1
    
    raise IOError("failed to read input")


def move_cursor(code):
    global caret
    
    c = arrow_map[code]
    d = arrow_dir[c]
    cs = '\x1b[' + c
    
    if d in 'UD':
        i = read.index + (1 if d == 'D' else -1)
        if 0 <= i < len(read.history):
            read.index = i
            caret = 0
            delete(len(buffer))
            write(''.join(read.history[i]), 1)
    else:
        if d == 'L' and caret < len(buffer):
            caret += 1
            write(cs)
        elif d == 'R' and caret > 0:
            caret -= 1
            write(cs)

    
def input(prompt='', indent=0):
    write(prompt)
    return read(indent=indent)

class BracketTracker:
    parentheses = ')(', '][', '}{'
    close_pars, open_pars = zip(*parentheses)
    par_map = dict(parentheses)
    stack = []

    @classmethod
    def push(cls, par, pos):
        cls.stack.append((par, pos))

    @classmethod
    def pop(cls, par):
        if cls.stack and cls.stack[-1][0] == cls.par_map[par]:
            cls.stack.pop()
        else:
            cls.stack.clear()
            raise SyntaxError('bad parentheses')

    @classmethod
    def next_insertion(cls, text):
        "Track the brackets in the line and return the appropriate pooint of the nest insertion."
        for line in text.splitlines():
            for i, c in enumerate(line):
                if c in cls.open_pars:
                    cls.push(c, i)
                elif c in cls.close_pars:
                    cls.pop(c)
        return cls.stack[-1][1] + 1 if cls.stack else 0


if __name__ == '__main__':
    while 1: write(repr(input('>> ')) + '\n')
