# My calculator

Dependencies: python 3.8+, sympy package

Run `python calc.py` to start the program.

In this calculator, there are five types of values: Number, Symbol, List, Range and Function.
Every evaluation will return a value of one of these five types.

Check the file "_builtins.py" to see the available built-in operations and functions.

## Features

* Evaluation of simple arithmetic expressions  

  **Examples**:  `1+3`; `0.5*2`; `-8^(4-2)`; `147%43` (modular arithmetic); `52//17` (integer division); `1e10*3e-5` (scientific notation); `0b0101 & 0b1110` (bit-wise AND; return: 4); `0b0101 | 0b1110` (bit-wise OR; return: 15)

* $\pi$ and $e$
  
  To input the values of $\pi$ and $e$, use `PI` and `E` respectively.

* Complex numbers

  The symbol `I` represents the imaginary number 'i' in mathematics.  

  **Examples**:  

  * `(3+4I)(2-6I)`
  * `z=3+4I`  
    [real[z], imag[z], angle[z], abs[z], conj[z]]  
    (return: [3.0, 4.0, 0.927295, 5.0, 3.0 - 4.0ⅈ])
  * `E^(PI*I)`  (return: ... you must know)

* Evaluation of boolean expressions  

    Return 1 if the result is true, otherwise return 0.  

    **Examples**: `3 > 2`; `x==y xor x==z`; `x > 0 and x < 2`; `not (a or b) == (not a and not b)`


* Conditional expression  

  **Syntax 1**:  
  *exp1* if *cond* else *exp2*  

  **Note**:  
  Short circuit evaluation is used - if `cond` is true, `exp1` will be evaluated but `exp2` will not, and vice versa.

  **Examples**:  

  * `1/0 if 0 else 1`  (return: 1)
  * `ramp[x] = 0 if x<0 else x`

  **Syntax 2**:  
  when(*cond1*: *exp1*, *cond2*: *exp2*, ... , *default*)  

  **Note**:  
  The *default* part does not have a condition preceding it and it is *mandatory*. This is completely equivalent to "*exp1* if *cond1* else *exp2* if *cond2* else ... else *default*".

  **Examples**:  

  * `max[x, y, z] = when(x > y and x > z: x, y > z: y, z)`

* Definition and evaluation of variables  

  A legitimate variable name **begins with a letter** and only contains digits, letters, underscores and '?' (usually added at the end of the name of a test function).  

  **Note**:  
  Thanks sympy, variable names that are greek letters will be displayed by the corresponding unicode characters. For instance, `pi` will be printed as π, `Sigma` as Σ, `alpha1` as α₁ and `gamma_i` as γᵢ. Note that `pi` is regarded as a symbol - for the constant value of $\pi$, use `PI`.  

  **Syntax**:  *var* = *exp*  
  (italic parts should be replaced by appropriate contents) 

  **Examples**: `x = 1`; `alpha = 0.05`; `g = x > 2`

* Symbol  

  In the `symbolic` mode, all undefined names will be regarded as symbols.  

  If this mode is off, then a symbol can be created by a single quotation mark `'` followed by a variable name.  

  **Examples**: `'James`, `diff['x^2 +ln('x), 'x]` (for functions like `diff`(differentiation), `int`(integral), variable names had better begin with `'` in case of existing bindings)  

* Definition and evaluation of functions

  **Examples**:  

  * `f[x, y] = 2x + y`
  * `f[3, 2]`
  * `cot[x] = 1/tan[x]`
  * `fact[n] = 1 if n==0 else n*fact[n-1]`
  * `g[x, y:1, z:2] = [x,y,z]` (default arguments)
  * `[g[3], g[3,-1]]` (return: [[3,1,2], [3,-1,2]])
  * `h[[x, y], *z] = [x, y, z]` (nested args and var-len args)  
    `h[[1, 2], 3]` (return: [1, 2, [3]])  
    `h[[1, [2]], 3, 4]` (return: [1, [2], [3, 4]])
  
  **Note**:  
  In Calc, a function is always a mapping from a argument list to an expression. The application of a function is done by preceding a list with this function. This is why I choose to use square brackets instead of the more commonly-used round parentheses. The argument list can be nested like usual lists. However, it additionally has default arguments (by using `:`) and var-len arguments (by using `*`). 

