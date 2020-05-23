import io
import sys
from __classes import Env, config, function
from __builtins import *
from __evaluator import add_bindings, calc_eval, history, CM
from __formatter import format


global_env = Env()


def calc_exec(exp, / , record=True, env=global_env):
    words = exp.split()
    if words[0] == 'ENV':
        for name in global_env.bindings:
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
        try:
            words.remove('-v')
        except:
            verbose = False
        definitions = {}
        for modules in words[1:]:
            locals = {}
            exec('from pymodules.%s import definitions' %
                 modules, globals(), locals)
            definitions.update(locals['definitions'])
        global_env.define(definitions)
        if verbose:
            return definitions
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
        else:
            raise SyntaxError('invalid format setting')
    elif words[0] == 'del':
        for name in words[1:]:
            global_env.remove(name)
    else:
        assign_mark = exp.find(':=')
        if assign_mark < 0:
            result = calc_eval(exp, global_env)
        else:  # an assignment
            lexp, rexp = exp[:assign_mark], exp[assign_mark + 2:]
            result = add_bindings(lexp, rexp, global_env)
        if not (CM.vals.empty() and CM.ops.empty()):
            raise SyntaxError('invalid expression!')
        if result is not None and record:
            history.append(result)
        return result


def run(filename=None, test=False, start=0, verbose=True, env=global_env):
    def get_lines(filename):
        if filename:
            file = open(filename, 'r')
            return file.readlines()
        else:
            return iter(lambda: 0, 1)  # an infinite loop

    def split_exp_comment(line):
        comment_at = line.find('#')
        if comment_at < 0:
            return line, ''
        else:
            return line[:comment_at], line[comment_at + 1:]

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

    buffer, count = '', 0
    for line in get_lines(filename):
        if test and count < start:
            count += 1
            continue
        try:
            # get input
            if line == '#TEST' and not test:
                return
            if verbose:
                print(f'({count})▶ ', end='', flush=True)  # prompt
            if filename is None:
                line = input()
            if filename and verbose:
                print(line, flush=True)
            line = line.strip()

            if line and line[-3:] == '...':
                buffer += line[:-3]
                continue  # join multiple lines
            elif buffer:
                line, buffer = buffer + line, ''
            if line and line[-1] == ';':
                line = line[:-1]
                show = False
            else:
                show = True

            exp, comment = split_exp_comment(line)
            if exp:
                result = calc_exec(exp, env=env)
            else:  # a comment line
                continue
            if result is None:
                continue

            if show and verbose:  # print output
                if type(result) == dict:  # imported definitions
                    print('imported:', ', '.join(result), flush=True)
                else:
                    print(format(result, config), flush=True)

            # test
            if test and comment:
                verify_answer(exp, result, comment, verbose)

            count += 1

        except KeyboardInterrupt:
            return
        except (Warning if test else Exception) as err:
            if test:
                raise Warning(err)
            if __debug__:
                raise Exception(err)
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
