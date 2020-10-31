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

def check(f, arg, expected, record=None):
    actual = f(arg)
    if not rec_comp(expected, actual):
        print(f'Wrong Answer of {f.__name__}{tuple(arg)}\n'
              f'Expected: {pformat(expected)}\n'
              f'Actual: {pformat(actual)}\n')
        if record: record[arg] = actual
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

def check_record(filename, func):
    testcases = json.load(open(filename, 'r'))
    passed = all(check(func, *case, testcases)
                 for case in testcases.items())
    if passed: print('All tests passed!')
    return testcases, passed
    
def interact(func):
    record = {}
    prev = None
    while True:
        exp = input('>>> ')
        if exp in 'qQ':
            return record
        elif exp in 'wW':
            check(func, [prev], None, record)
        else:
            pprint(func(exp))
            prev = exp