* List  

  **Syntax**: 
  [*exp1*, *exp2*, ...]  

  **Note**: The operators `in`, `+`, `*` have the same functions as those in Python.

  **Examples**:  
  * `3 in [1, 2, 3]`
  * `[1, 2] + [3, 4]`
  * `sum[1, 2, 3, 4]` (the `sum` function sums all arguments up)  
  * `sum[[1, 2], [3, 4]]` (since we can concatenate two lists by `+`, the `sum` function will concatenate all the lists; return: [1, 2, 3, 4])  


* List subscription  

  **Syntax**: *list*[$i_1$, ..., $i_n$]  
  The list is sequentially subscripted by $i_1$, $i_2$, ... Each of the indices is either an integer or an iterable value (List or Range). For an iterable subscript, it just maps each integer atom within it to the corresponding item in *list*.

  **Examples**:
  * `[1, 2, 3][1]`
  * `[1, 2][-1]` (return: 2)
  * s := [0, 2]  
    \[1, 2, 3][s] (return: [1, 3])  
  * \[1, 2, 3][[2, [1, 2], [0]]] (return: [3, [2, 3], [1]])
  * [a, b, c, d, e][[i for i in range(5) if i%2]] (return: [b, d])
  * m := [[1, 2, 3], [3, 4, 5]]  
    m[0, 1:] (return: [2, 3])

* List slicing  

  **Syntax**: `list`[`start`:`end`(:`step`)]  
  This syntax is identical to the list slicing syntax in python.  
  The second colon can be omitted, when `step` is 1 as default.  
  When `start` is omitted, it is set to 0; when `end` is omitted, it is set to the end of the list.  

  **Examples**:  
  * l := [1, 2, 3, 4, 5]  
  * [l[1:], l[:3], l[:], l[:2:-1], l[::2]] (return: [[2, 3, 4, 5], [1, 2, 3], [1, 2, 3, 4, 5], [5, 4], [1, 3, 5]])


* Anonymous functions

  An anonymous function allows you to directly create a function without assigning a name to it. 
  
  **Syntax**: *par* => *exp*

  **Note**: *par* can be a single argument or a list of arguments. For a single argument `x`, it has no difference between `x => ...` and `[x] => ...`.
  
  **Examples**:
  
  * `fact = n => 1 if n=0 else n*fact(n-1)`
  * `compose[f, g] = [*x] => f[g[*x]]`
  
* Local environment  

  **Syntax**:  
  * To create a local environment: (*par1*:*val1*, *par2*:*val2*, ...)
  * To evaluate an expression in a local environment: (*par1*:*val1*, ...) *exp*
  * To retrieve the bound value of a name in the environment:
  *env*.*name*  
    (*env* here should not be "(par:val, ...)" but a variable whose value is an environment; there must be no space following the dot)

  **Note**:
  Use `dir env` to display the bindings in `env`. You can also use `dir` to display global bindings.

  **Examples**:  

  * `person = (age: 21, gender: 'male, major: 'CS)`  
    `person.age < 30 and person.major in ['CS, 'CE]`
  * `(r: sqrt[x^2+y^2], t: atan[y/x]) [r*cos[t], r*sin[t]]`
  * `binomial[n, m] = 1 if (n==0 or m==0 or m==n) else (b1: binomial[n-1, m-1], b2: binomial[n-1, m]) b1 + b2`  
  * `d[f, d:1e-5] = x => (f[x+d]-f(x))/d`  
    `root_newton[f, x:0, thr:1e-5] = (df: d[f], update[x]: f[x]/df[x]) x if abs[f[x]] < thr else root_newton[f, update[x]]`  
    `root_newton[sin, 3]`  (note that in this example, `update` is bound with a function by writing `update[x]: ...` and it is the same as `update: x=>...`; return: 3.1416)

