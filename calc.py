import sys
from src import config
from src import parse
from src.objects import stack
from src.eval import calc_eval, LOAD
from src.format import calc_format
from src.funcs import eq_ as equal
from src.utils.debug import log
from src.utils.greek import escape_to_greek


# overwrite the builtin print
def print(*msgs, end='\n', flush=True):
    log(*msgs, end=end, out=sys.stdout)
    if flush: sys.stdout.flush()


# track the brackets
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
            if c in cls.open_pars: cls._push(c, i)
            elif c in cls.close_pars: cls._pop(c)
        return cls.stk.peek()[1] + 1 if cls.stk else 0


scripts_dir = 'scripts/'
def run(filename=None, test=False, start=0, verbose=True):
    def get_lines(filename):
        if filename:
            path = scripts_dir + filename
            file = open(path, 'r')
            return file.readlines()[start:]  # begins from line `start`
        else:
            return iter(lambda: '', 1)  # an infinite loop

    def split_comment(line):
        try: exp, comment = line.rsplit('#', 1)
        except: exp, comment = line, ''
        return exp.rstrip(), comment.strip()

    def verify_answer(exp, result, answer):
        if equal(result, eval(answer)):
            if verbose: print('--- OK! ---')
        else:
            raise Warning('--- Fail! Expected answer of %s is %s, but actual result is %s ---'
                          % (exp, answer, str(result)))
            
    arrow_choices = ['»=«', '▶=◀', '➤=', '▷=◁']
    bracket_choices = ['()', '[]', '⟦⟧', '﴾﴿']
    my_arrows = 0
    my_brackets = 1
    def make_prompt(in_out='in'):
        if indent: return indent * ' '
        arrows = arrow_choices[my_arrows]
        if in_out == 'in':
            arrow = arrows[0]
            brackets = bracket_choices[my_brackets]
        else:
            arrow = arrows[1]
            brackets = '% '
        return '%s%d%s%s ' % (brackets[0], count, brackets[1], arrow)

    buffer, count, indent = [], 0, 0

    for line in get_lines(filename):
        try:
            if line.find('#TEST') == 0 and not test:
                return  # the lines after #TEST are run only in test mode
            # get input
            prompt = make_prompt()
            if verbose:
                print(prompt, end='', flush=True)  # prompt
                if filename is None:
                    line = input()
                else:  # loading a script
                    print(line, flush=True)

            line, comment = split_comment(line)
            if not line: continue

            # check whether the line is unfinished
            indent = BracketTracker.next_insertion(prompt+line)
            if line[-3:] == '...':
                line = line[:-3]
                if not indent: indent = len(prompt)

            buffer.append(line)
            if indent: continue

            line = ''.join(buffer)
            line = escape_to_greek(line)
            # convert escaped chars to greek
            
            buffer, indent = [], 0

            result = calc_eval(line)
            if result is None: continue

            if verbose:  # print output
                opts = {opt: comment == opt.upper() 
                        for opt in ['sci', 'tex', 'bin', 'hex']}
                s = calc_format(result, **opts)
                p = make_prompt('out')
                print(p + s, flush=True)

            # test
            if test and comment:
                verify_answer(line, result, comment)

            count += 1

        except KeyboardInterrupt:
            return
        except Warning as w:
            print(w)
            if test and config.debug: raise Warning
        except Exception as e:
            if str(e): print('Error:', e)
            else: print('Exiting due to an exception...')
            if test or config.debug: raise
            
    if test:
        print('\nCongratulations, tests all passed in "%s"!\n' % filename)

LOAD.run = run  # enable LOAD in _eval to run a new script


if __name__ == "__main__":
    debug = '-d' in sys.argv
    test = '-t' in sys.argv
    
    config.debug = debug
    if debug:
        sys.argv.remove('-d')
        from src.grammar import grammar
        parse.grammar = grammar  # reload grammar only when debugging
        
    if test: sys.argv.remove('-t')
            
    if len(sys.argv) > 1 or test:
        if len(sys.argv) > 1:
            filename = sys.argv[1]
        else:
            filename = 'tests/tests.cal'
        try:
            run(filename, test)
        except FileNotFoundError:
            raise FileNotFoundError('script "%s" not found' % filename)
        except Exception:
            if config.debug: raise
    else:
        run()
