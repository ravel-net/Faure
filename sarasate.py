from z3 import *
import re

"SELECT a,b FROM T WHERE equal(C,'2') AND not_equal(a,b);"

"SELECT * FROM T1 JOIN T2;"
def cjoin(table1_info,table2_info,where):
    result = ''
    #t_result = 't_result'

    table1_info = table1_info.lower()

    table2_info = table2_info.lower()

    table1 =  table1_info.split('(')[0].strip()
    table2 =  table2_info.split('(')[0].strip()

    t_result = f"output"
    #t_result = f"{table1}_join_{table2}"
    p2 = re.compile(r'[(](.*?)[)]', re.S)
    t1_attr =  re.findall(p2, table1_info)[0].strip().split(',')
    t1_attr = [v.strip() for v in t1_attr ]
    t2_attr =  re.findall(p2, table2_info)[0].strip().split(',')
    t2_attr = [v.strip() for v in t2_attr ]

    common_attr=[val for val in t1_attr if val in t2_attr and val != 'cond']
    union_attr = list(set(t1_attr).union(set(t2_attr)))
    result += "Step1: Create Data Content\n"
    result += f"DROP TABLE IF EXISTS {t_result};\n"

    slt_attr = ""

    for a in t1_attr:
        if a not in common_attr and a != "cond":
            slt_attr += f" {table1}.{a}, "
    
    for a in t2_attr:
        if a not in common_attr and a != "cond":
            slt_attr += f"{table2}.{a},"

    for a in common_attr:
        slt_attr += f"{table1}.{a}, {table2}.{a} AS {table2}_{a},"

    if "cond" in t1_attr and "cond" in t2_attr:
        slt_attr += f"array_cat({table1}.cond, {table2}.cond) AS cond,"
        #slt_attr += f" {table1}.cond AS cond, {table2}.cond AS {table2}_cond,"
    elif "cond" in t1_attr:
        slt_attr += f" {table1}.cond AS cond,"
    elif "cond" in t2_attr:
        slt_attr += f" {table2}.cond AS {table2}_cond,"

    slt_attr = slt_attr[:-1]

    join_cond = ""

    for a in common_attr:
        join_cond += f" equal({table1}.{a}, {table2}.{a}) AND"
    join_cond = join_cond[:-3]

    
    if where != '':
        where_cond = ''
        if f"{table1}." or f"{table2}." in where:
            where.replace(f"{table1}.",'').replace(f"{table2}.",'')
        where_1 = where[:]
        where_2 = where[:]
        for c in common_attr:
            if c in where_1:
                where_1 = where_1.replace(c, f"{table1}.{c}")
                where_2 = where_2.replace(c, f"{table2}.{c}")
        #where_cond = f"({where_1}) and ({where_2})"   
        where_cond = f"{where_1}"     
        result += f"CREATE UNLOGGED TABLE {t_result} AS SELECT {slt_attr} FROM {table1} INNER JOIN {table2} on {join_cond} WHERE {where_cond}; \n"
    else:
        result += f"CREATE UNLOGGED TABLE {t_result} AS SELECT {slt_attr} FROM {table1} INNER JOIN {table2} on {join_cond}; \n"
    
    #result += f"SELECT * FROM {t_result};\n"
    result +="\n#"

    result +=  "Step2: Update Conditions\n"

    #result += f"UPDATE {t_result} SET cond =  array_cat(cond, {table2}_cond);\n"
    result += "2.1: Insert Join Conditions\n"
    for attr in common_attr:
        #result += f"UPDATE {t_result} SET cond = array_append(cond, {attr} || ' == ' || {table2}_{attr})  WHERE  (is_var({t_result}.{attr}) OR is_var({t_result}.{table2}_{attr}) );"
        result += f"UPDATE {t_result} SET cond = array_append(cond, {attr} || ' == ' || {table2}_{attr});\n"
    join_attr = ""

    result += "2.2: Projection and drop duplicated attributes\n"
    for attr in common_attr:

        result += f"UPDATE {t_result} SET {attr} = {table2}_{attr} WHERE not is_var({attr});\n"


    q_dropcol = ''
    for attr in common_attr: 
        q_dropcol += f"DROP COLUMN {table2}_{attr},"
    
    q_dropcol = q_dropcol[:-1]

    result += f"ALTER TABLE {t_result} {q_dropcol}; \n"
    #ALTER TABLE t_result DROP COLUMN dest, DROP COLUMN path;

    return result


