------------------------------------------------------------
-- BANDWIDTH CONSTRAINT APPLICATION
------------------------------------------------------------


DROP TABLE IF EXISTS Merlin_policy CASCADE;
CREATE UNLOGGED TABLE MERLIN_policy (
       fid	      integer,
       rate 	      integer,
       PRIMARY key (fid)
);

CREATE OR REPLACE VIEW MERLIN_violation AS (
       SELECT rm.fid, rate AS req, vol AS asgn
       FROM rm, Merlin_policy
       WHERE rm.fid = Merlin_policy.fid AND rate > vol
);

CREATE OR REPLACE RULE Merlin_repair AS
       ON DELETE TO Merlin_violation
       DO INSTEAD
              UPDATE rm SET vol = OLD.req WHERE fid = OLD.fid;
