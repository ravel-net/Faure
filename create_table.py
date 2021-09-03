
import psycopg2

def get_routing(r_len):
    result = [] 
    for i in range(1,r_len+1):
        low = i%127
        high = i//127
        result.append((f'10.0.{high}.{low}' , f"[ABC]", []) )
        result.append((f'10.0.{high}.{low}' , f"[ADEC]", []) )
    return result
    
def create_routing():
    conn = psycopg2.connect(host="127.0.0.1",user="ethan",password="ethan",database="mydb")
    with conn: 
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS routing")
        cur.execute("CREATE TABLE routing(dest TEXT, path TEXT, cond text [])")
        
        routing = get_routing(500)

        query = "INSERT INTO routing (dest, path, cond) VALUES (%s, %s, %s)"
        cur.executemany(query, routing)

        cur.execute("SELECT * FROM routing LIMIT 10")

    return

def create_policy3():
    conn = psycopg2.connect(host="127.0.0.1",user="ethan",password="ethan",database="mydb")
    with conn: 
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS policy3")
        cur.execute("CREATE TABLE policy3(dest TEXT, path TEXT, cond text [])")
        
        routing = get_routing(500)

        query = "INSERT INTO routing (dest, path, cond) VALUES (%s, %s, %s)"
        cur.executemany(query, routing)

        cur.execute("SELECT * FROM routing LIMIT 10")

    return

#create_routing()
create_policy3()