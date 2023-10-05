from ravel.app import AppConsole, mk_watchcmd
import psycopg2
import tabulate
import re

rib_file = './topo/RouteView/rib.txt'
upd_file = './topo/RouteView/update.txt'

class BGPConsole(AppConsole):
    def do_echo(self, line):
        print("test", line)

    def default(self, line):
        """
        Execute a PostgreSQL statement
        """
        try:
            select_clause, from_clause, defined_where_clause, where_lists = self.pre_processing(line)
            self.generator(select_clause, from_clause, defined_where_clause, where_lists)

        except psycopg2.ProgrammingError as e:
            print(e)
            return

        try:
            self.db.cursor.execute("select * from output;")
            data = self.db.cursor.fetchall()
            if data is not None:
                names = [row[0] for row in self.db.cursor.description]
                print(tabulate.tabulate(data, headers=names))
        except psycopg2.ProgrammingError:
            # no results, eg from an insert/delete
            pass
        except TypeError as e:
            print(e)

    def pre_processing(self, query):
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

    def generator(self, select_clause, from_clause, where_clause, where_lists):
        self.db.cursor.execute("drop table if exists output")

        '''
        The number of tables is greater than 1, it is join operation
        else, it is selection
        '''
        table_list = from_clause.split(',')
        if len(table_list) > 1:

            # print('join')
            t1_name = table_list[0].strip()
            t2_name = table_list[1].strip()
            
            if '*' in select_clause:
                '''
                get the attributes of each table
                '''
                self.db.cursor.execute("select * from {}".format(t1_name))
                t1_attrs = [row[0] for row in self.db.cursor.description]
                self.db.cursor.execute("select * from {}".format(t2_name))
                t2_attrs = [row[0] for row in self.db.cursor.description]
                
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

                if 'condition' in t1_attrs and 'condition' in t2_attrs:
                    attr_diff += "array_cat({}.condition, {}.condition) as condition".format(t1_name, t2_name)
                elif 'condition' in t1_attrs or 'condition' in t2_attrs:
                    attr_diff += "condition"
                else:
                    attr_diff = attr_diff
                
                # print("Step1: Create Data Content")
                sql = "create table output as select {} {} FROM {} where ".format(attr_equal, attr_diff, from_clause) + where_clause
                self.db.cursor.execute(sql)

                # print("Step2: Update Condition")

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
                    self.db.cursor.execute(sql)
                
                # add shortest path policy condition
                sql = "update output set condition = array_append(condition, 'l(' || path || ') == ' || l({}_path));".format(t2_name)
                self.db.cursor.execute(sql)

                attr_drop = ""
                for c in common_attr:
                    attr_drop = attr_drop + "drop column {}_{}, ".format(t2_name, c)

                    if 'len' in c:
                        continue

                    sql = "update output set {} = {}_{} where not is_var({})".format(c, t2_name, c, c)
                    self.db.cursor.execute(sql)

                # remove the spare ,
                # attr_drop = attr_drop[:-2]
                attr_drop = attr_drop + "drop column len_path"
                sql = "alter table output {};".format(attr_drop)
                self.db.cursor.execute(sql)

            else:
                print("still working")   
        else:
            # print('selection')
            # print('Step1: Create Data Content')
            sql = 'create table output as '

            sql = sql + select_clause + ' where '+ where_clause + ';'
            self.db.cursor.execute(sql)

            # print('Step2: Update Condition')
            for w in where_lists:
                args = w.strip().split(' ')
                left = args[0].strip()
                opr = args[1].strip()
                right = args[2].strip()
                # repalce = with == in order accommodate z3
                if '!=' not in opr and '<=' not in opr and '>=' not in opr and '=' in opr:
                    opr = opr.replace('=', '==')
                
                sql = "update output set condition = array_append(condition, {} || ' {} ' || {});".format(left, opr, right)
                self.db.cursor.execute(sql)


        # print('Step3: Normalization')
        sql = 'delete from output where is_contradiction(condition);'

        self.db.cursor.execute(sql)
        sql = "UPDATE output SET condition = '{}' WHERE is_tauto(condition);"

        self.db.cursor.execute(sql)
        sql = "UPDATE output SET condition = remove_redundant(condition) WHERE has_redundant(condition);"
        self.db.cursor.execute(sql)
    
    '''
    Load realistic data from RouteView RIB and UPDATE
    1. bgp_policy and candidate routes are generated from RIB
    2. routes_delta are generated from UPDATE
    default file: 2021.06.10 00:00
    '''
    def do_load(self,line):
        """
        Load realistic data for BGP simulation.
        1. BGP policy generated from RIB file including three types of policies(stored in bgp_policy): 
            a. Shortest Path Policy.
            b. Static Routes Policy.
            c. Filter Policy.
        2. Current best routes are generated by joining bgp policy and candidate routes(inferred from RIB file). 
           The data is stored in current_best_routes table.
        3. BGP announcement is generated from UPDATE file (stored in routes_delta table).

        Source: MRT format RIBs and UPDATEs from route-views2.oregon-ix.net(2021.06.10 00:00)   
        """
        # args = line.split()
        # if len(args) != 2:
        #     print("Invalid syntax") 
        #     return
        
        # rib_file = args[0]
        # upd_file = args[1]
        ptable, rtable, update_table = self._gen_ptable()
        
        self.db.cursor.execute("TRUNCATE TABLE bgp_policy CASCADE;")
        self.db.cursor.executemany("INSERT INTO bgp_policy VALUES (%s, %s, %s, %s);", ptable)

        self.db.cursor.execute("TRUNCATE TABLE routes CASCADE;")
        self.db.cursor.executemany("INSERT INTO routes(dest, path, min_len) VALUES (%s, %s, %s);", rtable)

        self.db.cursor.execute("TRUNCATE TABLE routes_delta CASCADE;")
        self.db.cursor.executemany("INSERT INTO routes_delta(dest, operation, path, len_path) VALUES (%s, %s, %s, %s);", update_table)
    
    def do_loaddemo(self, line):
        """
        Load realistic data for BGP simulation.
        1. BGP policy generated from RIB file including three types of policies(stored in bgp_policy): 
            a. Shortest Path Policy.
            b. Static Routes Policy.
            c. Filter Policy.
        2. Current best routes are generated by joining bgp policy and candidate routes(inferred from RIB file). The data is stored in current_best_routes table.
        3. BGP announcement is generated from UPDATE file (stored in routes_delta table).

        Source: MRT format RIBs and UPDATEs from route-views2.oregon-ix.net(2021.06.10 00:00)   
        """
        ptable = [
            ['1.6.68.0/22', 'x579', 2, '{"l(x579) <= 2"}'],
            ['1.6.4.0/22', 'x531', 2, '{"l(x531) <= 2"}'],
            ['1.6.188.0/24', 'y5', -1, '{"y5 == 3303 6453 9583"}'],
            ['1.22.208.0/24', 'z2', -1, '{"z2 == nopath"}']
        ]

        rtable = [['1.6.4.0/22', '3303 6453 9583', 2], ['1.6.4.0/22', '23673 9583', 2], ['1.6.4.0/22', '20912 3257 1299 9583', 2], ['1.6.4.0/22', '8492 31133 174 9583', 2], ['1.6.4.0/22', '3561 209 3356 1299 9583', 2], ['1.6.4.0/22', '7018 1299 9583', 2], ['1.6.4.0/22', '31019 43531 9583', 2], ['1.6.4.0/22', '34224 6453 9583', 2], ['1.6.4.0/22', '37100 6461 7473 9583', 2], ['1.6.4.0/22', '3549 3356 1299 9583', 2], ['1.6.4.0/22', '3130 2914 1299 9583', 2], ['1.6.4.0/22', '2152 7473 9583', 2], ['1.6.4.0/22', '293 3320 9583', 2], ['1.6.4.0/22', '6939 9583', 2], ['1.6.4.0/22', '2497 3491 9583', 2], ['1.6.4.0/22', '53767 14315 6453 6453 9583', 2], ['1.6.4.0/22', '3257 1299 9583', 2], ['1.6.4.0/22', '701 3320 9583', 2], ['1.6.4.0/22', '5413 6461 7473 9583', 2], ['1.6.4.0/22', '22652 6461 7473 9583', 2], ['1.6.4.0/22', '3741 174 9583', 2], ['1.6.4.0/22', '7660 4635 3491 3491 9583', 2], ['1.6.4.0/22', '2914 3491 9583', 2], ['1.6.4.0/22', '24441 3491 3491 9583', 2], ['1.6.4.0/22', '1221 4637 3320 9583', 2], ['1.6.4.0/22', '11686 174 9583', 2], ['1.6.4.0/22', '20130 6939 9583', 2], ['1.6.4.0/22', '57866 6461 7473 9583', 2], ['1.6.4.0/22', '49788 1299 9583', 2], ['1.6.4.0/22', '18106 9583', 2], ['1.6.4.0/22', '1403 1299 9583', 2], ['1.6.4.0/22', '3549 3356 174 9583', 2], ['1.6.4.0/22', '1299 9583', 2], ['1.6.4.0/22', '3130 1239 6453 9583', 2], ['1.6.68.0/22', '3303 6453 9583', 2], ['1.6.68.0/22', '23673 3491 174 9583', 2], ['1.6.68.0/22', '20912 3257 1299 9583', 2], ['1.6.68.0/22', '8492 31133 174 9583', 2], ['1.6.68.0/22', '3561 209 3356 1299 9583', 2], ['1.6.68.0/22', '7018 1299 9583', 2], ['1.6.68.0/22', '31019 43531 9583', 2], ['1.6.68.0/22', '34224 6453 9583', 2], ['1.6.68.0/22', '37100 6453 9583', 2], ['1.6.68.0/22', '3130 2914 1299 9583', 2], ['1.6.68.0/22', '22652 6453 9583', 2], ['1.6.68.0/22', '293 3320 9583', 2], ['1.6.68.0/22', '6939 9583', 2], ['1.6.68.0/22', '3549 3356 1299 9583', 2], ['1.6.68.0/22', '2914 6453 9583', 2], ['1.6.68.0/22', '53767 14315 6453 6453 9583', 2], ['1.6.68.0/22', '3257 1299 9583', 2], ['1.6.68.0/22', '701 3320 9583', 2], ['1.6.68.0/22', '49788 1299 9583', 2], ['1.6.68.0/22', '5413 1299 9583', 2], ['1.6.68.0/22', '7660 2516 3320 9583', 2], ['1.6.68.0/22', '2497 6453 9583', 2], ['1.6.68.0/22', '3741 174 9583', 2], ['1.6.68.0/22', '57866 1299 9583', 2], ['1.6.68.0/22', '2152 3356 6453 9583', 2], ['1.6.68.0/22', '24441 3491 3491 6453 9583', 2], ['1.6.68.0/22', '1221 4637 3320 9583', 2], ['1.6.68.0/22', '11686 174 9583', 2], ['1.6.68.0/22', '20130 6939 9583', 2], ['1.6.68.0/22', '18106 6939 9583', 2], ['1.6.68.0/22', '1403 1299 9583', 2], ['1.6.68.0/22', '3549 3356 174 9583', 2], ['1.6.68.0/22', '1299 9583', 2], ['1.6.68.0/22', '3130 1239 6453 9583', 2], ['1.6.188.0/24', '3303 6453 9583', -1], ['1.6.188.0/24', '23673 3491 174 9583', -1], ['1.6.188.0/24', '20912 3257 1299 9583', -1], ['1.6.188.0/24', '8492 31133 174 9583', -1], ['1.6.188.0/24', '3561 209 3356 1299 9583', -1], ['1.6.188.0/24', '7018 1299 9583', -1], ['1.6.188.0/24', '31019 43531 9583', -1], ['1.6.188.0/24', '34224 6453 9583', -1], ['1.6.188.0/24', '37100 6453 9583', -1], ['1.6.188.0/24', '49788 1299 9583', -1], ['1.6.188.0/24', '3130 2914 1299 9583', -1], ['1.6.188.0/24', '22652 6453 9583', -1], ['1.6.188.0/24', '293 3320 9583', -1], ['1.6.188.0/24', '6939 9583', -1], ['1.6.188.0/24', '3549 3356 1299 9583', -1], ['1.6.188.0/24', '2914 6453 9583', -1], ['1.6.188.0/24', '53767 14315 6453 6453 9583', -1], ['1.6.188.0/24', '3257 1299 9583', -1], ['1.6.188.0/24', '701 3320 9583', -1], ['1.6.188.0/24', '5413 1299 9583', -1], ['1.6.188.0/24', '7660 2516 3320 9583', -1], ['1.6.188.0/24', '2497 6453 9583', -1], ['1.6.188.0/24', '3741 174 9583', -1], ['1.6.188.0/24', '57866 1299 9583', -1], ['1.6.188.0/24', '2152 3356 6453 9583', -1], ['1.6.188.0/24', '24441 3491 3491 6453 9583', -1], ['1.6.188.0/24', '1221 4637 3320 9583', -1], ['1.6.188.0/24', '11686 174 9583', -1], ['1.6.188.0/24', '20130 6939 9583', -1], ['1.6.188.0/24', '18106 6939 9583', -1], ['1.6.188.0/24', '1403 1299 9583', -1], ['1.6.188.0/24', '3549 3356 174 9583', -1], ['1.6.188.0/24', '1299 9583', -1], ['1.6.188.0/24', '3130 2914 1299 9583', -1], ['1.22.208.0/24', '3303 9498 45528', -1]]

        current_best_routes = [['1.6.188.0/24', '3303 6453 9583', -1], ['1.6.4.0/22', '23673 9583', 2], ['1.6.68.0/22', '6939 9583', 2]]

        update_table = [
            ['1.6.68.0/22', 'A', '3130 2914 1299 9583', 4],
            ['1.6.68.0/22', 'A', '9583', 1],
            ['1.6.4.0/22', 'A', '3130 2914 1299 9583', 4],
            ['1.6.188.0/24', 'A','2914 6453 9583',  3 ],
            ['1.22.208.0/24', 'A', '3130 2914 1299 9498 45528', 5]
        ]
        self.db.cursor.execute("TRUNCATE TABLE bgp_policy CASCADE;")
        self.db.cursor.executemany("INSERT INTO bgp_policy VALUES (%s, %s, %s, %s);", ptable)

        self.db.cursor.execute("TRUNCATE TABLE routes CASCADE;")
        self.db.cursor.executemany("INSERT INTO routes(dest, path, min_len) VALUES (%s, %s, %s);", rtable)

        self.db.cursor.execute("TRUNCATE TABLE current_best_routes CASCADE;")
        self.db.cursor.executemany("INSERT INTO current_best_routes(dest, path, min_len) VALUES (%s, %s, %s);", current_best_routes)
        
        self.db.cursor.execute("TRUNCATE TABLE routes_delta CASCADE;")
        self.db.cursor.executemany("INSERT INTO routes_delta(dest, operation, path, len_path) VALUES (%s, %s, %s, %s);", update_table)


    def do_extend_values(self, line):
        """
        Extend values in condtion column to variables and rename the table name
        Usage: extend_values [table] [new_name] ...
        """
        args = line.split()
        if len(args) != 2:
            print("Invalid syntax") 
            return

        old_name = args[0]
        new_name = args[1]

        try:
            sql = "DROP TABLE IF EXISTS {};".format(new_name)
            print(sql)
            self.db.cursor.execute(sql)

            sql = "create table {} as select dest, set_path_val(path, condition) as path, min_len from {};".format(new_name, old_name)
            print(sql)
            self.db.cursor.execute(sql)
        except psycopg2.ProgrammingError as e:
            print(e)
            return

        try:
            print('\n************************************************************************')
            self.db.cursor.execute("select * from {};".format(new_name))
            data = self.db.cursor.fetchall()
            if data is not None:
                names = [row[0] for row in self.db.cursor.description]
                print(tabulate.tabulate(data, headers=names))
            print('************************************************************************')
        except psycopg2.ProgrammingError:
            # no results, eg from an insert/delete
            pass
        except TypeError as e:
            print(e)

    '''
    Update Policy
    arg1: policy table
    arg2: routes_delta
    '''
    def do_update_policy(self, line):
        """
        Update current bgp policy that are affected by bgp announcement
        Usage: update_policy [policy] [delta]
        """
        args = line.split()
        if len(args) != 2:
            print("Invalid syntax") 
            return
        
        policy = args[0]
        delta = args[1]

        try:
            sql = "UPDATE {} \
                    SET min_len = {}.len_path, \
                    condition = ARRAY['l(' || {}.path || ') <= ' || {}.len_path] \
                    FROM {} \
                    WHERE {}.min_len > {}.len_path \
                    AND {}.dest = {}.dest;".format(policy, delta, policy, delta, delta, policy, delta, policy, delta)
            
            # print(sql)
            self.db.cursor.execute(sql)
        except psycopg2.ProgrammingError as e:
            print(e)
            return



    '''
    Union
    arg1: current_best_routes
    arg2: routes_delta
    '''
    def do_union(self, line):
        """
        Union operation. 
        Usage: union [table1] [table2]
        """
        args = line.split()
        if len(args) != 2:
            print("Invalid syntax") 
            return
        
        current = args[0]
        delta = args[1]

        # name = "{}_union_{}".format(current, delta)
        name = "new_routes"

        try:
            sql = "DROP TABLE IF EXISTS {};".format(name)
            # print(sql)
            self.db.cursor.execute(sql)

            sql = "create table {} as select dest, path, min_len as len_path \
                    from {} \
                    where dest in (\
                        select dest from {} \
                    ) \
                    union select dest, path, len_path \
                    from {};".format(name, current, delta, delta)
            # print(sql)
            self.db.cursor.execute(sql)
        except psycopg2.ProgrammingError as e:
            print(e)
            return
        
        try:
            print('\n************************************************************************')
            self.db.cursor.execute("select * from {};".format(name))
            data = self.db.cursor.fetchall()
            if data is not None:
                names = [row[0] for row in self.db.cursor.description]
                print(tabulate.tabulate(data, headers=names))
            print('************************************************************************')
        except psycopg2.ProgrammingError:
            # no results, eg from an insert/delete
            pass
        except TypeError as e:
            print(e)

    def do_data(self, line):
        """
        Create data content.
        """

        select_clause, from_clause, defined_where_clause, where_lists = self.pre_processing(line)
        self._data(select_clause, from_clause, defined_where_clause, where_lists)

    def do_condition(self, line):
        """
        Update Conditions
        """
        select_clause, from_clause, defined_where_clause, where_lists = self.pre_processing(line)
        self._condition(select_clause, from_clause, defined_where_clause, where_lists)

        # _, condition, _ = self._get_sql(line)

        # print("\nStep2: Update Conditions\n")
        # for c in condition:
        #     if c != '':
        #         print(c)
        #         self.db.cursor.execute(c)

    def do_z3(self, line):
        self._z3()

    def _data(self, select_clause, from_clause, where_clause, where_lists):
        self.db.cursor.execute("drop table if exists output")

        '''
        The number of tables is greater than 1, it is join operation
        else, it is selection
        '''
        table_list = from_clause.split(',')
        if len(table_list) > 1:

            # print('join')
            t1_name = table_list[0].strip()
            t2_name = table_list[1].strip()
            
            if '*' in select_clause:
                '''
                get the attributes of each table
                '''
                self.db.cursor.execute("select * from {}".format(t1_name))
                t1_attrs = [row[0] for row in self.db.cursor.description]
                self.db.cursor.execute("select * from {}".format(t2_name))
                t2_attrs = [row[0] for row in self.db.cursor.description]
                
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

                if 'condition' in t1_attrs and 'condition' in t2_attrs:
                    attr_diff += "array_cat({}.condition, {}.condition) as condition".format(t1_name, t2_name)
                elif 'condition' in t1_attrs or 'condition' in t2_attrs:
                    attr_diff += "condition"
                else:
                    attr_diff = attr_diff

                # attr_diff += "array_cat({}.condition, {}.condition) as condition".format(t1_name, t2_name)

                # print("Step1: Create Data Content")
                sql = "create table output as select {} {} FROM {} where ".format(attr_equal, attr_diff, from_clause) + where_clause
                self.db.cursor.execute(sql)

            else:
                print("still working")
    
        else:
            # print('selection')
            # print('Step1: Create Data Content')
            sql = 'create table output as '

            sql = sql + select_clause + ' where '+ where_clause + ';'
            print(sql)
            self.db.cursor.execute(sql)


    def _condition(self, select_clause, from_clause, where_clause, where_lists):
        '''
        The number of tables is greater than 1, it is join operation
        else, it is selection
        '''
        table_list = from_clause.split(',')
        if len(table_list) > 1:

            # print('join')
            t1_name = table_list[0].strip()
            t2_name = table_list[1].strip()
            
            if '*' in select_clause:
                '''
                get the attributes of each table
                '''
                self.db.cursor.execute("select * from {}".format(t1_name))
                t1_attrs = [row[0] for row in self.db.cursor.description]
                self.db.cursor.execute("select * from {}".format(t2_name))
                t2_attrs = [row[0] for row in self.db.cursor.description]
                
                '''
                get common attributes and difference attributes
                '''
                common_attr = set(t1_attrs).intersection(set(t2_attrs)) - set(['condition'])
                union_attr = set(t1_attrs).union(set(t2_attrs)) - set(['condition'])
                diff_attr = union_attr - common_attr

                # print("Step2: Update Condition")

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
                    self.db.cursor.execute(sql)

                # add shortest path policy condition
                sql = "update output set condition = array_append(condition, 'l(' || path || ') == ' || l({}_path));".format(t2_name)
                self.db.cursor.execute(sql)

                attr_drop = ""

                for c in common_attr:
                    sql = "update output set {} = {}_{} where not is_var({})".format(c, t2_name, c, c)
                    attr_drop = attr_drop + "drop column {}_{}, ".format(t2_name, c)
                    self.db.cursor.execute(sql)

                # remove the spare ,
                # attr_drop = attr_drop[:-2]
                attr_drop = attr_drop + "drop column len_path"
                sql = "alter table output {};".format(attr_drop)
                self.db.cursor.execute(sql)
            else:
                print("still working")

    
        else:

            # print('Step2: Update Condition')
            for w in where_lists:
                args = w.strip().split(' ')
                left = args[0].strip()
                opr = args[1].strip()
                right = args[2].strip()
                # repalce = with == in order accommodate z3
                if '!=' not in opr and '<=' not in opr and '>=' not in opr and '=' in opr:
                    opr = opr.replace('=', '==')
                
                sql = "update output set condition = array_append(condition, {} || ' {} ' || {});".format(left, opr, right)
                self.db.cursor.execute(sql)


    def _z3(self):
        # print('Step3: Normalization')
        sql = 'delete from output where is_contradiction(condition);'
        self.db.cursor.execute(sql)

        sql = "UPDATE output SET condition = '{}' WHERE is_tauto(condition);"
        self.db.cursor.execute(sql)

        sql = "UPDATE output SET condition = remove_redundant(condition) WHERE has_redundant(condition);"
        self.db.cursor.execute(sql)

    def do_watch(self, line):
        """
        Launch an xterm window to watch database tables in real-time
        Usage: watch [table1(,max_rows)] [table2(,max_rows)] ...
        Example: watch hosts switches cf,5
        """
        if not line:
            return

        args = line.split()
        if len(args) == 0:
            print("Invalid syntax")
            return

        cmd, cmdfile = mk_watchcmd(self.env.db, args)
        self.env.mkterm(cmd, cmdfile)
    
        
    '''
    Tool function for gen_ptable()
    '''
    def _addtwodimdict(self, thedict, key_a, key_b, val): 
        if key_a in thedict:
            thedict[key_a].update({key_b: val})
        else:
            thedict.update({key_a:{key_b: val}})  

    '''
    Generate policy, condidates routes and routes_delta
    1. policy: a. shortest path policy
               b. static routes policy
               c. filter policy
    2. candidate routes
    3. delta routes: a. annoucement
                     b. withdrawal
    '''
    def _gen_ptable(self, filename = rib_file, update_file = upd_file, size1 = 333,size2 = 333,size3 = 334,symbol1 = 'x', symbol2 = 'y', symbol3 = 'z'):
        # policy, routing, rib = gen_all(rib_file, 'x', 'W', size1)
        # for i in range(0,5):
        #     print(policy[i])
        ctable = [] # policy table
        rtable = [] # route condidate table
        update_table =[] # UPDATE table
        upd_set = set() # check update duplication

        ips = set()
        p1 = []
        p2 = []
        p3 = []

        count1 = 0
        count2 = 0
        count3 = 0

        fo = open(filename, 'r')

        ips1 = set()
        ips2 = set()
        ips3 = set()
        spath_dict = {}

        temp_table = []

        p1_ctable = []
        p2_ctable = []
        p3_ctable = []
        p1_rtable = []
        p2_rtable = []
        p3_rtable = []

        var_count1 = 1
        var_count2 = 1
        var_count3 = 1
        p3_cond = []
        already_dict = {}
        for line in fo:

            record = line.split('|')

            ip = record[5]
            path = record[6].replace('{', '').replace('}', '')
            s_path = len(path.split(' '))
            
            # P1
            if ip in ips1: 
                if s_path < spath_dict[ip]:
                    spath_dict[ip] = s_path
                    self._addtwodimdict(already_dict, ip, s_path, False)
                if[ip, path] not in temp_table:
                    temp_table.append([ip, path])
                    self._addtwodimdict(already_dict, ip, s_path, False)
                continue
            elif ip not in ips1 and count1 < size1:
                ips1.add(ip)
                spath_dict[ip] = s_path
                self._addtwodimdict(already_dict, ip, s_path, False)
                temp_table.append([ip, path])
                count1 +=1
                continue

            # P2 static routing 

            if ip not in ips2 and count2 < size2:
                ips2.add(ip)
                symbol = symbol2 + str(var_count2)
                cond = [symbol + ' == '  + path  ]
                var_count2  += 1
                p2_ctable.append([ip,symbol, -1, cond ])    
                count2 +=1

                # p2_rtable.append([ip,path, -1, []])
                p2_rtable.append([ip,path, -1])
                continue         
            elif ip in ips2:
                # p2_rtable.append([ip,path, -1,[]])
                p2_rtable.append([ip,path, -1])
                continue

            # p3: filter
            
            if ip not in ips3 and count3 < size3:
                ips3.add(ip)

                s1 = symbol3 + str(var_count3)
                s2= symbol3 + str(int(var_count3) + 1)

                #p3_cond.append(symbol + ' != ' + ip)
                p3_ctable.append([ip,s2, -1, [str(s2) + ' == nopath'] ])
                p3_rtable.append([ip,path, -1])
                count3 += 1
                continue


        #p1 
        ips1_temp = set()
        for t in temp_table:
            if t[0] not in ips1_temp:

                cond = ['l(' + symbol1 + str(var_count1)+ ')' + ' <= ' + str(spath_dict[t[0]])]

                p1_ctable.append([t[0], symbol1 +  str(var_count1) , spath_dict[t[0]], cond]  )
                var_count1 += 2
                ips1_temp.add(t[0])
            # p1_rtable.append([t[0],t[1], spath_dict[t[0]], [] ])
            p1_rtable.append([t[0],t[1], spath_dict[t[0]]])
        
        # p3
        # num = var_count3 + 1
        # p3_ctable.append([symbol3+str(var_count3),symbol3+str(num), '_', p3_cond  ])



        # UPDATE table
        upf = open(update_file, 'r')

        for line in upf:

            record = line.split('|')

            ip = record[5]
            if ip in ips1 or ip in ips2 or ip in ips3:
                path = record[6].replace('{', '').replace('}', '')
                s_path = len(path.split(' '))
                if 'A' in record[2]:
                    operation = 'A'
                else: 
                    operation = 'W'

                list = [ip,operation, path, s_path]
                s = " ".join([str(item) for item in list]) # list to string

                if s not in upd_set: # if str in upd_set that means this record already in update_table
                    update_table.append(list)
                    upd_set.add(s)

        for i in range(5):
            print(p1_ctable[i])

        for i in range(5):
            print(p1_rtable[i])

        for i in range(5):
            print(p2_ctable[i])
        for i in range(5):
            print(p2_rtable[i])

        #print(p3_ctable)
        for i in range(5):
            print(p3_ctable[i])    
        for i in range(5):
            print(p3_rtable[i])     
        ctable = p1_ctable + p2_ctable + p3_ctable

        rtable = p1_rtable + p2_rtable + p3_rtable

        print(len(ctable), len(rtable), len(update_table))


        return ctable , rtable, update_table



shortcut = "bgp"
description = "BGP simulation"
console = BGPConsole

if __name__ == '__main__':
    bgp = BGPConsole()
    bgp.do_loaddata()
