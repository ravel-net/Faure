# from isposs import *
# from ip_policy_gen import *
from ip import *

from random import randint
from timeit import default_timer as timer
from statistics import mean, stdev

import os
import sys

import psycopg2
import json
from psycopg2.extensions import register_adapter, AsIs

cwd = os.getcwd()

rib_file = cwd + '/routeview/rib.txt'
update_file = cwd + '/routeview/update.txt'

#P1. Shortest path
#(DEST, PATH, S_path, cond)
#P2. static routing
#(DEST, PATH, COND)
#P3. filter
#(DEST, PATH, COND)

# size1: policy1 size
# symbol1: variable letter for policy1
def addtwodimdict(thedict, key_a, key_b, val): 
    if key_a in thedict:
        thedict[key_a].update({key_b: val})
    else:
        thedict.update({key_a:{key_b: val}})

def gen_ptable(filename = rib_file, update_file = update_file, size1 = 333,size2 = 333,size3 = 334,symbol1 = 'x', symbol2 = 'y', symbol3 = 'z'):
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
                addtwodimdict(already_dict, ip, s_path, False)
            if[ip, path] not in temp_table:
                temp_table.append([ip, path])
                addtwodimdict(already_dict, ip, s_path, False)
            continue
        elif ip not in ips1 and count1 < size1:
            ips1.add(ip)
            spath_dict[ip] = s_path
            addtwodimdict(already_dict, ip, s_path, False)
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

            p2_rtable.append([ip,path, -1, []])
            continue         
        elif ip in ips2:
            p2_rtable.append([ip,path, -1,[]])
            continue

        # p3: filter
        
        if ip not in ips3 and count3 < size3:
            ips3.add(ip)

            s1 = symbol3 + str(var_count3)
            s2= symbol3 + str(int(var_count3) + 1)

            #p3_cond.append(symbol + ' != ' + ip)
            p3_ctable.append([ip,s2, -1, [str(s2) + ' == nopath'] ])
            p3_rtable.append([ip,path, -1,[] ])
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
        p1_rtable.append([t[0],t[1], spath_dict[t[0]], [] ])
    
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

            list = [ip,operation, path, s_path, []]
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



def load_table(ctable_name = 'policy', rtable_name = 'rtable', update_name = 'update_table'):
    conn = psycopg2.connect(host="127.0.0.1",user="postgres",password="postgres",database="sql")
    #conn = psycopg2.connect(database='mydb',user='ethan',password='gbgb1995629',host='localhost',port='5432')

    ctable, rtable, update_table = gen_ptable()

    with conn: 
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {ctable_name}")
        cur.execute(f'CREATE TABLE {ctable_name}(dest TEXT, path TEXT, length_spath SMALLINT, cond TEXT[] )')
        query = f"INSERT INTO {ctable_name} (dest, path,length_spath, cond) VALUES (%s, %s, %s,%s)"

        cur.executemany(query, ctable)

        cur.execute(f"DROP TABLE IF EXISTS {rtable_name}")
        cur.execute(f'CREATE TABLE {rtable_name} (dest TEXT,path TEXT, length_spath SMALLINT,  cond TEXT[] )')
        query = f"INSERT INTO {rtable_name} (dest, path, length_spath, cond) VALUES (%s, %s, %s, %s)"

        cur.executemany(query, rtable)

        cur.execute(f"DROP TABLE IF EXISTS {update_name}")
        cur.execute(f'CREATE TABLE {update_name}(dest TEXT,operation TEXT, path TEXT, length_spath SMALLINT, cond TEXT[] )')
        query = f"INSERT INTO {update_name} (dest, operation, path, length_spath, cond) VALUES (%s, %s, %s, %s, %s)"

        cur.executemany(query, update_table)



        cur.execute(f"SELECT count(*) FROM {ctable_name}")
        rows = cur.fetchall()
        print(rows)

        cur.execute(f"SELECT count(*) FROM {rtable_name}")
        rows = cur.fetchall()
        print(rows)

        cur.execute(f"SELECT count(*) FROM {update_name}")
        rows = cur.fetchall()
        print(rows)

load_table()
# gen_ptable()




