# Calc: my calculator

Dependencies: python 3.8+, sympy package

Run `python calc.py` to start the program.

Check "builtin.py" to see the available built-in operations and functions.

## Features

* Simple arithmetic expressions  

  **Examples**:  `1+3`; `0.5*2`; `-8^(4-2)`; `147%43` (modular arithmetic); `52//17` (integer division); `1e10*3e-5` (scientific notation); `0b0101 & 0b1110` (bit-wise AND; return: 4); `0b0101 | 0b1110` (bit-wise OR; return: 15)

* π and e
  
  To input the math constants π and e, use `PI` and `E` respectively.

* Complex numbers

  The symbol `I` represents the imaginary number 'i' in mathematics.  

  **Examples**:  

  * `(3+4I)(2-6I)`
  * `z=3+4I`  
    `[real[z], imag[z], angle[z], abs[z], conj[z]]`
    (return: [3.0, 4.0, 0.927295, 5.0, 3.0 - 4.0ⅈ])
  * `E^(PI*I)`  (return: ... you must know)

* Boolean operations  

    Return 1 if the result is true, otherwise return 0.  

    **Examples**: `3 > 2`; `x==y xor x==z`; `x > 0 and x < 2`; `not (a or b) == (not a and not b)`

* Conditional expression  

  **Syntax 1**:  
  `_exp1_ if _cond_ else _exp2_`  
  Variables wrapped by `_` should be replaced by the corresponding expressions.

  **Note**:  
  Short circuit evaluation is used - if `cond` is true, `exp1` will be evaluated but `exp2` will not, and vice versa.

  **Examples**:  

  * `1/0 if 0 else 1`  (return: 1)
  * `ramp[x] = 0 if x<0 else x`

  **Syntax 2**:  
  `when(_cond1_: _exp1_, _cond2_: _exp2_, ... , _default_)`  

  **Note**:  
  The `default` part does not have a condition preceding it. This is completely equivalent to `_exp1_ if _cond1_ else _exp2_ if _cond2_ else ... else _default_`.

  **Examples**:  

  * `max[x, y, z] = when(x > y and x > z: x, y > z: y, z)`

* Variable

  A legitimate variable name **begins with a letter** and only contains digits, letters, underscores and '?' (usually added at the end of the name of a boolean-value function).  

  **Note**:  
  Thanks sympy, variable names that are greek letters will be displayed by the corresponding unicode characters. For instance, `pi` will be printed as π, `Sigma` as Σ, `alpha1` as α₁ and `gamma_i` as γᵢ. Note that `pi` is regarded as a symbol - for the constant value of π, use `PI`.  
  As a short hand, you can add a backslash `\` at the start of an English letter (with the exception of `\th`: θ and `\ps`: ψ) to convert it into its corresponding Greek letter.

  **Syntax**:  `_var_ = _exp_`  

  **Examples**: `x = 1`; `alpha = 0.05`; `g = x > 2`; `\a = 1.2`

* Symbol  

  In the `symbolic` mode, all undefined names will be regarded as symbols.  

  A symbol can also be created by a single quotation mark `'` followed by a variable name (regardless `symbolic` is on or off).  

  **Examples**: `'James`, `'\a_1` (printed as 'α₁'), `diff['x^2 +ln('x), 'x]` (for functions like `diff`(differentiation), `int`(integral), variable names had better begin with `'` in case of existing bindings)  

* Map

  A map maps a parameter list to an expression. To apply a map to a list of values, precede the list with this map.
  
  **Syntax**: `_par_ => _exp_`

  **Note**:  
  * `par` can be a single parameter or a list of parameters. For a single parameter `x`, it has no difference between `x => ...` and `[x] => ...`.
  * The parameter `par` has a similar form to normal lists (can be nested). However, it additionally allows optional parameters (by using `=`) and an extra parameter (by using `~`: `args~` is the same as `*args` in python).
  
  **Examples**:
  
  * `a = 10`  
    `f = [] => a`  
    `f[]` (return: 10)  
    `a = [1, 2]`  
    `f[]` (return: [1, 2])
  * `f = [a, b] => x => a*x + b`  
    `g = f[2, 3]`  
    `g[4]` (return: 11)
  * `f = [a, [b, c], d~] => [a, b, c, d]`  
    `f[1, [2, 3], 4, 5]` (return: [1, 2, 3, [4, 5]])
  * `f = [x='none] => [] if x is 'none else [x]`  
    `f[] == [] and f[2] == [2]` (return: 1)
  
