import sys
import json
from pprint import pformat, pprint
import config


def log(*messages, debug=True, end='\n', sep='',
        indent='default', out='default'):
    if not config.debug and debug:
        return
    
    if out == 'default':
        out = log.out
    if indent == 'default':
        indent = log.indent
        
    message = sep.join(map(log.format, messages))
    log.out.write(indent * ' ' + message + end)

log.indent = 0
log.format = str
log.out = sys.stdout
# log.out = open('src/utils/log.yaml', 'w')

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
    "recursively convert list $l to a tuple"
    if type(l) is list:
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
