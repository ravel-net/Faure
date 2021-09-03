import z3
from z3 import And, Not, Or, Implies 

def is_contradiction(cond):
   
    solver = z3.Solver()

    if len(cond) == 0:
        return False

    vars = set() # save Int compared variables for shortest path policy
    for c in cond:

        if '<=' in c:
            conds = c.split('<=')  # l(x3) <= x4
            
            var1 = conds[0].strip()
            var2 = conds[1].strip()
            
            if var1[0].isalpha():
                op1 = "z3.Int('{}')".format(var1)
                vars.add(var1)
            else:
                op1 = "z3.IntVal({})".format(int(var1))

            if var2[0].isalpha():
                op2 = "z3.Int('{}')".format(var2)
                vars.add(var2)
            else:
                op2 = "z3.IntVal({})".format(int(var2))

            expr = "{} <= {}".format(op1, op2)
            #print(expr)
            solver.add(eval(expr))
            continue

        # nopath means no path to dest
        if 'nopath' in c:
            return True
            
        if 'Or' not in c:
            #c_list = c.strip().split(' ')
            c = c.strip()

            first_space = c.find(' ')
            second_space = c.find(' ', first_space + 1)

            c_list = [c[:first_space].strip(), c[first_space + 1: second_space].strip(), c[second_space + 1:].strip()]

            if c_list[0] in vars: # if variable in vars that means this variable is Int variable and need to further set value for it
                solver.add(z3.Int(c_list[0]) == z3.IntVal(int(c_list[2])))
                continue
            elif c_list[0][0].isalpha():
                op1 = f"z3.String('{c_list[0]}')"
            else: 
                op1 = f"z3.StringVal('{c_list[0]}')"

            if c_list[2][0].isalpha():
                op2 = f"z3.String('{c_list[2]}')"
            else:
                op2 = f"z3.StringVal('{c_list[2]}')"
                
            #expr = f"{c_list[0]} {c_list[1]} z3.StringVal('{c_list[2]}')"
            expr = f"{op1} {c_list[1]} {op2}"
            #plpy.info(expr)
            solver.add(eval(expr))
        
        else:  #-- includes Or()
            c = c.strip().replace('Or','').replace('(','').replace(')','').strip()

            or_input = "Or("
            or_list =  c.split(',')
            for single_cond in or_list:
                c_list = single_cond.strip(). split(' ')
            
                if c_list[0][0].isalpha():
                    op1 = f"z3.String('{c_list[0]}')"
                else: 
                    op1 = f"z3.StringVal('{c_list[0]}')"

                if c_list[2][0].isalpha():
                    op2 = f"z3.String('{c_list[2]}')"
                else:
                    op2 = f"z3.StringVal('{c_list[2]}')"
                    
                #expr = f"{c_list[0]} {c_list[1]} z3.StringVal('{c_list[2]}')"
                expr = f"{op1} {c_list[1]} {op2}"
                or_input += expr + ','
    
            or_input = or_input[:-1] + ')'
            #plpy.info(or_input)
            solver.add(eval(or_input))
    re = solver.check()


    if str(re) == 'unsat':
        print('true')
        return True
    else:
        print('flase')
        print(solver.model())
        return False

def list_to_string(list):
    str = " ".join([item for item in list]) 
    print(str)

def set_path(path_name, conds):

    for cond in conds:
        cond = cond.strip()

        first_space = cond.find(' ')
        second_space = cond.find(' ', first_space + 1)

        var1 = cond[:first_space].strip()
        op = cond[first_space + 1: second_space].strip()
        var2 = cond[second_space + 1:].strip()
        
        if path_name == var1 and op == '==':
            return var2
        elif path_name == var2 and op == '==':
            return var1
        else:
            continue
    
    return ''
        

# list = ["l(x579) <= x580","x579 == 6939 9583","x580 == 2","l(x579) == 2", "4 <= x580"]

# is_contradiction(list)

# list = ['John', 'Bran', 'Grammy', 'Norah']
# list_to_string(list)

path_name = 'x531'
conds = ["l(x531) <= x532","x531 == 1299 9583","x532 == 2","l(x531) == 2"]
print(set_path(path_name, conds))