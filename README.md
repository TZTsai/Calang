# A small but powerful calculator

Dependencies: python 3.8+, sympy package

Run `python calc.py` to start the program.

In this calculator, there are five types of values: Number, Symbol, List, Range and Function.
Every evaluation will return a value of one of these five types.

Check the file "__builtins.py" to see the available built-in operations and functions.

## Features

* Evaluation of simple arithmetic expressions  

    **Examples**: 1+3, 0.5*2, -8^(4-2), 147 % 43 (modular arithmetic), 52 // 17 (integer division), 1e10 \* 3e-5 (supports scientific notation)

* Complex numbers

  The symbol `I` represents the imaginary number 'i' in mathematics.  

  **Examples**:  

  * (3+4I)*(2-6I)
  * z:=3+4I  
    [real(z), imag(z), angle(z), abs(z), conj(z)]  

* Evaluation of boolean expressions  

    Return 1 if the result is true, otherwise return 0.  

    **Examples**: 3 > 2, 2 = 2, x = y xor x = z, x > 0 and x < 2, not (a or b) = (not a and not b), 1 /\ 0, f \\/ g
    (note: /\ and \\/ resemble the symbols for "logical and" and "logical or" in mathematics. They are the same as `and` and `or` operations except higher priorities.)

* Definition and evaluation of variables  

    A legitimate variable name begins with a letter and only contains digits, letters, underscores and '?' (conventionally at the end of the name of a function that does a test).  

    **Note**: You can add a backslash before an English letter to convert it into its corresponding Greek letter! For instance, '\p' will be interpreted and printed as 'π'.  

    **Syntax**: `var` := `exp`  

    **Examples**: x := 1, \a := 0.05, g := x > 2, c := x if x > 2 else 0, sqr?(x) := (sqrt(x)//1)^2 = x

* Definition and evaluation of functions  

  **Examples**:  

  * f(x, y) := 2x + y
  * f(3, 2) = 8
  * cot(x) := 1/tan(x)  
  * fact(n) := 1 if n=0 else n*fact(n-1)
  * d(f) := lambda x: (f(x+0.0001)-f(x))/0.0001;  
    newton(f, x) := with update = lambda x: x - f(x)/d(f)(x): ...
    x if abs(f(x)) \< 0.0001 else newton(f, update(x));  
    newton(sin, 3)  (return: 3.1416)

* Lambda expression  

  A lambda expression directly evaluates to a function.  
  
  **Syntax 1**: lambda `par1`, `par2`, ... : `exp`  
  
  (note: The character `@` can be added at the beginning of the last to denote that it has a variable length, like the `*` form in python.)  
  
  **Examples**:
  
  * fact := lambda n: 1 if n=0 else n*fact(n-1)
  * compose := lambda f, g: x -> f(g(x))  
  * map := lambda f, %lists: [] if any([l = [] | l in lists]) else with args = [l\[0\] | l in lists], rests = \[l\[1:] | l in lists]: \[f(@args)] + map(f, @rests)
  
  **Syntax 2**: (`par1`, `par2`) -> `exp`  (the parentheses can be omitted if there is exactly one parameter)  
  
  **Examples**:  
  
  * double := f -> (x -> f(f(x)))
  * inc := x -> x+1
  * double(inc)(3) (return: 5)
  
* Conditional expression  

  **Syntax 1**: `exp1` if `cond` else `exp2`  
  (note: if `cond` holds then the expression is evaluated as `exp1`, otherwise as `exp2`. `exp1` will be evaluated first even if `cond` is false. `exp2`, however, will not be evaluated if `cond` is true.)

  **Examples**:  

  * step(x) := 0 if x<0 else 1  
  * ramp(x) := 0 if x<0 else x  
  * rect(x) := 0 if x<-1 else 1 if x<=1 else 0  

    **Syntax 2**: when(`cond1`, `exp1`; `cond2`, `exp2`; ... ; `default`)  

  (note: The `default` expression does not have a condition preceding it.
  In comparison to the 'if-else' syntax, the 'when' syntax is fully short-circuited
  \- if one condition is found to be true, all following conditions and their corresponding expressions will not be evaluated.)  

  **Examples**:  

  * max(x, y, z) := when(x > y and x > z: x, y > z: y, z)
  * when(a/\\b: 1, (not a)/\\(not b): 2, 4)

* Local environment  

  **Syntax**: with *par1*=*val1*, *par2*=*val2*, ... : *exp*  
  In fact, it is identical to (lambda `par1`, `par2`, ... : `exp`)(`val1`, `val2`, ... ), so the "with" expression will not change the current environment.  

  **Examples**:  

  * with exp = a_very_long_expression: sqrt(exp) + exp + exp^2  
  * binomial(n, m) := 1 if (n=0 or m=0 or m=n) else with b1=binomial(n-1, m-1), b2:binomial(n-1, m): b1 + b2  
  * x := 2  
      with x=4: x * 2 (return: 8)  
      x (return: 2)

* Symbol  

    In the `ALL-SYMBOL` mode, all undefined names will be regarded as symbols.  

    If this mode is off, then symbol is represented by an underscore `_` followed by a legitimate variable name.  

    **Examples**: \_x, \_y, \_angle, diff(\_x^2 +ln(\_x), \_x) (underscores can be removed in `ALL-SYMBOL` mode)

* List  

  **Syntax**: [`exp1`, `exp2`, ...]  
  The keyword `in` can examine whether an element is contained in a list.  
  The operation `+` can concatenate two lists together.  

  **Examples**:  
  * l := [1, 2, 3]  
    3 in l
  * [1, 2]+[3, 4]  
  * sum([1, 2, 3, 4]) (the "sum" function returns the sum of all elements of a list)  
  * sum([[1, 2], [3, 4]]) (since we can concatenate two lists by "+", the "sum" function will concatenate all lists in the list) (return: [1, 2, 3, 4])  

* List subscription  

  **Syntax 1**: `list>@\<index`  
  You can use either an integer, a list or a range as the index of the list. When using a list or a range, you will get a sub-list containing the elements whose indices lie in this range.  

  **Syntax 2**: `list>[\<i1`, `i2`, ..., `in`]  
  This syntax is equivalent to sequentially subscripting `list` by `i1`, `i2`, ...  
  **Note**: The advantage of the `@` symbol is that it is actually an operation, so the expression on its right is evaluated first. Thus, you are allowed to evaluate expressions like `l@s`, `l@[1, 2, 5]`, etc. Its disadvantage is that you are unable to slice the list till its end.  

  **Examples**:  
  * [1, 2, 3]@1
  * \[1, 2][-1] (a negative index means counting from the end of the list) (return: 2)
  * [1, 2, 3]@(1~2) (return: [2, 3])
  * [1, 2, 3, 4, 5]@[i for i in range(5) if i%2] (return: 2, 4)
  * m := [[1, 2, 3], [3, 4, 5]]  
  m[0, 1] (return: 2)

