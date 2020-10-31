import sys
import json
from pprint import pformat, pprint


indent = '  '
def log(*messages, end='\n', sep=''):
    if log.out is None: return
    msg = log.depth*indent + sep.join(map(str, messages)) + end
    log.out.write(msg)

log.depth = 0
log.out = sys.stdout

def check(f, args, expected, record=None):
    if type(args) is not tuple:
        args = tuple(args)
    actual = f(*args)
    if not rec_comp(expected, actual):
        print(f'Wrong Answer of {f.__name__}{args}\n'
              f'Expected: {pformat(expected)}\n'
              f'Actual: {pformat(actual)}\n')
        if record: record[args] = actual
        return False
    return True

def rec_comp(l1, l2):
    if type(l1) not in (tuple, list):
        if l1 != l2:
            print(l1, 'VS', l2)
            return False
        else:
            return True
    elif len(l1) != len(l2):
        print(l1, 'VS', l2)
        return False
    else:
        return all(rec_comp(i1, i2) for i1, i2 in zip(l1, l2))

def check_record(filename, func, record={}):
    all_tests = json.load(open(filename, 'r'))
    testcases = all_tests[func.__name__]
    testcases = {tuple(args): exp for args, exp in testcases}
    record.update(testcases)
    passed = all([check(func, args, exp, record)
                  for args, exp in record.items()])
    if passed:
        print('All tests passed!')
    elif input('rewrite? (y/N) ') == 'y':
        all_tests[func.__name__] = tuple(record.items())
        json.dump(all_tests, open(filename, 'w'))
