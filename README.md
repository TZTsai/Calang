# A small but powerful calculator

In this calculator, there are four types of values: Number, List, Range and Function.
Every evaluation will return a value of one of these four types.  

## Features

- Evaluation of simple arithmetic expressions  
    **Examples**: 1+3, .5*2, -8^(4-2), 147 % 43 (modular arithmetic), 52 // 17 (integer division), 8 & 3 (bitwise and operation), 1e10 \* 3e-5 (support scientific notation)
- History  
    Use keyword "ans" to represent the result of the last calculation.  
    Use keyword "ans.\<n>" to represent the result of the \<n>th calculation.
- Complex numbers  
    The keyword "I" represents the imaginary number "i" in mathematics.  
    **Examples**: (3+4I)*(2-6I)
- Evaluation of boolean expressions  
    return 1 if the result is true, otherwise return 0  
    **Examples**: 3 > 2, 2 = 2, x = y xor x = z, x > 0 and x < 2, not (a or b) = not a and not b (a tautology)
- Definition and evaluation of variables  
    **Syntax**: \<var> := \<exp>  
    **Examples**: x := 1, bool := x > 2, c := x if x > 2 else 0
- Definition and evaluation of functions  
    **Examples**:  
  - f(x, y) := 2x + y  
  - cot(x) := 1/tan(x)  
  - d(f) := {x} (f(x+0.0001)-f(x))/0.0001
  - fact(n) := 1 if n=0 else n*fact(n-1)
  - merge(l1, l2) := cases: l1, empty?(l2); l2, empty?(l1); [l1@0]++merge(tail(l1),l2), l1@0 < l2@0; [l2@0]++merge(l1, tail(l2))
- Display the bindings of variables
    Use keyword "ENV".
- Lambda expression (anonymous function)  
    **Syntax**: {\<par1>, \<par2>, ...} \<exp>  
    **Examples**: fact := {n} 1 if n=0 else n*fact(n-1), compose := {f, g} {x} f(g(x))
- Conditional expression  
    **Syntax 1**: \<exp1> if \<cond> else \<exp2> (if \<cond> holds then the expression is evaluated as \<exp1>, otherwise as \<exp2>)  
    **Examples**: step(x) := 0 if x<0 else 1, ramp(x) := 0 if x<0 else x  
    **Syntax 2**: cases: \<exp1>, \<cond1>; \<exp2>, \<cond2>; ... ; \<expElse> (note that for the lase expression there is no condition to examine)  
    **Examples**: max(x, y, z) := cases: x, x > y and x > z; y, y > z; z
- List  
    **Syntax**: [\<exp1>, \<exp2>, ...]  
    Use the symbol "@" to obtain the elements of a list by its index (beginning from 0).  
    Index chaining: use a list of indices @[i1, i2, ...] to represent @i1@i2@i3@...  
    The keyword "in" can examine whether an element is contained in a list.  
    The operation "++" can concatenate two lists together.  
    **Examples**: l := [1, 2, 3], 3 in l, l@1, m := [[1, 2], [3, 4]], m@[0, 1] (will return 2), [1, 2]++[3, 4], sum([1, 2, 3, 4]) (the builtin function "sum" will return the sum of all elements of a list)  
- Range  
    A range is a different type from list. A value of type "range" is an instance of the python class range.  
    There are two ways to generate a "range" type value: by using the symbol "\~" or by the builtin function "range".  
    The expression "a\~b" evaluates to a range including all integers from a to b.  
    The "range" function, however, is identical to the python function "range", which excludes the second argument from the range. Besides, you can use a third argument in the function "range" to specify the step of the range.  
    If a range is used as the index of a list, a sub-list containing elements whose indices lies in this range will be returned.  
    **Examples**: r := 1~4, list(r) (list is a builtin function which converts a range to a list, this expression evaluates to [1, 2, 3, 4]), r := range(1, 4), list(r) ([1, 2, 3]), r := range(9, 2, -2) ([9, 7, 5, 3])
- List comprehension  
    Use the same syntax as in python: [\<exp> for \<arg1> in \<range1> if \<cond1> for \<arg2> in \<range2> if \<cond2> ...]  
    Note that \<range> does not necessarily have to be a range type value - it can also be a list.  
    **Examples**: [i for i in range(4) if i%2], m := [[1, 2, 3],[3, 4, 5],[5, 6, 7]], m@[range(2), [i for i in [0, 1, 2] if i%2]] (What is its value? Answer: [[2],[4]]), [i\*j for i in range(10) if i%3 for j in range(10) if i+j>6], sum([i^2 for i in 1~10]), sin_approx(n) := {x} sum([(-1)^(i // 2)\*x^i/fact(i) for i in 1~n if i%2])

## Builtins

- Operations: +, -, *, /, //, ^, %, &, |, =, !=, <, >, <=, >=, in, xor, @, ++, ~, and, or, -, not, !
- Functions: sin, cos, tan, asin, acos, atan, abs, sqrt, floor, ceil, log, range, max, min, list, binom, log10, log2, exp, sum, prod, fact(factorial), empty? (tell whether a list or a range is empty), len (the length of a list or a range), number? (tell whether a value is a number), iter? (tell whether a value is a list or a range (both are iterables)), function?, list?, range?
- Constants: E, PI, I  
