import psycopg2

conn = psycopg2.connect(host="127.0.0.1",user="postgres",password="postgres",database="sql")

cur = conn.cursor()

sql = 'select * from rtable where dest in (select dest from sample_update);'

cur.execute(sql)

row = cur.fetchone()

list = []

while row is not None:
    list.append([row[0], row[1], row[2]])
    row = cur.fetchone()

print(list)
