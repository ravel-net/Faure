from z3 import *
from isposs import *

import os
print(os.getcwd())
#test_is_poss_recur(rtable,ctable,var_dict)

# var_list = ['a','b','c','d','e','f']
# var_dict = gen_var_dict(var_list)
# for var in var_dict:
#     exec(f"{var} = Int('{var}') ") 
# rtable = [[1,2,3,4],
#       [1,2,3,5]]
# ctable = [
#     # [a,b,3,4,[]],
#     [1,2,3,c,[a!=1]],
#     [1,2,d,e,[b!=2, c!=4]],
# ]

# def l(x):
#     return len(x)
# s = Solver()
# x = 'abc'
# s.add( len(x)  < 3  )
# # 也可以是 s.add(eval('l(x) < 3'))

# # P_A = [
# #     [1,'C',x,x==1],
# #     [1,'D',y,y==1],
# #     [2,'C',x,x!=1],
# #     [2,'D',y,y!=1],
# # ]
# #s.add(_)
# print(s.check())

# t1 = '[1,2,3,4]'
# t2 = eval(t1)
# print(t2[0])

# p3_0 = Int('p3_0')