def get_sql(query):
    #print("INPUT: " + query + "\n")
    #t_result = 't_result'
    if 'WHERE' in query:
        qlist = query.split('WHERE')
        query = qlist[0].lower() + ' where ' + qlist[1]
    elif 'where' in query:
        qlist = query.split('where')
        query = qlist[0].lower() + ' where ' + qlist[1]
    else: query = query.lower()    
    #select = re.split("select|from",query)
    p1 = re.compile(r'select(.*?)from', re.S) 
    select =  re.findall(p1, query)[0].strip()

    if 'from' in query:
        if 'where' in query:
            p2 = re.compile(r'from(.*?)where', re.S) 
        else: p2 = re.compile(r'from(.*?);', re.S) 
    table_name =  re.findall(p2, query)[0].strip()

    if 'where' in query:
        p3 = re.compile(r'where(.*?);', re.S) 
        where =  re.findall(p3, query)[0].strip()
        # where = where.upper()
    else:
        where = None

    query_list = re.split("select|from|join|where",query)

    if 'join' in query and 'join' in table_name:
        #print('JOIN CASE')
        table1 = table_name.split('join')[0].strip()
        table2 = table_name.split('join')[1].strip()

        table1_info = table1.lower()
        table2_info = table2.lower()
    
        table1_name =  table1_info.split('(')[0].strip()
        table2_name =  table2_info.split('(')[0].strip()
        #t_result = f"{table1_name}_join_{table2_name}"
        t_result = f"output"
        result = ""
        #result = f"Optional: DROP TABLE IF EXISTS {t_result}; \n\n"

        if where == None:
            result += cjoin(table1, table2,'')
        else:
            result += cjoin(table1,table2,where)
            #result += f"SELECT * FROM cjoin('{table1}', '{table2}');"
            # result += f"CREATE TABLE {t_result}_temp AS SELECT * from {t_result} where {where};"
            # result += f"DROP TABLE IF EXISTS {t_result};"
            # result += f"ALTER TABLE {t_result}_temp RENAME TO {t_result};"
    if 'join' not in query:
        #t_result = f"{table_name}_o"
        t_result = f"output"
        result = ""
        
        result += "Step1: Create data content\n"
        result += f"DROP TABLE IF EXISTS {t_result}; \n"
 
        q1 = f"CREATE UNLOGGED TABLE {t_result} AS {query} \n"
        result+=q1
        if where == None:
            #result = query
            return result
        
        #result += f"SELECT * FROM {t_result};\n"
        result +="\n#"

        result +=  "Step2: Update Conditions\n"

    if where != None:

        if "and"  in where: 
            where_list = where.split("and")
            #plpy.info(where_list[0].strip())
        else: 
            where_list = []
            where_list.append(where.strip())

        ##### c may contain '(OR)'

        for disj in where_list:
            has_or = False
            
            if 'or' in disj:
                if 'and' not in query:
                    disj = disj.strip()
                    c_orlist = disj.split('or')
                else:
                    disj = disj.strip()[1:-1].strip()
                    c_orlist = disj.split('or')
                has_or = True
            
            else:   
                c = disj.strip()

            if has_or:
                or_exp = ''
                l_list = []
                r_list = []
                for c in c_orlist:
                    p1 = re.compile(r'[(](.*?)[,]', re.S) 
                    left =  re.findall(p1, c)[0].strip()

                    left_is_attr = False

                    if "'" in left:
                        left = left # cons

                    else:  # attr
                        left = left.replace(table_name, t_result)
                        left_is_attr = True
                        if '.' in left:
                            left = left.split('.')[1]
                    # 2nd arg
                    right_is_attr = False
                    p2 = re.compile(r'[,](.*?)[)]', re.S) 
                    right =  re.findall(p2, c)[0].strip()

                    if table_name in right:
                        right = right.replace(table_name, t_result)
                        right_is_attr = True
                        if '.' in right:
                            right = right.split('.')[1]

                    elif "'" in right:
                        right = right # cons

                    if 'not_equal' in c:
                        or_exp += f"{left} || ' != ' || { right } || ',' ||"
                    elif 'equal' in c:
                        or_exp += f"{left} || ' == ' || { right } || ',' ||"
                    elif 'greater' in c:
                        or_exp += f"{left} || ' > ' || { right } || ',' ||"
                    elif 'less' in c:
                        or_exp += f"{left} || ' < ' || { right } || ',' ||"
                    elif 'geq' in c:
                        or_exp += f"{left} || ' >= ' || { right } || ',' ||"
                    elif 'leq' in c:
                        or_exp += f"{left} || ' <= ' || { right } || ',' ||"

                    left = left.replace("'","")
                    right = right.replace("'","")
                    l_list.append(left)
                    r_list.append(right)
                or_exp = or_exp[:-9]
                #or_exp += ")"
                for idx in range(len(l_list)):
                    
                    #result += f"UPDATE {t_result} SET cond = array_append(cond, {or_exp})  WHERE is_var({t_result}.{l_list[idx]}) Or is_var({t_result}.{r_list[idx]}); \n"

                    if "'" in r_list[idx] or "'" in l_list[idx]:
                        q = f"UPDATE {t_result} SET cond = array_append(cond, 'Or(' || {or_exp} || ')' ) ; \n"

                    else: 
                        q = ''
                    if q not in result:
                        result += q
            
            elif not has_or:

                # 1st arg
                p1 = re.compile(r'[(](.*?)[,]', re.S) 
                left =  re.findall(p1, c)[0].strip()

                left_is_attr = False

                if "'" in left:
                    left = left # cons

                else:  # attr
                    left = left.replace(table_name, t_result)
                    left_is_attr = True
                    if '.' in left:
                        left = left.split('.')[1]
                # 2nd arg
                right_is_attr = False
                p2 = re.compile(r'[,](.*?)[)]', re.S) 
                right =  re.findall(p2, c)[0].strip()

                if table_name in right:
                    right = right.replace(table_name, t_result)
                    right_is_attr = True
                    if '.' in right:
                        right = right.split('.')[1]

                elif "'" in right:
                    right = right # cons

                #result += "Insert SELECT conditions:\n"

                if 'not_equal' in c:

                    if right_is_attr or left_is_attr:
                        q = f"UPDATE {t_result} SET cond = array_append(cond, {left} ||' != '|| {right}); \n"
                    else:
                        q = ''
                    result += q

                elif 'equal' in c:

                    if right_is_attr or left_is_attr:
                        q = f"UPDATE {t_result} SET cond = array_append(cond, {left} ||' == '|| {right}) ;\n"
                    else:
                        q = ''
                    result += q

                elif 'greater' in c:

                    if right_is_attr or left_is_attr:
                        q = f"UPDATE {t_result} SET cond = array_append(cond, {left} ||' > '|| {right}) ;\n"
                    else:
                        q = ''
                    result += q

                elif 'less' in c:

                    if right_is_attr or left_is_attr:
                        q = f"UPDATE {t_result} SET cond = array_append(cond, {left} ||' < '|| {right});\n"

                    else:
                        q = ''
                    result += q

                elif 'geq' in c:

                    if right_is_attr or left_is_attr:
                        q = f"UPDATE {t_result} SET cond = array_append(cond, {left} ||' >= '|| {right}) ;\n"
                    else:
                        q = ''
                    result += q

                elif 'leq' in c:

                    if right_is_attr or left_is_attr:
                        q = f"UPDATE {t_result} SET cond = array_append(cond, {left} ||' <= '|| {right});\n"
                    else:
                        q = ''
                    result += q

    #result += f"SELECT * FROM {t_result};\n"
    result +="\n#"
    result +=  "Step3: Normalization\n"

    q_contra = f"DELETE FROM {t_result} WHERE is_contradiction({t_result}.cond);\n"

    q_tauto = f"UPDATE {t_result} SET cond = '{{}}' WHERE is_tauto({t_result}.cond);\n"

    result += q_contra + q_tauto

    q_rm = f"UPDATE {t_result} SET cond = remove_redundant(cond) where has_redundant(cond);\n"
    result += q_rm

    # q_projection = f"SELECT {select} from {t_result};\n"
    # result += q_projection



    return result