* List slicing  

  **Syntax**: `list>[\<start>:\<end>(:\<step`)]
  This syntax is identical to the list slicing syntax in python.  
  The second colon can be omitted, when `step` is 1 as default.  
  When `start` is omitted, it is set to 0; when `end` is omitted, it is set to the end of the list.  

  **Examples**:  
  * l := [1, 2, 3, 4, 5]  
  * [l[1:], l[:3], l[:], l[:2:-1], l[::2]] (return: [[2, 3, 4, 5], [1, 2, 3], [1, 2, 3, 4, 5], [5, 4], [1, 3, 5]])

* Range  

    A range is a different type from list. It is useful to represent a wide range of numbers, i.e. range(1, 100000). For such a range, on the one hand, the calculator will print "range(1, 100000)" instead of a really long list as the output; on the other hand, internally, a range is not directly evaluated to all the numbers it covers. Instead, it send a number to the calculator and changes to its next state, "range(1, 100000)" to "range(2, 100000)" as an example. Thus it saves the memory.  
    There are two ways to generate a "range" type value: by using the symbol "\~" or by the built-in function "range".  
    The expression "a\~b" evaluates to a range including all integers from a to b.  
    The "range" function, however, is identical to its corresponding python function, which excludes the second argument from the range. Besides, you can use a third argument in the function "range" to specify the step of the range.
    If a range is used as the index of a list, a sub-list containing elements whose indices lies in this range will be returned.  

  **Examples**:  
  * r := 1~4  
  * list(r) (converts a range to a list, return: [1, 2, 3, 4])
  * sum([i^2 | i in 1~10])
  * r := range(1, 4), list(r) (return: [1, 2, 3])
  * r := range(9, 1, -2) (return: [9, 7, 5, 3])  

