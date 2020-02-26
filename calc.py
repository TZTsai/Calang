import io
import sys
from __classes import *
from __parser import *
from __builtins import *
from __formatter import *

py_eval = eval

global_env = Env()
history = []
CM = calcMachine()


def config(): return None


config.prec = 4
config.latex = False
config.all_symbol = True


def eval_list(exp, env):
    comprehension = get_list(exp, '|')
    if len(comprehension) > 1:
        return eval_comprehension(comprehension, env)

    def value(exp): return calc_eval(exp, env)

    lst = get_list(exp)
    result = []
    for exp in lst:
        if not exp:
            raise SyntaxError('invalid list syntax')
        if exp[0] == '*':
            result.extend(value(exp[1:]))
        else:
            result.append(value(exp))
    return tuple(result)


def eval_subscription(lst, subscript_exp, env):
    def eval_index(index_exp):
        slice_args = [calc_eval(exp, env) for exp in split(index_exp, ':')]
        if len(slice_args) > 1:
            return slice(*slice_args)
        else:
            return slice_args[0]
    subscript_exps = get_list(subscript_exp)
    if not subscript_exps:
        raise SyntaxError('invalid subscript')
    if len(subscript_exps) == 1:
        return index(lst, eval_index(subscript_exps[0]))
    return subscript(lst, tuple(map(eval_index, subscript_exps)))


def eval_comprehension(comprehension, env):
    def gen_vals(exp, constraints):
        if constraints:
            constr = constraints[0]
            try:
                param, range_, spec = *split(constr[0], 'in'), constr[1:]
            except ValueError:
                raise SyntaxError('no range provided, use \'in\'')
            param = get_name(param)
            for val in calc_eval(range_, local_env):
                local_env[param] = val
                if not spec or calc_eval(spec[0], local_env):
                    yield from gen_vals(exp, constraints[1:])
        else:
            yield calc_eval(exp, local_env)

    exp, constraints = comprehension[0], comprehension[1:]
    constraints = [split(constr, 'and', 2) for constr in constraints]
    local_env = env.make_subEnv()
    return tuple(gen_vals(exp, constraints))


# def eval_set(exp, env):
#     try:
#         varstr, constr = get_list(exp, '|')
#     except ValueError:
#         return set(eval_list(exp, env))
#     def getvar(s):
#         if len(t := split(s, 'in')) == 2:
#             return t[0], calc_eval(t[1], env)
#         else:
#             return s, None
#     vars_ = [getvar(s) for s in split(varstr, ',')]
#     constr = function(list(zip(*vars_))[0], constr, env)
#     return GeneralSet(vars_, constr)


def eval_cases(exp, env):
    cases = [split(case, ':') for case in get_list(exp)]
    def value(exp): return calc_eval(exp, env)
    try:
        for val in (value(exp) for cond, exp in cases if value(cond)):
            return val
    except ValueError:
        return value(cases[-1][0])


def eval_name(token, env):
    try:
        val = env[token]
    except KeyError:
        if token in builtins:
            val = builtins[token]
        elif config.all_symbol:
            val = Symbol(token)
        else:
            raise NameError(f'unbound symbol \'{token}\'')
    return val


def eval_ans_id(token):
    if all(c == '_' for c in token):
        return -len(token)
    else:
        return int(token[1:])


def eval_closure(type_, token, exp, env):
    i = first(lambda c: c.isspace(), token)
    segs = split(token[i:-1], ',')  # the last char is ':'
    if type_ == 'with':
        bindings = [get_binding(name, exp, env) for name, exp in
                    (split(pair, '=', 2) for pair in segs)]
        return calc_eval(exp, env.make_subEnv(dict(bindings)))
    else:
        return function(segs, exp, env)


def get_binding(lexp, rexp, env=global_env):
    """ lexp can be either a name or a repr of a function, eg. 'f(x)' """
    name, rest = get_name(lexp, False)
    if not rest:
        return name, calc_eval(rexp, env)
    else:  # bind a function, eg. f(x) bound to x + 1
        type_, params, rest = get_token(rest)
        if type_ != 'paren' or rest != '':
            raise SyntaxError('invalid variable name!')
        func = function(get_list(params), rexp, env.make_subEnv())
        func._env[name] = func  # enable recursion
        return name, func


def is_replacable(type_, *replaced_types):
    return type_ in replaced_types + ('name', 'paren', 'ans')


def is_applying(prev_val, prev_type, type_):
    return type_ == 'paren' and is_function(prev_val) \
        and is_replacable(prev_type, 'name')