* Map definition

  A variable can be bound to a map like any other types of values. But as a shorthand, you can define the map by
  
  **Syntax**: `_name_ _par_ = _exp_`

  **Examples**:  

  * `f[x, y] = 2x + y`
  * `f[3, 2]`
  * `cot[x] = 1/tan[x]`
  * `fact[n] = 1 if n==0 else n*fact[n-1]`
  * `g[x, y=1, z=2] = [x,y,z]` (default parameters)
  * `[g[3], g[3,-1]]` (return: [[3,1,2], [3,-1,2]])
  * `h[[x, y], z~] = [x, y, z]` (extra parameter)  
    `h[[1, 2], 3]` (return: [1, 2, [3]])  
    `h[[1, [2]], 3, 4]` (return: [1, [2], [3, 4]])
  
* List  

  **Syntax**:
  `[_exp1_, _exp2_, ...]`

  **Note**: For lists, operations can be automatically broadcasted. The operation `in` allows you to check whether a value is an item of a list. The operation `&` finds common items between two lists and `|` concatenates two lists together. Besides, you can use `~` to unpack a list into its outer list (if it is not nested in a list, this will be an error).

  **Examples**:  
  * `3 in [1, 2, 3]`
  * `[1, 2] | [3, 4]` (return: [1, 2, 3, 4])
  * `1 | [2, 3] | 4` (return: [1, 2, 3, 4])
  * `a = [2, 3]`  
    `[1, a~]` (return: [1, 2, 3])
  * `sum[1, 2, 3, 4]` (the `sum` function sums all arguments up)  

* List subscription  

  **Syntax**: `_list_[_i1_, ..., _in_]`  
  The list is sequentially subscripted by `i1`, ..., `in`. Each of the indices is an integer. If an index is negative, it will subscribe from the end, like python.

  **Examples**:
  * `[1, 2, 3][1]`
  * `[1, 2, 3][-1]` (return: 3)
  * `m = [[1, 2, 3], [3, 4, 5]]`  
    `m[0, 1]` (return: 2)

* List slicing  

  **Syntax**: `_list_[_start_:_end_(:_step_)]`  
  This syntax is identical to the list slicing syntax in python.  
  The second colon can be omitted, where `step` is 1 as default.  
  When `start` is omitted, it is set to 0; when `end` is omitted, it is set to the end of the list.  

  **Examples**:  
  * `l = [1, 2, 3, 4, 5]`
  * `[l[1:], l[:3], l[:2:-1], l[::2]]` (return: [[2, 3, 4, 5], [1, 2, 3], [5, 4], [1, 3, 5]])
  * `m = [[1, 2, 3], [3, 4, 5]]`  
    `m[:, 1:3]` (return: [[2, 3], [4, 5]])

* Range  

  A range is a different type from list. It is useful to represent a wide range of numbers, eg. `1..1000`. For such a range, the calculation of each item is delayed, thus saving time and memory.  

  **Syntax**:
  * `_start_.._end_`  
  This evaluates to a range including all integers from `_start_` to `_end_`.  
  * `_start_.._next_.._end_`  
  This creates an arithmetic sequence that begins with `_start_` **followed** by `_next_` and ends with `_end_` (if `_end_` is not included in this sequence, then it ends before `_end_`).  
  * `_start_.._step_+.._end_`  
  This creates an arithmetic sequence that has a step of `_step_`.  
  * `_start_.._step_-.._end_`  
  This is equivalent to `_start_..-_step_+.._end_` (the step is the negative of `_step_`).

  **Examples**:  
  * `r = 1..4`  
    `list[r]` (return: [1, 2, 3, 4]; `list` converts a range to a list)
  * `list[1..3..9]` (return: [1, 3, 5, 7, 9])
  * `list[1..3+..9]` (return: [1, 4, 7])
  * `sum[i^2 for i in 1..10]`

