import sys
import threading

sys.path.append('src')

from src.io import BracketTracker, print, input
import config


debug = '-d' in sys.argv
test = '-t' in sys.argv

scripts_dir = 'scripts/'
config.debug = debug

    
def run(filename=None, test=False, start=0, verbose=True):
    def get_lines(filename):
        if interactive:
            return iter(lambda: '', 1)  # infinite loop
        else:
            path = scripts_dir + filename
            file = open(path, 'r')
            return file.readlines()[start:]

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
    my_arrows, my_brackets = 2, 1
    def make_prompt(in_out='in'):
        arrows = arrow_choices[my_arrows]
        if in_out == 'in':
            arrow = arrows[0]
            brackets = bracket_choices[my_brackets]
        else:
            arrow = arrows[1]
            brackets = '% '
        prompt = '%s%d%s%s ' % (brackets[0], count, brackets[1], arrow)
        return prompt

    interactive = filename is None
    buffer, count, indent = [], 0, 0

    for line in get_lines(filename):
        try:
            if line.find('#TEST') == 0 and not test:
                return  # the lines after #TEST are run only in test mode

            if verbose:  # make prompt
                if buffer:  # last line not completed
                    prompt = ' ' * indent
                else:
                    prompt = make_prompt()
                print(prompt, end='', flush=True)
                
            if interactive:  # get input
                try:
                    line = input()
                except IOError:
                    print(indent=0)
                    continue  # abandon current input
            elif verbose:  # print content in the loaded script
                print(line, indent=0)
                
            if loading_thread.is_alive():
                loading_thread.join()
                
            line, comment = split_comment(line)
            if not line: continue

            indent = BracketTracker.next_insertion(prompt + line)
            if line[-3:] == '...':
                line = line[:-3]
                if not indent: indent = len(prompt)

            buffer.append(line)
            if indent: continue

            line = ''.join(buffer)
            buffer, indent = [], 0

            result = calc_eval(line)
            if result is None: continue

            if verbose:  # print output
                prompt = make_prompt('out')
                print(prompt, end='')
                opts = {opt: comment == opt.upper()
                        for opt in ['sci', 'tex', 'bin', 'hex']}
                linesep = '\n' + ' ' * len(prompt)
                output = calc_format(result, linesep=linesep, **opts)
                print(output, flush=True)

            if test and comment:
                verify_answer(line, result, comment)

            count += 1

        except KeyboardInterrupt:
            print('Byebye!')
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
        
        
def load_src():  # to speed up the startup of calc
    from eval import calc_eval, LOAD
    from format import calc_format
    from funcs import eq_ as equal
    
    LOAD.run = run
    globals().update((obj.__name__, obj) for obj in
                     [calc_eval, calc_format,
                      equal, BracketTracker])

loading_thread = threading.Thread(target=load_src)
loading_thread.start()


if debug:
    sys.argv.remove('-d')
    from src.grammar import grammar
    parse.grammar = grammar  # reload grammar only when debugging
    
if test:
    sys.argv.remove('-t')
        
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