user_input = ''

while user_input != 'q':
    try:
        user_input = input("Please input ctable SQL query('q' quit)： \n")

        # fix bug(when fisrt time input is 'q')
        if user_input == 'q':
            break
        
        r = get_sql(user_input)
        relist = r.split('#')

        print(relist[0])
        input("Press Enter to continue...")
        print()
        print(relist[1])
        input("Press Enter to continue...")
        print()
        print(relist[2])
        input("Press Enter to continue...")
        print()
    except:
        print("ERROR: Illegal Input")


#PART1:
#SELECT * FROM Policy1(DEST,PATH,COND) JOIN Policy2(DEST,PATH, FLAG, COND);
#SELECT * FROM Policy1(DEST,PATH,COND) JOIN Policy2(DEST,PATH, FLAG, COND) WHERE not_equal(path, '[ADC]');


#Part2: 
#SELECT * FROM Policy1(DEST,PATH,COND) JOIN Routing1(DEST,PATH);
#SELECT * FROM POlicy1(DEST,PATH,COND) JOIN Routing2(DEST,PATH);

#Part3:
#SELECT * FROM Policy3(DEST,PATH,COND) JOIN Policy4(DEST,NH, FLAG, COND);


# query = "SELECT * FROM P1(DEST,PATH,COND) JOIN P3(DEST,PATH, FLAG, COND) WHERE equal(flag,'1');"
# query = "SELECT * FROM P1(DEST,PATH,COND) JOIN P3(DEST,PATH, FLAG, COND);"
# query = "SELECT * FROM P1(DEST,PATH,COND) JOIN P3(DEST,PATH, FLAG, COND) WHERE equal(dest,'5.6.7.8');"
# query = "select * from policy2 where equal(flag,'1');"
# query = "SELECT * FROM Policy1(DEST,PATH,COND) JOIN Policy2(DEST,PATH, FLAG, COND) WHERE not_equal(path, '[ADC]');"
# query = "SELECT * FROM Policy1(DEST,PATH,COND) JOIN Routing1(DEST,PATH);"
# query = "SELECT * FROM Policy3(DEST,PATH,COND) JOIN Policy4(DEST,NH, FLAG, COND);"
# print(query)
# re = get_sql(query)
# relist = re.split('#')

# print(relist[0])
# input("Press Enter to continue...")
# print()
# print(relist[1])
# input("Press Enter to continue...")
# print()
# print(relist[2])


#print(get_sql("SELECT * FROM t2 WHERE equal(d,'1');"))
    
#print(get_sql("SELECT * FROM T3 WHERE equal(c,'1');"))

# print(get_sql("SELECT * FROM T1 JOIN T2;"))

#print(get_sql("SELECT * FROM T5 WHERE  equal(a,'1')  OR  equal(a,'2')  ;"))
#print(get_sql("SELECT * FROM T4 WHERE equal(c,'1');"))

# query_user = input("Please input ctable SQL query：")
# print(type(query_user)) 
 