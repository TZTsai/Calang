# TODO

1. 环境ENV的实现
2. 语法树化简
3. 语法树求值：applicative order
4. FIT的实现：由值为列表的EXP与"->"标记组成的对象，可以应用到一个符号列表（FORMAL）之上。他会与FORMAL进行形式和值的匹配，生成符号与值的绑定（BIND），也就是ENV
5. MAP的实现：由FORMAL，"->"标记，和一个EXP组成。首先将EXP尽量化简（可以求值的分支就求值，遇到NAME则保留当前结构），生成一个简化的语法树并储存在MAP对象中。同时储存FORMAL和创建该对象的ENV。将MAP应用到一个列表上时，先将列表FIT到自身的FORMAL之上，生成一个ENV，该ENV的上级即MAP自身的ENV。然后在该ENV中求EXP的值。
6. 定义ENV时将自身作为取值环境：例如`(x: 3, y: x+2)`，y可以求值为5。
7. OOP的实现：可以定义返回ENV的函数，并且实现继承功能。
8. operations: is (check type), @ (A@B x == A x -> B x)
