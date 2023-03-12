from pprint import pformat, pprint
from functools import wraps
import traceback
import json
import config


def log(*messages, debug=True, end='\n', sep='',
        indent='default', file='default'):
    if not config.debug and debug:
        return
    if file == 'default':
        file = log.file
    if indent == 'default':
        indent = log.indent
        
    message = sep.join(map(log.format, messages))
    file.write(indent * ' ' + message + end)


logfile = open('utils/cal.log', 'w', encoding='utf8')
log.indent = 0
log.format = str
log.file = logfile


def trace(f):
    "Print info before and after the call of a function."
    @wraps(f)
    def _f(*args):
        cur_logfile = log.file
        log.file = logfile
        
        fmt = str if 'parse' in f.__name__ else log.format
        signature = format_call(f, args, fmt)
        
        log('%s:' % signature)
        log.indent += 2
        try:
            result = f(*args)
            log.indent -= 2
        except Exception as e:
            log(signature, ' exited due to %s' % (str(e) or 'an exception'))
            log.indent -= 2
            raise
        log(f'{signature} ==> {result}')

        log.file = cur_logfile
        return result
    return _f


def disabled(f, *ignore): return f  # used to disable a decorator

if not config.debug: trace = disabled


def format_call(f, args, formatter):
    if f.__name__ == '_func':
        f, args = args
    return '%s%s' % (f.__name__, formatter(args))


def interact(func):
    print('interactive testing of calc_parse:')
    record = {}
    while True:
        exp = input('>>> ')
        if exp in 'qQ':
            return record
        else:
            result = func(exp)
            pprint(result)
            record[exp,] = None  # for writing to testfile
            
def check(f, args, expected, record=None):
    args = freeze(args)
    actual = f(*args)
    if not deep_compare(expected, actual):
        print(f'Wrong Answer of {f.__name__}{args}\n'
              f'Expected: {pformat(expected)}\n'
              f'Actual: {pformat(actual)}\n')
        if record is not None:
            record[args] = actual
        return False
    return True

def deep_compare(l1, l2):
    if type(l1) not in (tuple, list, dict):
        if l1 != l2:
            print(l1, 'VS', l2)
            return False
        else:
            return True
    elif len(l1) != len(l2):
        print(l1, 'VS', l2)
        return False
    elif type(l1) is dict:
        return all(deep_compare(l1[k], l2[k]) for k in l1)
    else:
        return all(deep_compare(i1, i2) for i1, i2 in zip(l1, l2))
    
def freeze(l):
    "recursively convert the list to a tuple"
    if type(l) in [list, tuple]:
        return tuple(freeze(x) for x in l)
    else:
        return l

def check_record(filename, func, record=None):
    funcname = func.__name__
    all_tests = json.load(open(filename, 'r'))
    testcases = all_tests[funcname]
    testcases = {freeze(args): exp for args, exp in testcases}
    if record is None: record = {}
    record.update(testcases)
    passed = all([check(func, args, exp, record)
                  for args, exp in record.items()])
    if passed:
        print('All tests passed for %s!' % funcname)
    elif input('Rewrite %s testcases? (y/N) ' % funcname) == 'y':
        all_tests[func.__name__] = tuple(record.items())
        json.dump(all_tests, open(filename, 'w'), indent=2)
