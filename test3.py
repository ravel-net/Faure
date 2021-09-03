import psycopg2
import re

conn = psycopg2.connect(host="127.0.0.1",user="postgres",password="251314",database="postgres")
cur = conn.cursor()

def pre_processing(query):
    # remove ;
    if ';' in query:
        query = query[:-1]

    query_lower = query.lower()

    # detect the location of where
    where_index = query_lower.find('where')
    where_clause = query[where_index+5:]

    select_clause = query_lower[ :where_index]

    # get the tables
    pattern = re.compile(r'from(.*?)where', re.S)
    from_clause = re.findall(pattern, query_lower)[0].strip()

    '''
    Processing comparison operators
    '''
    defined_where_clause = ""
    where_lists = re.split("and", where_clause)
    for w in where_lists:
        # if 'len' in w, that means this columm's type is integer
        if 'len' in w:
            continue

        if '!=' in w:
            args = w.split('!=')
            left = args[0].strip()
            right = args[1].strip()
            defined_where_clause = defined_where_clause + "not_equal({}, {}) and".format(left, right) 
        elif '<>' in w:
            args = w.split('<>')
            left = args[0].strip()
            right = args[1].strip()
            defined_where_clause = defined_where_clause + "not_equal({}, {}) and ".format(left, right) 
        elif '<=' in w:
            args = w.split('<=')
            left = args[0].strip()
            right = args[1].strip()
            defined_where_clause = defined_where_clause + "leq({}, {}) and ".format(left, right)
        elif '>=' in w:
            args = w.split('>=')
            left = args[0].strip()
            right = args[1].strip()
            defined_where_clause = defined_where_clause + "geq({}, {}) and ".format(left, right)
        elif '<' in w:
            args = w.split('<')
            left = args[0].strip()
            right = args[1].strip()
            defined_where_clause = defined_where_clause + "less({}, {}) and ".format(left, right)
        elif '>' in w:
            args = w.split('>')
            left = args[0].strip()
            right = args[1].strip()
            defined_where_clause = defined_where_clause + "greater({}, {}) and ".format(left, right)
        elif '=' in w:
            args = w.split('=')
            left = args[0].strip()
            right = args[1].strip()
            defined_where_clause = defined_where_clause + "equal({}, {}) and ".format(left, right)

    defined_where_clause = defined_where_clause[:-4]  # remove final 'and'      
    
    return select_clause, from_clause, defined_where_clause, where_lists

def generator(select_clause, from_clause, where_clause, where_lists):
    '''
    The number of tables is greater than 1, it is join operation
    else, it is selection
    '''
    table_list = from_clause.split(',')
    if len(table_list) > 1:

        t1_name = table_list[0].strip()
        t2_name = table_list[1].strip()
        
        if '*' in select_clause:
            '''
            get the attributes of each table
            '''
            cur.execute("select * from {}".format(t1_name))
            t1_attrs = [row[0] for row in cur.description]
            cur.execute("select * from {}".format(t2_name))
            t2_attrs = [row[0] for row in cur.description]
            
            '''
            get common attributes and difference attributes
            '''
            common_attr = set(t1_attrs).intersection(set(t2_attrs)) - set(['condition'])
            union_attr = set(t1_attrs).union(set(t2_attrs)) - set(['condition'])
            diff_attr = union_attr - common_attr

            attr_diff = ""
            attr_equal = ""
            
            for c in common_attr:
                attr_equal += "{}.{}, {}.{} AS {}_{},".format(t1_name, c, t2_name, c, t2_name, c)
                
            for d in diff_attr:
                attr_diff += " {},".format(d)

            attr_diff += "array_cat({}.condition, {}.condition) as condition".format(t1_name, t2_name)

            print("Step1: Create Data Content")
            sql = "create table output as select {} {} FROM {} where ".format(attr_equal, attr_diff, from_clause) + where_clause
            print(sql)

            print("Step2: Update Condition")

            for w in where_lists:
                args = w.strip().split(' ')

                left = args[0].strip()
                if '.' in left:
                    left = left.replace(t1_name + '.', '')

                opr = args[1].strip()

                right = args[2].strip()
                if '.' in right:
                    right = right.replace('.', '_')
                # repalce = with == in order accommodate z3
                if '!=' not in opr and '<=' not in opr and '>=' not in opr and '=' in opr:
                    opr = opr.replace('=', '==')
                
                sql = "update output set condition = array_append(condition, {} || ' {} ' || {});".format(left, opr, right)

            attr_drop = ""

            for c in common_attr:
                sql = "update output set {} = {}_{} where not is_var({})".format(c, t2_name, c, c)
                attr_drop = attr_drop + "drop column {}_{}, ".format(t2_name, c)
                print(sql)

            # remove the spare ,
            attr_drop = attr_drop[:-2]
            sql = "alter table output {};".format(attr_drop)
            print(sql)
        else:
            print("still working")

   
    else:
        print('Step1: Create Data Content')
        sql = 'create table output as '

        sql = sql + select_clause + ' where '+ where_clause + ';'
        print(sql)

        print('Step2: Update Condition')
        for w in where_lists:
            args = w.strip().split(' ')
            left = args[0].strip()
            opr = args[1].strip()
            right = args[2].strip()
            # repalce = with == in order accommodate z3
            if '!=' not in opr and '<=' not in opr and '>=' not in opr and '=' in opr:
                opr = opr.replace('=', '==')
            
            sql = "update output set condition = array_append(condition, {} || ' {} ' || {});".format(left, opr, right)
            print(sql)
    

    print('Step3: Normalization')
    sql = 'delete from output where is_contradiction(condition);'
    print(sql)
    sql = "UPDATE output SET condition = '{}' WHERE is_tauto(condition);"
    print(sql)
    sql = "UPDATE output SET condition = remove_redundant(condition) WHERE has_redundant(condition);"
    print(sql)



