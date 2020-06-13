import sys
from _exec import run


if __name__ == "__main__":
    # usage:
    # python calc.py
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
