from _obj import stack, config
from _parser import calc_parse
from _eval import eval_tree, Global, GlobalEnv, drop_tag, tag
from _funcs import eq_ as equal
from _format import calc_format


### TODO 
#   0. DEF
#   1. CMD: dir, conf, del, ...
#   2. import and load
#   3. auto indent


def calc_exec(exp):
    global Global
    tree, rest = calc_parse(exp)
    if rest: raise SyntaxError('parsing failed, the unparsed part: ' + rest)
    type_ = tag(tree)
    if type_ == 'CMD':
        drop_tag(tree, 'CMD')
        type_ = tree[0]
        if type_ == 'DIR':
            field = Global if len(tree) == 1 else eval_tree(tree[1])
            for name, val in field.local.items(): print(f"{name}: {val}")
        elif type_ == 'LOAD':  # load a cal script
            modname = tree[1]
            test = '-t' in tree
            verbose = '-v' in tree
            overwrite = '-w' in tree
            current_global = Global
            Global = GlobalEnv()  # a new global env
            run('scripts/' + modname + '.cal', test, start=0, verbose=verbose)
            if overwrite:
                current_global.update(Global)
            else:
                for name in Global:
                    if name not in current_global:
                        current_global[name] = Global[name]
                    else:
                        print(f'name {name} not loaded because it is bounded')
            Global = current_global
        elif type_ == 'IMPORT':  # import definitions from a python file or sympy
            modname = tree[1]
            verbose = '-v' in tree
            overwrite = '-w' in tree
            env = definitions = {}
            try:
                exec('from modules.%s import export'%modname, env)
                definitions = env['export']
            except ModuleNotFoundError:
                exec('from sympy import %s'%modname, definitions)
            
            for name, val in definitions.items():
                if name not in Global or overwrite:
                    if verbose: print(f'imported: {name}')
                    Global[name] = val
        elif type_ == 'CONF':
            conf = tree[1]
            if conf == 'prec':
                if len(tree) == 2:
                    print(config.precision)
                else:
                    config.precision = min(1, int(tree[2]))
            elif conf == 'toler':
                if len(tree) == 2:
                    print(config.tolerance)
                else:
                    config.tolerance = float(tree[2])
            else:
                if len(tree) == 2:
                    print(getattr(config, conf))
                else:
                    setattr(config, conf, True if tree[2] in ('on', '1') else False)
        elif type_ == 'DEL':
            for field in tree[1:]:
                if field[0] == 'NAME':
                    attr = field[1]
                    field = Global
                else:
                    attr = field.pop()[1]
                    field = eval_tree(field)
                field.delete(attr)
    elif type_ == 'DEF':
        pass
    else:
        result = eval_tree(tree)
        Global._ans.append(result)
        return result


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


def run(filename=None, test=False, start=0, verbose=True):
    def get_lines(filename):
        if filename:
            file = open(filename, 'r')
            return file.readlines()[start:]  # begins from line `start`
        else:
            return iter(lambda: '', 1)  # an infinite loop

    def split_comment(line):
        try: exp, comment = line.split('#', 1)
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
            buffer, indent = [], 0

            show = True
            if line and line[-1] == ';':
                line = line[:-1]
                show = False

            result = calc_exec(line)
            if result is None: continue

            if show and verbose:  # print output
                sci = comment == 'SCI'
                tex = comment == 'TEX'
                print(calc_format(result, sci=sci, tex=tex), flush=True)

            # test
            if test and comment:
                verify_answer(line, result, comment)

            count += 1

        except KeyboardInterrupt: return
        except (Warning if test or config.debug else Exception) as err:
            print('Error:', err)
            

    if test:
        print('\nCongratulations, tests all passed in "%s"!\n' % filename)


run()