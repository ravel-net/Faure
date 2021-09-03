----------------------------------------------
-- BGP simulation
----------------------------------------------

/* Candidate routing table for BGP simulation -- from RIB files
 * dest: IP prefix
 * path: AS path
 */
DROP TABLE IF EXISTS routes CASCADE;
CREATE UNLOGGED TABLE routes (
       fid SERIAL PRIMARY key,
       dest TEXT,
       path TEXT
);

/* Routes Updates -- from UPDATE files
 * dest: IP prefix
 * operation: A (Annoucement), W (Withdrawal)
 * path: AS path
 * len_path: length of path
 */
DROP TABLE IF EXISTS routes_delta CASCADE;
CREATE UNLOGGED TABLE routes_delta (
       fid SERIAL PRIMARY key,
       dest TEXT,
       operation TEXT,
       path TEXT,
       len_path integer
);

CREATE EXTENSION IF NOT EXISTS plpython3u;

CREATE OR REPLACE FUNCTION is_var(a text)
    RETURNS boolean
AS $$

    SELECT
    CASE WHEN a ~ '^[a-zA-Z]'THEN True
    --CASE WHEN a LIKE 'var_%' THEN True
    ELSE False
    END;

$$ LANGUAGE SQL;

--DROP FUNCTION If EXISTS equal(text, text) CASCADE;

CREATE OR REPLACE FUNCTION equal(col1 TEXT, col2 TEXT)
returns boolean as
$$
select 
CASE WHEN col1 = col2 THEN True

    WHEN is_var(col1) or is_var(col2) THEN True

    ELSE False
    END
;
$$LANGUAGE SQL;


CREATE OR REPLACE FUNCTION not_equal(col1 TEXT, col2 TEXT)
returns boolean as
$$
select 
CASE 

    WHEN is_var(col1) or is_var(col2) THEN True
    WHEN col1 != col2 and not (is_var(col1) or is_var(col2)) THEN True

    ELSE False
    END
;

$$LANGUAGE SQL;

CREATE OR REPLACE FUNCTION geq(col1 TEXT, col2 TEXT)
returns boolean as
$$
select 
CASE 

    WHEN is_var(col1) or is_var(col2) THEN True
    WHEN (col1 > col2 or col1 = col2) and not (is_var(col1) or is_var(col2)) THEN True

    ELSE False
    END
;

$$LANGUAGE SQL;

CREATE OR REPLACE FUNCTION leq(col1 TEXT, col2 TEXT)
returns boolean as
$$
select 
CASE 

    WHEN is_var(col1) or is_var(col2) THEN True
    WHEN (col1 < col2 or col1 = col2) and not (is_var(col1) or is_var(col2)) THEN True

    ELSE False
    END
;

$$LANGUAGE SQL;

CREATE OR REPLACE FUNCTION greater(col1 TEXT, col2 TEXT)
returns boolean as
$$
select 
CASE 

    WHEN is_var(col1) or is_var(col2) THEN True
    WHEN col1 > col2 and not (is_var(col1) or is_var(col2)) THEN True

    ELSE False
    END
;

$$LANGUAGE SQL;

CREATE OR REPLACE FUNCTION less(col1 TEXT, col2 TEXT)
returns boolean as
$$
select 
CASE 

    WHEN is_var(col1) or is_var(col2) THEN True
    WHEN col1 < col2 and not (is_var(col1) or is_var(col2)) THEN True

    ELSE False
    END
;

$$LANGUAGE SQL;

DROP FUNCTION IF EXISTS is_contradiction;
CREATE OR REPLACE FUNCTION is_contradiction(cond TEXT [])
    RETURNS boolean
AS $$
    import z3
    from z3 import And, Not, Or, Implies    
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

            if c_list[0] in vars: # if variable in vars that means this variable is Int variable and need to further set Int value for it
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
        return True
    else:
        return False
$$ LANGUAGE plpython3u;


DROP FUNCTION IF EXISTS is_tauto;
CREATE OR REPLACE FUNCTION is_tauto(cond TEXT [] )
    RETURNS boolean