def is_making_func(exp):
    if exp and (tup := get_token(exp))[0] == 'arrow':
        return tup[2]
    return False


def calc_eval(exp, env):
    """ a pure function that evaluates exp in env """
    # inner evaluation
    if exp == '':
        return
    CM.begin()
    prev_type = None
    while exp:
        type_, token, exp = get_token(exp)
        prev_val = None if CM.vals.empty() else CM.vals.peek()
        if is_applying(prev_val, prev_type, type_):  # apply a function
            func, args = CM.vals.pop(), eval_list(token, env)
            CM.push_val(func(*args))
            continue
        if all(is_replacable(t, 'number', 'symbol') for t in (type_, prev_type)):
            CM.push_op(binary_ops['*'])
        if type_ == 'ans':
            try:
                id = eval_ans_id(token)
                CM.push_val(history[id])
            except IndexError:
                raise ValueError(f'Answer No.{id} not found!')
        elif type_ == 'number':
            try:
                CM.push_val(py_eval(token))
            except Exception:
                raise SyntaxError(f'invalid number: {token}')
        elif type_ == 'name':
            if (body := is_making_func(exp)) == False:
                CM.push_val(eval_name(token, env))
            else:
                CM.push_val(function([token], body, env))
                break
        elif type_ == 'symbol':
            CM.push_val(Symbol(token[1:]))
        elif type_ == 'op':
            if (prev_type in (None, 'op')) and token in unitary_l_ops:
                CM.push_op(unitary_l_ops[token])
            elif exp and token in binary_ops:
                CM.push_op(binary_ops[token])
            else:
                CM.push_op(unitary_r_ops[token])
        elif type_ == 'if':
            CM.push_op(Op('bin', priority=-5,
                          function=standardize('if', lambda x, y: x if y else None)))
        elif type_ == 'else':
            CM.push_op(Op('bin', standardize('else', lambda x, y: y), -5))
            if CM.vals.peek() is not None:
                CM.ops.pop()
                break  # short circuit
        elif type_ == 'cases':
            type_, token, exp = get_token(exp)
            if type_ != 'paren':
                raise SyntaxError('invalid cases expression')
            CM.push_val(eval_cases(token, env))
        elif type_ == 'paren':
            lst = get_list(token)
            if (body := is_making_func(exp)) != False:
                # a shorthand function
                CM.push_val(function(lst, body, env))
                break
            else:
                if len(lst) != 1:
                    raise SyntaxError('invalid syntax in parentheses')
                CM.push_val(calc_eval(lst[0], env))
        elif type_ == 'bracket':
            if is_iterable(prev_val) and is_replacable(prev_type, 'bracket'):
                CM.push_val(eval_subscription(CM.vals.pop(), token, env))
            else:
                CM.push_val(eval_list(token, env))
        elif type_ == 'brace':
            # experiment feature
            CM.push_val(eval_set(token, env))
        elif type_ in ('function', 'with', 'lambda'):
            CM.push_val(eval_closure(type_, token, exp, env))
            break
        else:
            raise SyntaxError('invalid token: %s' % token)
        prev_type = type_
    result = CM.calc()
    return result


function._eval = calc_eval


def calc_exec(exp, / , record=True, env=global_env):
    exps = exp.split(';')
    if not exps:
        return
    if len(exps) > 1:
        for exp in exps[:-1]:
            calc_exec(exp, False)
        return calc_exec(exps[-1])
    exp = exps[0]
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
        if words[1] == 'PREC':
            if len(words) == 2:
                print(config.prec)
            else:
                prec = py_eval(words[2])
                config.prec = prec
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
                print(eq_tolerance[0])
            else:
                eq_tolerance[0] = float(words[2])
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
            name, value = get_binding(lexp, rexp)
            if any(name in lst for lst in (special_words, builtins, op_list)):
                raise SyntaxError('word "%s" is protected!' % name)
            if value is None:
                raise ValueError(f'assigning {name} to none!')
            global_env[name] = value
            result = value
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
        if equal(result, py_eval(answer)):
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
            if filename:
                line = line.strip()
            if line == '#TEST' and not test:
                return
            if verbose:
                print(f'({count})▶ ', end='', flush=True)  # prompt
            if filename is None:
                line = input()
            if filename and verbose:
                print(line, flush=True)

            if line and line[-1] == '\\':
                buffer += line[:-1]
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
                print(err)
                raise Warning
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
