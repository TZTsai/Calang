import sys
import os
import re
import msvcrt
import time
from .debug import log


getch = msvcrt.getwch

spaces = ' \t\r\n'        # invokes a substitution if possible
esc = '\x1b'              # also invokes a substitution
cancel_signal = '\x1a'    # cancels the current input, here ^Z
exit_signal = '\x03\x04'  # exits the program, here ^C or ^D

arrow_map = dict(zip('HPMK', 'ABCD'))  # moves the cursor
arrow_dir = dict(zip('ABCD', 'UDRL'))  # corresponding directions


buffer = []
caret = 0           # position of insertion from the end of buffer
esc_pos = None      # position of the last esc_pos from the end


def ins():  # insertion position from the beginning
    return len(buffer) - caret


def write(s, track=0):
    if type(s) is not str:
        s = ''.join(s)

    if s == '\t':
        sp = 4 - ins() % 4
        sys.stdout.write(sp * ' ')
    else:
        sys.stdout.write(s)
    
    bl = 0  # length of backspace
    
    if track:
        for ch in s:
            if ch == '\b':
                try: buffer.pop(-caret-1)
                except: break
                bl += 1
            else:
                buffer.insert(ins(), ch)
                
    tail = ''.join(buffer[ins():])
    if bl + len(tail) > 0:
        sys.stdout.write(tail)
        sys.stdout.write(bl * ' ')
        bl += len(tail)
        sys.stdout.write('\b' * bl)  # move back the caret
            
    sys.stdout.flush()
        
        
def delete(n=1):
    write('\b' * n, 1)
        

def resetbuffer():
    global caret, esc_pos
    buffer.clear()
    caret = 0
    esc_pos = None


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
            
            # if s[0] == 'x':  # a decorator, 'x' is a placeholder
            #     write(s[1:])
            #     move_cursor('K')  # move to the left of the decorator
            # else:
            write(s, 1)

            esc_pos = None
            
        if end_ch in end:
            line = ''.join(buffer)
            
            next_indent = BracketTracker.next_insertion(' '*indent + line)
            if line and line[-1] == '\\':
                line = line[:-1]
                indent += 2
            else:
                indent = next_indent
            text += line
                
            if indent:  # incomplete line
                resetbuffer()
                write(' ' * indent)
            else:
                for _ in range(caret):
                    move_cursor('M')  # move to the end of line
                write(end_ch)
                read.history[-1] = text
                return text
        
        if end_ch in spaces:
            write(end_ch, 1)

# assign read.subst in 'calc.py'
read.subst = lambda s: s
read.history = []
read.index = 0


def _read():
    global esc_pos
    c = -1
    edited = 0
    
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
        elif c in '\x00\xe0':
            if (d := getch()) in 'KHMP':  # arrow key
                if edited and d in 'HP':
                    # set the last history to the current buffer
                    read.history[-1] = list(buffer)
                    read.index = len(read.history) - 1
                    edited = 0
                move_cursor(d)
                continue
            else:
                write(c + d, 1)
        else:
            write(c, 1)
            
        edited = 1
    
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
            write(read.history[i], 1)
    else:
        if d == 'L' and caret < len(buffer):
            caret += 1
            write(cs, 0)
        elif d == 'R' and caret > 0:
            caret -= 1
            write(cs, 0)
        # buf = list(buffer)
        # buf.insert(ins(), '^')
        # print(buf)

    
def input(prompt='', indent=0):
    write(prompt)
    return read(indent=indent)

def close(): return
    
    
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