AS $$
    import z3
    from z3 import And, Not, Or, Implies
    solver = z3.Solver()
    
    if len(cond) == 0:
        return True
    
    for c in cond:


        if 'Or' not in c:
            c_list = c.split(' ')
            
            if c_list[0][0].isalpha():
                op1 = f"z3.String('{c_list[0]}')"
            else: 
                op1 = f"z3.StringVal('{c_list[0]}')"
            
            if c_list[2][0].isalpha():
                op2 = f"z3.String('{c_list[2]}')"
            else:
                op2 = f"z3.StringVal('{c_list[2]}')"
            
            operator = c_list[1]

            #expr = f"{c_list[0]} {operator} z3.StringVal('{c_list[2]}')"
            expr = f"Not({op1} {operator} {op2})"
            #plpy.info(expr)
            solver.push()
            solver.add(eval(expr))
            re = solver.check()
            solver.pop()
            if str(re) == 'sat':
                return False
            else: #-- tautology to be removed
                pass
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
                expr = f"Not({op1} {c_list[1]} {op2})"
                or_input += expr + ','
            or_input = or_input[:-1] + ')'
            
            solver.push()
            solver.add(eval(or_input))
            re = solver.check()
            solver.pop()
            if str(re) == 'sat':
                return False
            else: #-- tautology to be removed
                pass
    return True
$$ LANGUAGE plpython3u;


DROP FUNCTION IF EXISTS has_redundant;
CREATE OR REPLACE FUNCTION has_redundant(cond TEXT [] )
    RETURNS boolean
AS $$
    import z3
    from z3 import And, Not, Or, Implies
    s = z3.Solver()
    
    if len(cond) == 0:
        return True
    
    for idx1 in range(len(cond)):
        if 'Or' not in cond[idx1]:

            c1_list = cond[idx1].split(' ')
            
            if c1_list[0][0].isalpha():
                op11 = f"z3.String('{c1_list[0]}')"
            else: 
                op11 = f"z3.StringVal('{c1_list[0]}')"
        
            if c1_list[2][0].isalpha():
                op12 = f"z3.String('{c1_list[2]}')"
            else:
                op12 = f"z3.StringVal('{c1_list[2]}')"
            
            operator1 = c1_list[1]

            expr1 = f"{op11} {operator1} {op12}"

        else: 
            cond_idx1 = cond[idx1].strip().replace('Or','')[1:-1]

            or_input = "Or("
            or_list =  cond_idx1.split(',')
            for single_cond in or_list:
                c_list = single_cond.strip(). split(' ')
            
                if c_list[0][0].isalpha():
                    op11 = f"z3.String('{c_list[0]}')"
                else: 
                    op11 = f"z3.StringVal('{c_list[0]}')"

                if c_list[2][0].isalpha():
                    op12 = f"z3.String('{c_list[2]}')"
                else:
                    op12 = f"z3.StringVal('{c_list[2]}')"
                    
                operator1 = c_list[1]
                expr = f"{op11} {operator1} {op12}"
                or_input += expr + ','
            expr1 = or_input[:-1] + ')'
        for idx2 in range(idx1,len(cond)):
            if idx2 == idx1: continue

            if cond[idx1] == cond[idx2]:
                return True
            
            if 'Or' not in cond[idx2]:
                #plpy.info(str(cond[idx1]) + ' ' + str(cond[idx2]))
                c2_list = cond[idx2].split(' ')
                
                if c2_list[0][0].isalpha():
                    op21 = f"z3.String('{c2_list[0]}')"
                else: 
                    op21 = f"z3.StringVal('{c2_list[0]}')"

                if c2_list[2][0].isalpha():
                    op22 = f"z3.String('{c2_list[2]}')"
                else:
                    op22 = f"z3.StringVal('{c2_list[2]}')"
                
                operator2 = c2_list[1]

                expr2 = f"{op21} {operator2} {op22}"            

            else: #-- 'Or' in cond[idx2]
                
                cond_idx2 = cond[idx2].strip().replace('Or','')[1:-1]

                or_input = "Or("
                or_list =  cond_idx2.split(',')


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
                        
                    expr = f"{op1} {c_list[1]} {op2}"
                    or_input += expr + ','
                expr1 = or_input[:-1] + ')'

            G = Implies(eval(expr1), eval(expr2))
            s.push()
            s.add(Not(G))
            re = str(s.check())
            s.pop()
            if str(re) == 'unsat':
                #plpy.info(f"Implies(eval({expr1}), eval({expr2})) has redundancy!!")
                return True

            G = Implies(eval(expr2), eval(expr1))
            s.push()
            s.add(Not(G))
            re = str(s.check())
            s.pop()
            if str(re) == 'unsat':
                #plpy.info(f"Implies(eval({expr2}), eval({expr1})) has redundancy!!")
                return True
    return False
$$ LANGUAGE plpython3u;


DROP FUNCTION IF EXISTS remove_redundant;
CREATE OR REPLACE FUNCTION remove_redundant(cond TEXT [] )
    RETURNS TEXT[]
