------------------------------------------------------------
-- SERVICE CHAIN (PGA) APPLICATION
------------------------------------------------------------

DROP TABLE IF EXISTS PGA_policy CASCADE;
CREATE UNLOGGED TABLE PGA_policy (
       gid1	      integer,
       gid2 	      integer,
       MB	      text,
       PRIMARY key (gid1, gid2)
);
CREATE INDEX ON PGA_policy (gid1, gid2);

DROP TABLE IF EXISTS PGA_group CASCADE;
CREATE UNLOGGED TABLE PGA_group (
       gid	      integer,
       sid_array      integer[],
       PRIMARY key (gid)
);
CREATE INDEX ON PGA_group (gid);

DROP VIEW IF EXISTS PGA CASCADE;
CREATE OR REPLACE VIEW PGA AS(
       WITH PGA_group_policy AS (
       	    SELECT p1.sid_array AS sa1,
       	      	   p2.sid_array AS sa2, MB
            FROM PGA_group p1, PGA_group p2, PGA_policy
       	    WHERE p1.gid = gid1 AND p2.gid = gid2),
       PGA_group_policy2 AS (
            SELECT unnest (sa1)"sid1", sa2, MB
	    FROM PGA_group_policy)
       SELECT sid1, unnest (sa2)"sid2", MB
       FROM  PGA_group_policy2
);

CREATE OR REPLACE VIEW PGA_violation AS (
       SELECT fid, MB
       FROM rm, PGA
       WHERE src = sid1 AND dst = sid2 AND
       ((MB = 'FW' AND FW=0) OR (MB='LB' AND LB=0))
);

CREATE OR REPLACE RULE PGA_repair AS
       ON DELETE TO PGA_violation
       DO INSTEAD
       (
       UPDATE rm SET FW = 1 WHERE fid = OLD.fid AND OLD.MB = 'FW';
       UPDATE rm SET LB = 1 WHERE fid = OLD.fid AND OLD.MB = 'LB';
       );



------------------------------------------------------------
-- SAMPLE CONFIGURATION (for toy_dtp.py topo)
------------------------------------------------------------

-- INSERT INTO PGA_policy (gid1, gid2, MB) VALUES (1,2,'FW'), (4,3,'LB');
-- INSERT INTO PGA_group (gid, sid_array) VALUES
-- 	(1, ARRAY[5]),
-- 	(2, ARRAY[6]),
-- 	(3, ARRAY[6,7]),
-- 	(4, ARRAY[5,8]);