* List comprehension  

  **Syntax**:  
    `[_exp_ for _arg1_ in _range1_ (if _cond1_) for _arg2_ in _range2_ (if _cond2_) ...]`  
    The `if` parts are optional.

  **Examples**:
  * `[i for i in 1..5 and i%2]` (return: [1, 3, 5])
  * `[i for i in 1..100 if i%3==2 and i%7==4 and i%11==9]` (return: [53])
  * `f[n] = [[i, j] for i in 0..n for j in 0..i-1 if i+j == n]`  
    `f[6]` (return: [[4, 2], [5, 1], [6, 0]])
  * `diff_poly[coeffs~] = [coeffs[i]*i for i in 1..len[coeffs]-1]`
    `diff_poly[1,2,3]` (return: [2, 6])

* Environment  

  An environment is a collection of name-value bindings. Actually normally we are evaluating in the *Global* environment. When you create an environment yourself, it will set its parent to the current environment it is being evaluated.

  The evaluation rule within an environment: when a name is evaluated in an environment, Calc will first check whether it is bound in this environment; if not, Calc will go up to look up its value in its parent environment; this procedure will continue recursively until it reaches the *Global* environment - if it is still unbound, it will be evaluated as a Symbol or an NameError will be raised dependent on the user config.

  **Syntax**:  
  * To create an environment:  
    `(_par1_=_val1_, _par2_=_val2_, ...)`  
    pars must be names, not numbers
  * To evaluate an expression in an environment:  
    * `(_par1_=_val1_, ...) _exp_`
    * `@_env_ _exp_` (`_env_` is a variable of environment)
  * To retrieve the bound value of a name in the environment:  
    `_env_._name_`  
    here `_env_` should be a variable of environment not a bracketed environment

  **Note**:
  Use `dir _env_` to display the bindings in `_env_`. You can also use `dir` to display global bindings.

  **Examples**:  

  * `person = (age = 21, gender = 'male, major = 'CS)`  
    `person.age < 30 and person.major == 'CS`
  * `(r=sqrt[x^2+y^2], t=acos[x/r]) r*sin[t]` (bindings are evaluated sequentially and later bindings can make use of previous bindings)
  * `binomial[n, m] = 1 if (n==0 or m==0 or m==n) else (b1=binomial[n-1, m-1], b2=binomial[n-1, m]) b1 + b2`  
  * `d[f, d=e-5] = x => (f[x+d]-f[x])/d`  
    `root_newton[f, x=0, thr=1e-5] = (df=d[f], update[x]=f[x]/df[x]) x if abs[f[x]] < thr else root_newton[f, update[x]]`  
    `root_newton[sin, 3]`  (return: 3.1416; note that `update[x]= ...` is allowed as a binding and it is the same as `update = x=>...`)

* Attribute

  An attribute is a bound name in an environment. You can define an attribute in the same way as defining a variable. You are also allowed to define attributes of a non-environment.

  **Examples**:
  * `e = (a=1, b=2)`  
    `e.a` (return: 1)  
    `e.a = (b=0)`  
    `e.a` (return: (b = 0))  
    `e.a.b` (return: 0)  
    `@e b` (return: 2; evaluates `b` in `e`)  
    `@e.a b` (return: 0)
  * `x = 2`  
    `x.neg = -2`  
    `x` (return: 2)  
    `x + 3` (return: 5)  
    `x.neg + 3` (return: 1)
  * `f[x] = (val=x, sq=x^2, sqrt=sqrt[x])`  
    `x = f[4]`  
    `x.sqrt` (return: 2)  
    `@f[4] sqrt` (return: 2)  
    `g[x] = @f[x] (double = 2*val)`  
    `y = g[4]`  
    `[y.val, y.sq, y.double]` (return: [4, 16, 8])

* String
  

* Parameter matching

  Instead of explicitly create an environment, you can also match a parameter (list) to a value.  
  Actually, when you apply a function, it will automatically do a matching to bind the parameters with the input arguments and create a local environment.

  **Syntax**: `_par(s)_ :: _exp_`

  **Examples**:
  * `x::2` (return: (x = 2))
  * `[x, y]::[2, 3] x+y` (return: 5)
  * `m = [a, [b, c]] :: [2, [[1, 0], 3]]`  
    `[m.a, m.b, m.c]` (return: [2, [1, 0], 3])

