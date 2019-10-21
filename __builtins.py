import math

builtins = {'sin':math.sin, 'cos':math.cos, 'tan':math.tan, 
'asin':math.asin, 'acos':math.acos, 'atan':math.atan,
'abs':abs, 'sqrt':math.sqrt, 'floor':math.floor, 'ceil':math.ceil,
'log':math.log, 'E':math.e, 'Pi':math.pi, 'range':range,
'sum':lambda f, l: sum(f(x) for x in l), }