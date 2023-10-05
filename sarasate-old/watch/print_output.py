import psycopg2
import os

USER = 'postgres'
DATABASE = 'sql'


# TITLE = 'select * from policy1 where not_equal(path, [ABC])'
# TITLE = 'policy 1 join policy 2'
TITLE = 'New Best Routes'
# TITLE = 'New Candidate Routes'

"""
check table if exits before displaying table content
"""
def print_output(tablename = 'output', columns = '*'):
    SQL = 'select {} from {};'.format(columns, tablename)

    conn = psycopg2.connect(host="127.0.0.1",user=USER,password="postgres",database=DATABASE)

    # check table
    cur = conn.cursor()
    cur.execute("select * from information_schema.tables where table_name='{}'".format(tablename))

    if bool(cur.rowcount):
        title = '-------{}-------'.format(TITLE)
        os.system("echo '{}'; psql -U postgres -d sql -c '{}'".format(title, SQL))
    else:
        print('-------{}-------'.format(TITLE))



print_output('new_best_routes')
# print_output(tablename='new_candidate')