* List comprehension  

    [`exp` | `arg1` in `range1` (and `cond1`) | `arg2` in `range2` (and `cond2`) ...]  

  **Examples**:
  * [i | i in range(5) and i%2] (return: [1, 3])
  * [i*j | i in range(80) and i%3=2 and i%7=4 | j in range(50) and i%11=9 and i+j > 100] (return: [2544, 2597])
  * sum([i^2 | i in 1~10])
  * diff_poly(coeffs) := [coeffs[i*i] | i in range(len(coeffs)) and i > 0]

* History  

  Use the symbol \_ to represent the result of the last calculation, \_\_ the second last, \_\_\_ the third last, and so on (but you may not want to use longer ones XD).  
  Use keyword `_``n` to represent the result of the calculation no.`n`.  
  Use keyword `ENV` to let the calculator print all variable bindings in the global environment.  

* Config

  Use keyword `conf` to config the calculator.  
  Available parameters:  

  * PREC (significant digits of decimals)
  * LATEX (all outputs will be in the LaTeX format)
  * ALL-SYMBOL (all undefined names will be regarded as symbols)
  * TOLERANCE (if the difference of two numbers is within TOLERANCE, they are considered equal)  

  **EXAMPLES**:
  * conf PREC 4
  * conf LATEX on
  * conf LATEX off
  * conf TOLERANCE 1e-20

* Multiline expression  

  Use `...` at the end of the line to indicate that the expression continues in the next line.  

* Omit displaying result

  Use `;` at the end of the line.  

* Comment  

  Use `#` to comment.  

* Load files  

  Use the keyword "load" appended by a sequence of file names (located in "modules") to load these files. You can use "ENV" after the loading to check what definitions have been appended.  
  The calculator will run through the loaded file and load its definitions into the current environment. However, the current evaluation history will not be affected.  
  The loading command has two extra options: verbose and test. To turn on the verbose option, add "-v" in your command; to turn on the test option, add "-t" in your command. The testing process will be explained in the next section.  
  
  **Examples**:  
  * load ../examples/merge_sort examples/btree
  * 12  
    load somefile  
    _ (return: 12)

  * load la -t (la is my linear algebra library)  

  * load scinums -v

* Create modules and testing  

  If you want to write a module by yourself, create a file inside the "modules" directory and write your definitions in it. To test your module, add the expected value after an expression as a comment. Besides, to better organize your module, you can separate your definitions and tests; if you add a line of comment: "#TEST" and put tour tests below it, the calculator will not run these tests when you load without the test option.  
  
  **An example of a module**:  
  * (Inside a module "sample")  
    f(x) := x^2 + 2*x + 1;  
const := sqrt(2) - 1;  
    \#TEST  
    f(const)  #2
  * (In the calculator)  
    load sample -t (it will tell you tests have been passed)  
    const (return 0.4142)

* Import python modules

  Use the keyword "import" appended by a sequence of python module names (located in "pymodules") to import the definitions in these modules. To create such an importable module, you must create a python file in the "pymodules" directory and define a dict "definitions", containing the definitions you want to export (the main program will only import "definitions" in this file). This feature is used to empower calculator with python functions and powerful python modules like numpy and sympy.  

  **Example**:  
  * import gauss_jordan

* Exit  

  Ctrl+C or exit()

You can find more examples in the "examples" folder.