* Environment matching

  Instead of explicitly write a local environment, you can also create an environment by "matching"; that is, to match a variable with any expression (which creates a single-binding environment) or an argument list with a list-value expression.  
  Actually, when you apply a function, it will automatically do a matching to bind the arguments with values and create a local environment.

  **Syntax**: *par(s)* :: *exp*

  **Examples**:
  * `x::2` (return: (x: 2))
  * `y::9 3y` (return: 27)
  * `m = [a, [b, c]] :: [2, [[1, 0], 3]]`  
    `[m.a, m.b, m.c]` (return: [2, [1, 0], 3])

* Range  

    A range is a different type from list. It is useful to represent a wide range of numbers, i.e. range(1, 100000). For such a range, the calculation of each item is delayed, thus saving time and memory.  
    There are three ways to generate a "Range" type value: by using the symbol `..`, or by the built-in function `range`.  
    The expression `a..b` evaluates to a range including all integers from a to b. In addition, `a..b..c` creates an arithmetic sequence that begins with `a` following by `b` and ends with `c` (if `c` is not included by this sequence, then it ends before `c`).  
    The "range" function, however, is identical to its corresponding python function, which excludes the second argument from the range.  

  **Examples**:  
  * r := 1..4  
    list(r) (converts a range to a list, return: [1, 2, 3, 4])
  * l := 1..3..9 (return: 1..3..9)  
    list(l) (return: [1, 3, 5, 7, 9])
  * sum([i^2 | i in 1~10])
  * r := range(1, 4)  
    list(r) (return: [1, 2, 3])
  * r := range(9, 1, -2) (return: [9, 7, 5, 3])  

* List comprehension  

  **Syntax**:  
    [`exp` @ `arg1` in `range1` (and `cond1`) @ `arg2` in `range2` (and `cond2`) ...]  
    `@` is used to separate the expression and the constraints of the variables. For the constraint of a variable, a range must be provided, with an option of further constraints by adding `and <condition>`.  

  **Examples**:
  * [i | i in range(5) and i%2] (return: [1, 3])
  * [i*j | i in range(80) and i%3=2 and i%7=4 | j in range(50) and i%11=9 and i+j > 100] (return: [2544, 2597])
  * sum([i^2 | i in 1~10])
  * diff_poly(coeffs) := [coeffs[i*i] | i in range(len(coeffs)) and i > 0]

* History  

  Use the symbol \_ to represent the result of the last calculation, \_\_ the second last, \_\_\_ the third last, and so on (but you may not want to use longer ones XD).  
  Use keyword `_n` to represent the result of the calculation no.`n`.  
  Use keyword `env` to let the calculator print all variable bindings in the global environment.  

* Config

  Use keyword `conf` to config the calculator.  
  Available parameters:  

  * `prec`/`precision` (number of significant digits of decimals)
  * `latex` (all outputs will be in the LaTeX format)
  * `symbolic` (all undefined names will be regarded as symbols)
  * `tolerance` (if the difference of two numbers is within `tolerance`, they are considered equal)  

  **EXAMPLES**:
  * `conf prec 4`
  * `conf latex on`
  * `conf tolerance 1e-20`

* Multiline expression  

  Use `...` at the end of the line to indicate that the expression continues in the next line.  

* Omit output

  Use `;` at the end of the line to suppress the output.

* Comment  

  Use `#` to comment.  
  Special comments:
  * `#SCI`: use scientific notation (eg. a big integer)
  * `#TEX`: display in LaTeX format
  * `#BIN`: binary representation
  * `#HEX`: hexadecimal representation

  **Examples**:
  * `0b0101 | 0b1110 #BIN` (return: 0b1111)
  * `x/sqrt[x^2+1] #TEX` (return: \frac{x}{\sqrt{x^{2} + 1}})

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
