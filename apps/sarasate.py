from ravel.app import AppConsole, mk_watchcmd
import psycopg2
import tabulate
import re
from z3 import *

class RelaAlgConsole(AppConsole):

    def default(self, line):
        "Execute a PostgreSQL statement"
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

                attr_drop = ""
                for c in common_attr:
                    attr_drop = attr_drop + "drop column {}_{}, ".format(t2_name, c)

                    if 'len' in c:
                        continue

                    sql = "update output set {} = {}_{} where not is_var({})".format(c, t2_name, c, c)
                    self.db.cursor.execute(sql)

                # remove the spare ,
                attr_drop = attr_drop[:-2]
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

    def do_data(self, line):
        "Create data content."

        select_clause, from_clause, defined_where_clause, where_lists = self.pre_processing(line)
        self._data(select_clause, from_clause, defined_where_clause, where_lists)

    def do_condition(self, line):
        "Update Conditions"
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

                attr_diff += "array_cat({}.condition, {}.condition) as condition".format(t1_name, t2_name)

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

                attr_drop = ""

                for c in common_attr:
                    sql = "update output set {} = {}_{} where not is_var({})".format(c, t2_name, c, c)
                    attr_drop = attr_drop + "drop column {}_{}, ".format(t2_name, c)
                    self.db.cursor.execute(sql)

                # remove the spare ,
                attr_drop = attr_drop[:-2]
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
        """Launch an xterm window to watch database tables in real-time
           Usage: watch [table1(,max_rows)] [table2(,max_rows)] ...
           Example: watch hosts switches cf,5"""
        if not line:
            return

        args = line.split()
        if len(args) == 0:
            print("Invalid syntax")
            return

        cmd, cmdfile = mk_watchcmd(self.env.db, args)
        self.env.mkterm(cmd, cmdfile)

shortcut = "s"
description = "Relational Algebra for Conditional Table."
console = RelaAlgConsole