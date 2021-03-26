import threading
import sys, os

# read program arguments
debug = '-d' in sys.argv
test = '-t' in sys.argv

# directory of scripts to load
scripts_dir = os.path.join(os.getcwd(), 'scripts/')

import src
from utils.io import BracketTracker, input
import config

config.debug = debug

    
def run(filename=None, test=False, start=0, verbose=True):
    def get_lines(filename):
        if interactive:
            return iter(lambda: '', 1)  # infinite loop
        else:
            path = scripts_dir + filename
            with open(path, 'r', encoding='utf8') as f:
                return f.read().splitlines()[start:]

    def verify_answer(exp, result, answer):
        if eq(result, eval(answer)):
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
            brackets = '$ '
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
                print(prompt, end='')
                
            if interactive:  # get input
                try:
                    line = input(indent=len(prompt))
                except IOError:
                    print(); continue  # abandon current input
            else:  # print content in the loaded script
                if verbose: print(line)
                indent = BracketTracker.next_insertion(line)
                if line and line[-1] == '\\':
                    line = line[:-1]
                    if not indent: indent = len(prompt)
                
            if loading_thread.is_alive():
                loading_thread.join()

            buffer.append(line)
            if indent: continue

            line = ''.join(buffer)
            buffer, indent = [], 0

            result = calc_eval(line)
            comment = LINE.comment
            
            if test and comment:
                verify_answer(line, result, comment)

            if result is None: continue
            
            if verbose:  # print output
                prefix = make_prompt('out')
                opts = {opt: comment == opt.upper()
                        for opt in ['sci', 'tex', 'bin', 'hex']}
                linesep = '\n' + ' ' * len(prefix)
                output = calc_format(result, linesep=linesep, **opts)
                print(prefix + output)
            
            count += 1

        except KeyboardInterrupt:
            print('\nByebye!')
            return
        except Warning as w:
            print(w)
            if test and config.debug: raise #Warning
        except Exception as e:
            if str(e): print('Error:', e)
            else: print('Exiting due to an exception...')
            if test or config.debug: raise
            
    if test:
        print('\nCongratulations, tests all passed in "%s"!\n' % filename)
        
        
def load_mods():
    "Load modules, which can cost some time."
    import utils.io as io
    from utils.debug import log
    # from utils.unicode import subst
    from eval import calc_eval, LOAD, LINE
    from format import calc_format
    from funcs import eq
    
    # io.read.subst = subst
    log.file = io
    LOAD.run = run
    
    globals().update((obj.__name__, obj) for obj in
                     [calc_eval, calc_format, eq, log, LINE])

# start another thread to speed up the startup
loading_thread = threading.Thread(target=load_mods)
loading_thread.start()


if debug:
    sys.argv.remove('-d')
    
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
    finally:
        log.file.close()
else:
    run()