def data(select_clause, from_clause, where_clause, where_lists):
    '''
    The number of tables is greater than 1, it is join operation
    else, it is selection
    '''
    table_list = from_clause.split(',')
    if len(table_list) > 1:

        t1_name = table_list[0].strip()
        t2_name = table_list[1].strip()
        
        if '*' in select_clause:
            '''
            get the attributes of each table
            '''
            cur.execute("select * from {}".format(t1_name))
            t1_attrs = [row[0] for row in cur.description]
            cur.execute("select * from {}".format(t2_name))
            t2_attrs = [row[0] for row in cur.description]
            
            '''
            get common attributes and difference attributes
            '''
            common_attr = set(t1_attrs).intersection(set(t2_attrs)) - set(['condition'])
            union_attr = set(t1_attrs).union(set(t2_attrs)) - set(['condition'])
            diff_attr = union_attr - common_attr

            print(common_attr)
            print(diff_attr)

            attr_diff = ""
            attr_equal = ""
            
            for c in common_attr:
                attr_equal += "{}.{}, {}.{} AS {}_{},".format(t1_name, c, t2_name, c, t2_name, c)
                
            for d in diff_attr:
                attr_diff += " {},".format(d)

            attr_diff += "array_cat({}.condition, {}.condition) as condition".format(t1_name, t2_name)

            print("Step1: Create Data Content")
            sql = "create table output as select {} {} FROM {} where ".format(attr_equal, attr_diff, from_clause) + where_clause
            print(sql)

        else:
            print("still working")
   
    else:
        print('Step1: Create Data Content')
        sql = 'create table output as '

        sql = sql + select_clause + ' where '+ where_clause + ';'
        print(sql)


def condition(select_clause, from_clause, where_clause, where_lists):
    '''
    The number of tables is greater than 1, it is join operation
    else, it is selection
    '''
    table_list = from_clause.split(',')
    if len(table_list) > 1:

        t1_name = table_list[0].strip()
        t2_name = table_list[1].strip()
        
        if '*' in select_clause:
            '''
            get the attributes of each table
            '''
            cur.execute("select * from {}".format(t1_name))
            t1_attrs = [row[0] for row in cur.description]
            cur.execute("select * from {}".format(t2_name))
            t2_attrs = [row[0] for row in cur.description]
            
            '''
            get common attributes and difference attributes
            '''
            common_attr = set(t1_attrs).intersection(set(t2_attrs)) - set(['condition'])
            union_attr = set(t1_attrs).union(set(t2_attrs)) - set(['condition'])
            diff_attr = union_attr - common_attr

            print(common_attr)
            print(diff_attr)

            print("Step2: Update Condition")

            for w in where_lists:
                args = w.strip().split(' ')

                left = args[0].strip()
                if '.' in left:
                    left = left.replace(t1_name + '.', '')

                opr = args[1].strip()

                right = args[2].strip()
                if '.' in right:
                    right = right.replace('.', '_')
                # repalce = with == in order accommodate z3
                if '!=' not in opr and '<=' not in opr and '>=' not in opr and '=' in opr:
                    opr = opr.replace('=', '==')
                
                sql = "update output set condition = array_append(condition, {} || ' {} ' || {});".format(left, opr, right)

            attr_drop = ""

            for c in common_attr:
                sql = "update output set {} = {}_{} where not is_var({})".format(c, t2_name, c, c)
                attr_drop = attr_drop + "drop column {}_{}, ".format(t2_name, c)
                print(sql)

            # remove the spare ,
            attr_drop = attr_drop[:-2]
            sql = "alter table output {};".format(attr_drop)
            print(sql)
        else:
            print("still working")

   
    else:

        print('Step2: Update Condition')
        for w in where_lists:
            args = w.strip().split(' ')
            left = args[0].strip()
            opr = args[1].strip()
            right = args[2].strip()
            # repalce = with == in order accommodate z3
            if '!=' not in opr and '<=' not in opr and '>=' not in opr and '=' in opr:
                opr = opr.replace('=', '==')
            
            sql = "update output set condition = array_append(condition, {} || ' {} ' || {});".format(left, opr, right)
            print(sql)


def z3():
    print('Step3: Normalization')
    sql = 'delete from output where is_contradiction(condition);'
    print(sql)
    sql = "UPDATE output SET condition = '{}' WHERE is_tauto(condition);"
    print(sql)
    sql = "UPDATE output SET condition = remove_redundant(condition) WHERE has_redundant(condition);"
    print(sql)

if __name__ == '__main__':
    # query = "select * from policy1 where path != '[ABC]'"
    # query = "select * from policy1, policy2 where policy1.dest = policy2.dest and policy1.path = policy2.path;"
    # query = "select * from bgp_policy, new_candidates where bgp_policy.dest = new_candidates.dest and bgp_policy.path = new_candidates.path and min_len <= len_path;"
    # select_clause, from_clause, defined_where_clause, where_lists = pre_processing(query)
    # generator(select_clause, from_clause, defined_where_clause, where_lists)
    user_input = ''

    while user_input != 'q':
        try:
            user_input = input("Please input ctable SQL query('q' quit)： \n")

            # fix bug(when fisrt time input is 'q')
            if user_input == 'q':
                break

            select_clause, from_clause, defined_where_clause, where_lists = pre_processing(user_input)
            generator(select_clause, from_clause, defined_where_clause, where_lists)

        except:
            print("ERROR: Illegal Input")
