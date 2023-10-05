
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
                expr2 = or_input[:-1] + ')'

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
                expr2 = or_input[:-1] + ')'

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



--DROP FUNCTION IF EXISTS simplify;
DROP FUNCTION IF EXISTS cjoin(TEXT,TEXT,TEXT);
DROP FUNCTION IF EXISTS cjoin(TEXT,TEXT);
CREATE OR REPLACE FUNCTION cjoin(table1 TEXT, table2 TEXT)
    RETURNS TEXT
AS $$
    #-- STEP1: Create initial table
    global table1
    global table2
    table1 = table1.lower()
    table2 = table2.lower()
    t_result = 't_result'

    query_cond = "SELECT column_name FROM information_schema.columns WHERE table_name = '" + table1 + "';"
    rv_cond = plpy.execute(query_cond);
    #plpy.info(rv_cond)
    
    t1_attr = []
    for i in range(rv_cond.nrows()):
        t1_attr.append(rv_cond[i]['column_name']  )
    #plpy.info(t1_attr)

    query_cond = "SELECT column_name FROM information_schema.columns WHERE table_name = '" + table2 + "';"
    rv_cond = plpy.execute(query_cond);
    #plpy.info(rv_cond)
    
    t2_attr = []
    for i in range(rv_cond.nrows()):
        t2_attr.append(rv_cond[i]['column_name']  )
    #plpy.info(t2_attr)

    common_attr=[val for val in t1_attr if val in t2_attr and val != 'cond']
    union_attr = list(set(t1_attr).union(set(t2_attr)))

    #plpy.info(common_attr)
    
    q = f"DROP TABLE IF EXISTS t_result;"
    plpy.execute(q)
    
    slt_attr = ""

    for a in t1_attr:
        if a not in common_attr and a != "cond":
            slt_attr += f" {table1}.{a}, "
    
    for a in t2_attr:
        if a not in common_attr and a != "cond":
            slt_attr += f"{table2}.{a},"

    for a in common_attr:
        slt_attr += f"{table1}.{a} AS {table1}_{a}, {table2}.{a} AS {table2}_{a},"

    if "cond" in t1_attr and "cond" in t2_attr:
        slt_attr += f" {table1}.cond AS {table1}_cond, {table2}.cond AS {table2}_cond,"
    elif "cond" in t1_attr:
        slt_attr += f" {table1}.cond AS {table1}_cond,"
    elif "cond" in t2_attr:
        slt_attr += f" {table2}.cond AS {table2}_cond,"

    slt_attr = slt_attr[:-1]

    #plpy.info(slt_attr)

    join_cond = ""
    #plpy.info(common_attr)
    for a in common_attr:
        join_cond += f" equal({table1}.{a}, {table2}.{a}) AND"
    join_cond = join_cond[:-3]
   
    q = f"CREATE UNLOGGED TABLE {t_result} AS SELECT {slt_attr} FROM {table1} INNER JOIN {table2} on {join_cond}; "
    #plpy.info(q)
    plpy.execute(q)

    if "cond" in t1_attr and "cond" in t2_attr:
        pass
    elif "cond" in t1_attr:
        q1 = f"ALTER TABLE {t_result} ADD COLUMN {table2}_cond text [];"
        q2 = f"UPDATE {t_result} SET {table2}_cond = '{{}}';"
        plpy.execute(q1)
        plpy.execute(q2)
    elif "cond" in t2_attr:
        q1 = f"ALTER TABLE {t_result} ADD COLUMN {table1}_cond text [];"
        q2 = f"UPDATE {t_result} SET {table1}_cond = '{{}}';"
        plpy.execute(q1)
        plpy.execute(q2)


    #--STEP2: Update and Simplify
    q = f"UPDATE {t_result} SET {table1}_cond =  array_cat({table1}_cond, {table2}_cond);" 
    #plpy.info(q)
    plpy.execute(q)

    for attr in common_attr:

        q = f"UPDATE {t_result} SET {table1}_cond = array_append({table1}_cond, {table1}_{attr} || ' == ' || {table2}_{attr})  WHERE  (is_var({t_result}.{table1}_{attr}) OR is_var({t_result}.{table2}_{attr}) );"
        #plpy.info(q)
        plpy.execute(q)
    #-- UPDATE t1_join_t2 SET cond = array_append(cond, c || ' == ' || c1)  WHERE  (is_var(t1_join_t2.c) OR is_var(t1_join_t2.c1) );
    #-- UPDATE t1_join_t2 SET cond = array_append(cond, b || ' == ' || b1)  WHERE  (is_var(t1_join_t2.b) OR is_var(t1_join_t2.b1) );

    q = f"DELETE FROM {t_result} WHERE is_contradiction({t_result}.{table1}_cond);"
    #plpy.info(q)
    #plpy.execute(q)

    q = f"UPDATE {t_result} SET {table1}_cond = '{{}}' WHERE is_tauto({t_result}.{table1}_cond);"
    #plpy.info(q)
    #plpy.execute(q)

    #--STEP3: Projection 
    
    join_attr = ""
    for attr in common_attr:
        q_com = f"CASE WHEN is_var({table1}_{attr}) THEN {table1}_{attr} ELSE {table2}_{attr} END AS {attr},"
        join_attr += q_com

    t1_a = ""
    for a in t1_attr:
        if a not in common_attr and a != "cond":
            t1_a += f"{a},"

    t2_a = ""
    for a in t2_attr:
        if a not in common_attr and a != "cond":
            t2_a += f"{a},"
    #plpy.info(other_attr)
    #plpy.info(join_attr)

    attr_str = t1_a + join_attr + t2_a + f"{table1}_cond AS cond"
    #plpy.info(attr_str)

    q = f"DROP TABLE IF EXISTS {t_result}_temp;"
    plpy.execute(q)

    #if where_cond == '':
    q = f"CREATE UNLOGGED TABLE {t_result}_temp AS SELECT {attr_str} FROM {t_result};"
    #else:
        #q = q = f"""CREATE UNLOGGED TABLE {t_result}_temp AS SELECT {attr_str} FROM {t_result} where {where_cond};"""
    plpy.execute(q)

    q = f"DROP TABLE IF EXISTS {t_result};"
    plpy.execute(q)

    q = f"ALTER TABLE {t_result}_temp RENAME TO {t_result};"
    plpy.execute(q)

    return 'Done'
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


DROP FUNCTION IF EXISTS set_path_val;
CREATE OR REPLACE FUNCTION set_path_val(path_name TEXT, conds TEXT [])
    RETURNS TEXT
AS $$
    if path_name == '_':
        return '_'
        
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
$$ LANGUAGE plpython3u;