AS $$
    global cond
    result = cond[:]
    
    drop_idx = {}
    dp_arr = []
    for i in range(len(cond)):
        drop_idx[i] = []
    #plpy.info(drop_idx)
    import z3
    from z3 import And, Not, Or, Implies
    s = z3.Solver()
    
    if len(cond) == 0:
        return result
    
    
    for idx1 in range(len(cond)):
        if 'Or' not in cond[idx1]:

            c1_list = cond[idx1].split(' ')
            
            if c1_list[0][0].isalpha():
                op11 = f"z3.String('{c1_list[0]}')"
            else: 
                op11 = f"z3.StringVal('{c1_list[0]}')"
        
            if c1_list[2][0].isalpha():
                op12 = f"z3.String('{c1_list[2]}')"
            else:
                op12 = f"z3.StringVal('{c1_list[2]}')"
            
            operator1 = c1_list[1]

            expr1 = f"{op11} {operator1} {op12}"

        else: 
            cond_idx1 = cond[idx1].strip().replace('Or','')[1:-1]

            or_input = "Or("
            or_list =  cond_idx1.split(',')
            for single_cond in or_list:
                c_list = single_cond.strip(). split(' ')
            
                if c_list[0][0].isalpha():
                    op11 = f"z3.String('{c_list[0]}')"
                else: 
                    op11 = f"z3.StringVal('{c_list[0]}')"

                if c_list[2][0].isalpha():
                    op12 = f"z3.String('{c_list[2]}')"
                else:
                    op12 = f"z3.StringVal('{c_list[2]}')"
                    
                operator1 = c_list[1]
                expr = f"{op11} {operator1} {op12}"
                or_input += expr + ','
            expr1 = or_input[:-1] + ')'
        for idx2 in range(idx1,len(cond)):
            if idx2 == idx1: continue

            
            if 'Or' not in cond[idx2]:
                #plpy.info(str(cond[idx1]) + ' ' + str(cond[idx2]))
                c2_list = cond[idx2].split(' ')
                
                if c2_list[0][0].isalpha():
                    op21 = f"z3.String('{c2_list[0]}')"
                else: 
                    op21 = f"z3.StringVal('{c2_list[0]}')"

                if c2_list[2][0].isalpha():
                    op22 = f"z3.String('{c2_list[2]}')"
                else:
                    op22 = f"z3.StringVal('{c2_list[2]}')"
                
                operator2 = c2_list[1]

                expr2 = f"{op21} {operator2} {op22}"            

            else: #-- 'Or' in cond[idx2]
                
                cond_idx2 = cond[idx2].strip().replace('Or','')[1:-1]

                or_input = "Or("
                or_list =  cond_idx2.split(',')


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
                        
                    expr = f"{op1} {c_list[1]} {op2}"
                    or_input += expr + ','
                expr1 = or_input[:-1] + ')'

            G = Implies(eval(expr1), eval(expr2))
            s.push()
            s.add(Not(G))
            re = str(s.check())
            s.pop()
            if str(re) == 'unsat':
                #plpy.info(f"Implies(eval({expr1}), eval({expr2})) has redundancy!!")
                drop_idx[idx1].append(idx2)


            G = Implies(eval(expr2), eval(expr1))
            s.push()
            s.add(Not(G))
            re = str(s.check())
            s.pop()
            if str(re) == 'unsat':
                #plpy.info(f"Implies(eval({expr2}), eval({expr1})) has redundancy!!")
                drop_idx[idx2].append(idx1)


    drop_result = {}
    for i in range(len(cond)):
        drop_result[i] = []



    for c1 in list(drop_idx):

        for c2 in drop_idx[c1]:
            if c2 == c1:
                continue
            drop_idx[c1]+=(drop_idx[c2])
            drop_idx[c1] = list(set(drop_idx[c1]))
            drop_idx[c2] = []

            #plpy.info(drop_idx)
            if c1 in drop_idx[c1]:

                drop_idx[c1].remove(c1)

    

    for c1 in list(drop_idx):
        for c2 in drop_idx[c1]:        
            dp_arr.append(c2)
    #plpy.info(drop_idx)
    #plpy.info(dp_arr)
    
    result = [result[i] for i in range(0, len(result), 1) if i not in dp_arr]
    return result
$$ LANGUAGE plpython3u;

-- l function: returns the length of path
DROP FUNCTION IF EXISTS l;
CREATE OR REPLACE FUNCTION l(path TEXT )
    RETURNS smallint
AS $$
    global path

    if path == '_':
        return 0

    return len(path.split(' '))
$$ LANGUAGE plpython3u;

DROP FUNCTION IF EXISTS str_to_int;
CREATE OR REPLACE FUNCTION str_to_int(var smallint )
    RETURNS TEXT
AS $$

    return int(var)
$$ LANGUAGE plpython3u;

