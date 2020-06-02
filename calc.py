import io
import sys
from __classes import Env, config, function
from __builtins import *
from __evaluator import add_bindings, calc_eval, history, CM, my_globals
from __formatter import format
from __parser import split, IncompleteLine, get_bracket, get_colon_token
from sympy import pprint


global_env = Env()


def calc_exec(exp, / , record=True, env=global_env):
    words = exp.split()
    if words[0] == 'ENV':
        for name in global_env:
            print(f"{name}: {global_env[name]}")
    elif words[0] == 'load':
        current_history = history.copy()
        test = verbose = protect = True
        try:
            words.remove('-t')
        except:
            test = False
        try:
            words.remove('-v')
        except:
            verbose = False
        try:
            words.remove('-p')
        except:
            protect = False  # disable overwriting
        for filename in words[1:]:  # default folder: modules/
            new_env = Env()
            run('modules/' + filename + '.cal', test, start=0,
                verbose=verbose, env=new_env)
            if not protect:
                global_env.update(new_env)
            else:
                for name in new_env:
                    if name not in global_env:
                        global_env[name] = new_env[name]
        history.clear()
        history.extend(current_history)
    elif words[0] == 'import':
        verbose = True
        try: words.remove('-v')
        except: verbose = False
        bindings = {}
        for obj in words[1:]:
            try: 
                exec('from pymodules.%s import export'%obj, None, export:={})
                bindings.update(export['export'])
            except ModuleNotFoundError:
                exec('from sympy import %s'%obj, None, bindings)
        for _name, _val in bindings.items():
            if verbose:
                print('imported: '+_name)
            if _name in global_env:
                print('Warning: overwrite name "%s"'%_name)
            global_env[_name] = _val
    elif words[0] == 'conf':
        if len(words) == 1:
            raise SyntaxError('config field unspecified')
        if words[1] == 'prec':
            if len(words) == 2:
                print(config.precision)
            else:
                precision = eval(words[2])
                config.precision = precision
        elif words[1] == 'LATEX':
            if len(words) == 2:
                print(config.latex)
            else:
                config.latex = True if words[2] in ('on', '1') else False
        elif words[1] == 'ALL-SYMBOL':
            if len(words) == 2:
                print(config.all_symbol)
            else:
                config.all_symbol = True if words[2] in ('on', '1') else False
        elif words[1] == 'TOLERANCE':
            if len(words) == 2:
                print(config.tolerance)
            else:
                config.tolerance = float(words[2])
        elif words[1] == 'DEBUG':
            if len(words) == 2:
                print(config.debug)
            else:
                config.debug = True if words[2] in ('on', '1') else False
        else:
            raise SyntaxError('invalid format setting')
    elif words[0] == 'del':
        for name in words[1:]:
            global_env.remove(name)
    else:
        assign_split = split(exp, ':=')
        if len(assign_split) == 1: 
            exp = assign_split[0]
            result = calc_eval(exp, global_env)
        elif len(assign_split) == 2:
            lexp, rexp = assign_split
            result = add_bindings(lexp, rexp, global_env)
        else:  # an assignment
            raise SyntaxError('invalid use of assignment symbol!')
            
        if not (CM.vals.empty() and CM.ops.empty()):
            raise SyntaxError('invalid expression!')
        if result is not None and record:
            history.append(result)
        return result


my_globals['exec'] = calc_exec


def run(filename=None, test=False, start=0, verbose=True, env=global_env):
    def get_lines(filename):
        if filename:
            file = open(filename, 'r')
            return file.readlines()
        else:
            return iter(lambda: '', 1)  # an infinite loop

    def split_exp_comment(line):
        try: exp, comment = line.split('#', 1)
        except: exp, comment = line, ''
        return exp.rstrip(), comment.strip()

    def verify_answer(exp, result, answer, verbose):
        def equal(x, y):
            if is_number(x) and is_number(y):
                return abs(x-y) < 0.001
            if all(is_iterable(t) for t in (x, y)):
                return len(x) == len(y) and all(equal(xi, yi)
                                                for xi, yi in zip(x, y))
            return x == y
        if equal(result, eval(answer)):
            if verbose:
                print('--- OK! ---')
        else:
            raise Warning('--- Fail! expected answer of %s is %s, but actual result is %s ---'
                          % (exp, answer, str(result)))

    buffer, count, indent = [], 0, 0

    for line in get_lines(filename):
        if test and count < start:
            count += 1
            continue
        try:
            # get input
            if line.find('#TEST') == 0 and not test:
                return
            if verbose:
                print(f'({count})▶ ', end=' '*indent, flush=True)  # prompt
            if filename is None:
                line = input()
            if filename and verbose:
                print(line, flush=True)

            line, comment = split_exp_comment(line)

            if line and line[-3:] == '...':
                buffer.append(' '*indent + line[:-3])
                continue  # join multiple lines

            buffer.append(' '*indent + line)
            line = ''.join(buffer)
            try: 
                list(get_bracket(line))
                list(get_colon_token(line))
            except IncompleteLine as err:  # brackets not paired; continue
                indent = err.msg
                for b in buffer:
                    if indent > len(b): indent -= len(b)
                continue

            buffer, indent = [], 0

            if line and line[-1] == ';':
                line = line[:-1]
                show = False
            else:
                show = True

            if line: result = calc_exec(line, env=env)
            else: continue
            if result is None: continue

            if show and verbose:  # print output
                sci = comment == 'SCI'
                tex = comment == 'TEX'
                print(format(result, sci=sci, tex=tex), flush=True)

            # test
            if test and comment:
                verify_answer(line, result, comment, verbose)

            count += 1

        except KeyboardInterrupt:
            return
        except (Exception if not test and not config.debug else Warning) as err:
            print('Error:', err)
            CM.reset()
            

    if test:
        print('\nCongratulations, tests all passed in "%s"!\n' % filename)


### RUN ###

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

    import doctest
    doctest.testmod()

    if len(sys.argv) > 1:
        if sys.argv[1] == '-t':
            if len(sys.argv) == 2:
                testfile = 'tests.cal'
            else:
                testfile = sys.argv[2]
            run("tests/"+testfile, test=True, start=0)
        else:
            run(sys.argv[1])
    else:
        run()
