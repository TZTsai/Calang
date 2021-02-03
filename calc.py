import sys
sys.path.append('src')

import config
import parse
from objects import stack
from eval import calc_eval, LOAD
from format import calc_format
from funcs import eq_ as equal
from parse import BracketTracker
from utils.debug import log
from utils.backslash import escape_to_greek


scripts_dir = 'scripts/'


# override the builtin print
def print(*msgs, end='\n', flush=True):
    log(*msgs, sep=' ', end=end, out=sys.stdout, level=1)
    if flush: sys.stdout.flush()


def run(filename=None, test=False, start=0, verbose=True):
    def get_lines(filename):
        if filename:
            path = scripts_dir + filename
            file = open(path, 'r')
            return file.readlines()[start:]
        else:
            return iter(lambda: '', 1)  # infinite loop

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
    my_arrows = 2
    my_brackets = 1
    def make_prompt(in_out='in'):
        arrows = arrow_choices[my_arrows]
        if in_out == 'in':
            arrow = arrows[0]
            brackets = bracket_choices[my_brackets]
        else:
            arrow = arrows[1]
            brackets = '% '
        prompt = '%s%d%s%s ' % (brackets[0], count, brackets[1], arrow)
        print(prompt, end='', flush=True)
        return prompt

    buffer, count, indent = [], 0, 0

    for line in get_lines(filename):
        try:
            if line.find('#TEST') == 0 and not test:
                return  # the lines after #TEST are run only in test mode

            if not buffer and verbose:  # make prompt
                prompt = make_prompt()
            else:
                prompt = ''
            if filename is None:  # get input
                line = input(' ' * indent)
            elif verbose:  # print content in the loaded script
                print(' ' * indent + line, flush=True)

            line, comment = split_comment(line)
            if not line: continue

            indent = BracketTracker.next_insertion(prompt+line)
            if line[-3:] == '...':
                line = line[:-3]
                if not indent:
                    indent = len(prompt)

            buffer.append(line)
            if indent: continue

            line = ''.join(buffer)
            line = escape_to_greek(line)
            # convert escaped chars to greek
            
            buffer, indent = [], 0

            result = calc_eval(line)
            if result is None: continue

            if verbose:  # print output
                make_prompt('out')
                opts = {opt: comment == opt.upper() 
                        for opt in ['sci', 'tex', 'bin', 'hex']}
                print(calc_format(result, **opts), flush=True)

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
