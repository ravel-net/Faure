------------------------------------------------------------
-- BASE TABLES
------------------------------------------------------------

/* Topology table - pairs of connected nodes
 * sid: switch id
 * nid: next-hop id
 * ishost: if nid is a host
 * isactive: if the sid-nid link is online
 * bw: link bandwidth
 */
DROP TABLE IF EXISTS tp CASCADE;
CREATE UNLOGGED TABLE tp (
       sid      integer,
       nid      integer,
       ishost   integer,
       isactive integer,
       bw       integer,
       PRIMARY KEY (sid, nid)
);
CREATE INDEX ON tp(sid, nid);


/* Configuration table - per-switch flow configuration
 * fid: flow id
 * pid: id of previous-hop node
 * sid: switch id
 * nid: id of next-hop node
 */
DROP TABLE IF EXISTS cf CASCADE;
CREATE UNLOGGED TABLE cf (
       fid      integer,
       pid      integer,
       sid      integer,
       nid      integer
);
CREATE INDEX ON cf(fid,sid);


/* Reachability matrix - end-to-end reachability matrix
 * fid: flow id
 * src: the IP address of the source node
 * dst: the IP address of the destination node
 * vol: volume allocated for the flow
 * FW: if flow should pass through a firewall
 * LB: if flow should be load balanced
 */
DROP TABLE IF EXISTS rm CASCADE;
CREATE UNLOGGED TABLE rm (
       fid      integer,
       src      integer,
       dst      integer,
       vol      integer,
       FW       integer,
       LB       integer,
       PRIMARY KEY (fid)
);
CREATE INDEX ON rm (fid,src,dst);



------------------------------------------------------------
-- NODE TABLES
------------------------------------------------------------

/* Switch table
 * sid: switch id (primary key, NOT datapath id)
 * dpid: datapath id
 * ip: switch's IP address
 * mac: switch's MAC address
 * name: switch's name (in Mininet) 
 */
DROP TABLE IF EXISTS switches CASCADE;
CREATE UNLOGGED TABLE switches (
       sid	integer PRIMARY KEY,
       dpid	varchar(16),
       ip	varchar(16),
       mac	varchar(17),
       name	varchar(16)
);
CREATE INDEX ON switches(sid);


/* Host table
 * hid: host id
 * ip: host's IP address
 * mac: host's MAC address
 * name: hostname (in Mininet)
 */
CREATE UNLOGGED TABLE hosts (
       hid	integer PRIMARY KEY,
       ip	varchar(16),
       mac	varchar(17),
       name	varchar(16)
);
CREATE INDEX ON hosts (hid);


/* Node view - all nodes and switches in the network
 * id: the node's id from its respective table (hosts.hid or switches.sid)
 * name: the node's name
 */
DROP VIEW IF EXISTS nodes CASCADE;
CREATE OR REPLACE VIEW nodes AS (
       SELECT sid AS id, name FROM SWITCHES UNION
       SELECT hid AS id, name FROM HOSTS
);


/* Ports table
 * sid - switch id
 * nid - id of next-hop node
 * port - outport on sid for nid
 */
DROP TABLE IF EXISTS ports CASCADE;
CREATE UNLOGGED TABLE ports (
       sid      integer,
       nid      integer,
       port     integer
);



------------------------------------------------------------
-- ORCHESTRATION PROTOCOL
------------------------------------------------------------

/* Orchestration token clock */
DROP TABLE IF EXISTS clock CASCADE;
CREATE UNLOGGED TABLE clock (
       counts   integer,
       PRIMARY key (counts)
);


/* Initialize the clock to 0 */
INSERT into clock (counts) values (0) ;


/* Routing shortest path vector priority table */
DROP TABLE IF EXISTS p_spv CASCADE;
CREATE UNLOGGED TABLE p_spv (
       counts   integer,
       status   text,
       PRIMARY key (counts)
);


/* Orchestration enabling function */
CREATE OR REPLACE FUNCTION protocol_fun() RETURNS TRIGGER AS
$$
ct = plpy.execute("""select max (counts) from clock""")[0]['max']
plpy.execute ("INSERT INTO p_spv VALUES (" + str (ct+1) + ", 'on');")
return None;
$$
LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;



------------------------------------------------------------
-- USER-FACING REACHABILITY MATRIX
------------------------------------------------------------

/* User reachability matrix */
DROP TABLE IF EXISTS urm CASCADE;
CREATE UNLOGGED TABLE urm (
       fid      integer,
       host1    integer,
       host2    integer,
       PRIMARY KEY (fid)
);
CREATE INDEX ON urm(fid,host1);