* History  

  Use the symbol % to represent the result of the last calculation, %% the second last, etc.  
  Use `%n` to represent the result of calculation no. `n`.  
  Only results that have been printed out will be recorded in the history, which means results of definitions, loading/importing and evaluation of expressions ending with `;` will not be recorded.

* Config

  Use keyword `config` to config the calculator.  
  Available parameters:  

  * `prec`/`precision` (number of significant digits of decimals)
  * `latex` (all outputs will be in the LaTeX format)
  * `symbolic` (all undefined names will be regarded as symbols)
  * `tolerance` (if the difference of two numbers is within `tolerance`, they are considered equal)  
  * `debug` (to show the internal calculation process)

  **EXAMPLES**:
  * `config prec 4`
  * `config latex on`
  * `config tolerance 1e-20`

* Multiline expression  

  Use `...` at the end of the line to indicate that the expression continues in the next line.  

* Single line with multiple expressions

  You can put several expressions in a single line. Use `;` to separate them.

* Omit output

  Use `;` at the end of the line to suppress the output.

* Comment  

  Use `#` to comment.  
  Special comments:
  * `#SCI`: display in scientific notation
  * `#TEX`: display in LaTeX format
  * `#BIN`: binary representation
  * `#HEX`: hexadecimal representation

  **Examples**:
  * `0b0101 | 0b1110 #BIN` (return: 0b1111)
  * `x/sqrt[x^2+1] #TEX` (return: \frac{x}{\sqrt{x^{2} + 1}})

* Load scripts  

  Use the keyword `load` followed by a Calc script name (located in "scripts") to load these files.  
  The calculator will run through the loaded script and load its definitions into the current environment. However, the current calculation history will not be affected.  
  The loading command has two extra options: verbose and test. To turn on the verbose option, add `-v` in your command; to turn on the test option, add `-t` in your command. The testing process will be explained in the next section.  
  
  **Examples**:  
  * `load examples.merge_sort`
  * `12`  
    `load scinums -v`  
    `_` (return: 12)
    `c0` (return: 299792458)

* Test scripts

  To test a script, add the expected value after an expression as a comment. Besides, you can separate your definitions and tests: if you add a line of comment: `#TEST` and put tour tests below it, the calculator will not run these tests when you load without the `-t` option.  
  
  **Examples**:  
  * (inside a script "example")  
    `f[x] = x^2 + 2x + 1`  
    `a = sqrt[2] - 1`  
    `#TEST`  
    `f[a] #2`  

    (in Calc)  
    `load example -v -t`  (will display the test result)  

* Import python files

  Calc can also import definitions from python files inside the "modules" directory. Use the keyword `import` followed by the name of a python file (located in "modules"). To create such an importable file, you must define a *dict* `definitions`, containing the definitions you want to export (Calc will only import `definitions`).  Besides, Calc allows you to directly import anything from *sympy*.  

  **Example**:  
  * `import gauss_jordan`  
    `inverse[[1,2],[4,3]]`
  * `import Matrix` (not found in "modules", import from sympy)  
    `m = Matrix[[[1,2],[4,3]]]; m.inv[]`

* Logging
  
  Use \`\` to wrap around text to let Calc print some information when evaluating the expression.  
  Like python f-string, inside \`\`, you can wrap an expression with `{}` to evaluate it.

  **Examples**:  
  * count_down[n] = \`n={n}\` 'end if n==0 else count_down[n-1]
  * count_up[n] = 'end if n==0 else count_up[n-1] \`n={n}\`
  
* Docstring

  Add a string wrapped by `""` at the end of a definition to create a docstring for the defined variable. Use the function `help` to display the docstring.

  **Examples**:  
  * `sr = 1.414 "square root of 2"`  
    `help[sr]`
  * `fact[n] = 1 if n <= 1 else n*fact[n-1] "factorial of an integer"`
    `help[fact]`

* Hotkeys
  * `Ctrl-C`/`Ctrl-D`: exit
  * `Ctrl-Z`: cancel current input
  * `Ctrl-N`: 

* Exit  

  `Ctrl-C` or a single command `exit`

You can find the detailed grammar of Calc in "grammar.txt". You can also find more examples in the "scripts/examples" folder.
