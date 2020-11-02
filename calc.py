import sys
from src import config
from src import parse
from src.objects import stack
from src.eval import calc_eval, LOAD
from src.format import calc_format
from src.funcs import eq_ as equal
from src.utils.deco import log
from src.utils.greek import escape_to_greek


# track the brackets
class BracketTracker:
    stk = stack()

    @classmethod
    def _push(cls, par, pos):
        cls.stk.push((par, pos))

    @classmethod
    def _pop(cls, par):
        if cls.stk.peek()[0] == cls.par_map[par]:
            cls.stk.pop()
        else:
            cls.stk.clear()
            raise SyntaxError('invalid parentheses')

    parentheses = ')(', '][', '}{'
    close_pars, open_pars = zip(*parentheses)
    par_map = dict(parentheses)

    @classmethod
    def track(cls, line):
        "Track the brackets in the line and return the pos of the last unclosed bracket."
        for i, c in enumerate(line):
            if c in cls.open_pars: cls._push(c, i)
            elif c in cls.close_pars: cls._pop(c)
        return cls.stk.peek()[1] if cls.stk else -1


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

    buffer, count, indent = [], 0, 0

    for line in get_lines(filename):
        try:
            if line.find('#TEST') == 0 and not test:
                return  # the lines after #TEST are run only in test mode
            # get input
            prompt = indent*' ' if indent else f'({count})▶ '
            if verbose:
                print(prompt, end='', flush=True)  # prompt
                if filename is None:
                    line = input()
                else:  # loading a script
                    print(line, flush=True)

            line, comment = split_comment(line)
            if not line: continue

            # check whether the line is unfinished
            unfinished = False
            if line[-3:] == '...':
                line = line[:-3]
                unfinished = True
            indent = BracketTracker.track(prompt+line) + 1
            if indent: unfinished = True

            buffer.append(line)
            if unfinished: continue

            line = ''.join(buffer)
            line = escape_to_greek(line)
            # convert escaped chars to greek
            
            buffer, indent = [], 0

            result = calc_eval(line)
            if result is None: continue

            if verbose:  # print output
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
            if test and config.debug: raise
        except Exception as e:
            if str(e): print('Error:', e)
            else: print('Exiting due to an exception...')
            if config.debug: raise
            
    if test:
        print('\nCongratulations, tests all passed in "%s"!\n' % filename)

LOAD.run = run  # enable LOAD in _eval to run a new script


if __name__ == "__main__":
    debug = '-d' in sys.argv
    test = '-t' in sys.argv
    
    config.debug = debug
    if debug:
        sys.argv.remove('-d')
        # log.out = open('src/utils/log.yaml', 'w')
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