/* User reachability matrix insertion */
CREATE OR REPLACE RULE urm_in_rule AS
       ON INSERT TO urm
       DO ALSO
       INSERT INTO rm VALUES (NEW.fid,
                              NEW.host1,
                              NEW.host2,
                              1);


/* User reachability matrix deletion */
CREATE OR REPLACE RULE urm_del_rule AS
       ON DELETE TO urm
       DO ALSO DELETE FROM rm WHERE rm.fid = OLD.fid;

/* User reachability matrix update */
CREATE OR REPLACE RULE urm_up_rule AS
       ON UPDATE TO urm
       DO ALSO (
          DELETE FROM rm WHERE rm.fid = OLD.fid;
          INSERT INTO rm VALUES (OLD.fid,
                                 NEW.host1,
                                 NEW.host2,
                                 1);
       );



------------------------------------------------------------
-- REACHABILITY MATRIX UPDATES
------------------------------------------------------------

DROP TABLE IF EXISTS rm_delta CASCADE;
CREATE UNLOGGED TABLE rm_delta (
       fid      integer,
       src      integer,
       dst      integer,
       vol      integer,
       isadd    integer
);
CREATE INDEX ON rm_delta (fid,src);

CREATE OR REPLACE RULE rm_ins AS
       ON INSERT TO rm
       DO ALSO
           INSERT INTO rm_delta values (NEW.fid, NEW.src, NEW.dst, NEW.vol, 1);

CREATE OR REPLACE RULE rm_del AS
       ON DELETE TO rm
       DO ALSO(
           INSERT INTO rm_delta values (OLD.fid, OLD.src, OLD.dst, OLD.vol, 0);
           DELETE FROM rm_delta WHERE rm_delta.fid = OLD.fid AND isadd = 1;
           );



------------------------------------------------------------
-- SHORTEST PATH VECTOR
------------------------------------------------------------

DROP TABLE IF EXISTS spv_tb_ins CASCADE;
CREATE UNLOGGED TABLE spv_tb_ins (
       fid      integer,
       pid      integer,
       sid      integer,
       nid      integer
);


DROP TABLE IF EXISTS spv_tb_del CASCADE;
CREATE UNLOGGED TABLE spv_tb_del (
       fid      integer,
       pid      integer,
       sid      integer,
       nid      integer
);


CREATE OR REPLACE FUNCTION spv_constraint1_fun ()
RETURNS TRIGGER
AS $$
plpy.notice ("spv_constraint1_fun")
if TD["new"]["status"] == 'on':
    rm = plpy.execute ("SELECT * FROM rm_delta;")

    for t in rm:
        if t["isadd"] == 1:
            f = t["fid"]
            s = t["src"]
            d = t["dst"]
            pv = plpy.execute("SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id, sid as source, nid as target, 1.0::float8 as cost FROM tp WHERE isactive = 1'," +str (s) + "," + str (d)  + ",FALSE, FALSE))")[0]['array']

	    l = len (pv)
            for i in range (l):
                if i + 2 < l:
                    plpy.execute ("INSERT INTO cf (fid,pid,sid,nid) VALUES (" + str (f) + "," + str (pv[i]) + "," +str (pv[i+1]) +"," + str (pv[i+2])+  ");")

        elif t["isadd"] == 0:
            f = t["fid"]
            plpy.execute ("DELETE FROM cf WHERE fid =" +str (f) +";")

    plpy.execute ("DELETE FROM rm_delta;")
return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


CREATE TRIGGER spv_constraint1
       AFTER INSERT ON p_spv
       FOR EACH ROW
       EXECUTE PROCEDURE spv_constraint1_fun();


CREATE OR REPLACE RULE spv_constaint2 AS
       ON INSERT TO p_spv
       WHERE NEW.status = 'on'
       DO ALSO
           (UPDATE p_spv SET status = 'off' WHERE counts = NEW.counts;
           DELETE FROM cf WHERE (fid,pid,sid,nid) IN (SELECT * FROM spv_tb_del);
           INSERT INTO cf (fid,pid,sid,nid) (SELECT * FROM spv_tb_ins);
           DELETE FROM spv_tb_del ;
           DELETE FROM spv_tb_ins ;
           );


CREATE OR REPLACE RULE tick_spv AS
       ON UPDATE TO p_spv
       WHERE (NEW.status = 'off')
       DO ALSO
           INSERT INTO clock values (NEW.counts);


