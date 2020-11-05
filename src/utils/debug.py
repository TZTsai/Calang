import sys
import json
from pprint import pformat, pprint
import config


indent = '  '
max_depth = 20
def log(*messages, end='\n', sep=''):
    if not config.debug: return
    log.out.write(log.depth*indent)
    if log.depth < max_depth:
        log.out.write(sep.join(map(str, messages)) + end)
    else:
        print('max depth reached!')
        exit(-1)

log.depth = 0
log.out = sys.stdout

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