DROP VIEW IF EXISTS spv CASCADE;
CREATE OR REPLACE VIEW spv AS (
       SELECT fid,
              src,
              dst,
              (SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id,
                                                     sid as source,
                                                     nid as target,
                                                     1.0::float8 as cost
                                                     FROM tp
                                                     WHERE isactive = 1', src, dst,FALSE, FALSE))) as pv
       FROM rm
);


DROP VIEW IF EXISTS spv_edge CASCADE;
CREATE OR REPLACE VIEW spv_edge AS (
       WITH num_list AS (
       SELECT UNNEST (ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]) AS num
       )
       SELECT DISTINCT fid, num, ARRAY[pv[num], pv[num+1], pv[num+2]] as edge
       FROM spv, num_list
       WHERE pv != '{}' AND num < array_length (pv, 1) - 1
       ORDER BY fid, num
);


DROP VIEW IF EXISTS spv_switch CASCADE;
CREATE OR REPLACE VIEW spv_switch AS (
       SELECT DISTINCT fid,
              edge[1] as pid,
              edge[2] as sid,
              edge[3] as nid
       FROM spv_edge
       ORDER BY fid
);


DROP VIEW IF EXISTS spv_ins CASCADE;
CREATE OR REPLACE VIEW spv_ins AS (
       SELECT * FROM spv_switch
       EXCEPT (SELECT * FROM cf)
       ORDER BY fid
);


DROP VIEW IF EXISTS spv_del CASCADE;
CREATE OR REPLACE VIEW spv_del AS (
       SELECT * FROM cf
       EXCEPT (SELECT * FROM spv_switch)
       ORDER BY fid
);



------------------------------------------------------------
-- TOPOLOGY UPDATES/REROUTING
------------------------------------------------------------

CREATE OR REPLACE FUNCTION tp2spv_fun () RETURNS TRIGGER
AS $$
isactive = TD["new"]["isactive"]
sid = TD["new"]["sid"]
nid = TD["new"]["nid"]
if isactive == 0:
   fid_delta = plpy.execute ("SELECT fid FROM cf where (sid =" + str (sid) + "and nid =" + str (nid) +") or (sid = "+str (nid)+" and nid = "+str (sid)+");")
   if len (fid_delta) != 0:
      for fid in fid_delta:
          plpy.execute ("INSERT INTO spv_tb_del (SELECT * FROM cf WHERE fid = "+str (fid["fid"])+");")

          s = plpy.execute ("SELECT * FROM rm WHERE fid =" +str (fid["fid"]))[0]["src"]
          d = plpy.execute ("SELECT * FROM rm WHERE fid =" +str (fid["fid"]))[0]["dst"]

          pv = plpy.execute("""SELECT array(SELECT id1 FROM pgr_dijkstra('SELECT 1 as id, sid as source, nid as target, 1.0::float8 as cost FROM tp WHERE isactive = 1',""" +str (s) + "," + str (d)  + ",FALSE, FALSE))""")[0]['array']

          for i in range (len (pv)):
              if i + 2 < len (pv):
                  plpy.execute ("INSERT INTO spv_tb_ins (fid,pid,sid,nid) VALUES (" + str (fid["fid"]) + "," + str (pv[i]) + "," +str (pv[i+1]) +"," + str (pv[i+2])+  ");")

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;

CREATE TRIGGER tp_up_trigger
       AFTER UPDATE ON tp
       FOR EACH ROW
       EXECUTE PROCEDURE protocol_fun();

CREATE TRIGGER tp_up_spv_trigger
       AFTER UPDATE ON tp
       FOR EACH ROW
       EXECUTE PROCEDURE tp2spv_fun();

------------------------------------------------------------
-- APPLICATION VIOLATION VIEWS/TABLES
------------------------------------------------------------
DROP TABLE IF EXISTS app_violation CASCADE;
CREATE TABLE app_violation (
       app      VARCHAR,
       violation      VARCHAR
);
CREATE INDEX ON app_violation(app);

------------------------------------------------------------
-- MY EXPERIMENT RECHABILITY MATRIX TABLE
------------------------------------------------------------
DROP TABLE IF EXISTS my_rm CASCADE;
CREATE TABLE my_rm (
       fid      integer,
       src      integer,
       dst      integer,
       FW       integer,
       PRIMARY KEY (fid)
);
CREATE INDEX ON my_rm (fid,src,dst);