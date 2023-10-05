------------------------------------------------------------
-- STATEFUL FIREWALL
------------------------------------------------------------

/* Flow whitelist */
DROP TABLE IF EXISTS FW_policy_acl CASCADE;
CREATE UNLOGGED TABLE FW_policy_acl (
       end1           integer,
       end2           integer,
       allow          integer,
       PRIMARY key (end1, end2)
);
CREATE INDEX ON FW_policy_acl (end1,end2);

/* Node whitelist */
DROP TABLE IF EXISTS FW_policy_user CASCADE;
CREATE UNLOGGED TABLE FW_policy_user (
       uid            integer
);

/* If flow source is in whitelist, allow and add to flow whitelist */
CREATE OR REPLACE RULE FW1 AS
       ON INSERT TO rm
       WHERE ((NEW.src, NEW.dst) NOT IN (SELECT end2, end1 FROM FW_policy_acl)) AND
              (NEW.src IN (SELECT * FROM FW_policy_user))
       DO ALSO (
          INSERT INTO FW_policy_acl VALUES (NEW.dst, NEW.src, 1);
       );

/* Remove whitelisted flow when removed form reachability matrix */
CREATE OR REPLACE RULE FW2 AS
       ON DELETE TO rm
       WHERE (SELECT count(*) FROM rm WHERE src = OLD.src AND dst = OLD.dst) = 1 AND
             (OLD.src IN (SELECT * FROM FW_policy_user))
       DO ALSO
          DELETE FROM FW_policy_acl WHERE end2 = OLD.src AND end1 = OLD.dst;

/* Violations - flows installed that are not in the host or node whitelist */
CREATE OR REPLACE VIEW FW_violation AS (
       SELECT fid
       FROM rm
       WHERE FW = 1  AND (src, dst) NOT IN (SELECT end1, end2 FROM FW_policy_acl)
);

/* Repair - remove proposed flows from the reachability matrix */
CREATE OR REPLACE RULE FW_repair AS
       ON DELETE TO FW_violation
       DO INSTEAD
          DELETE FROM rm WHERE fid = OLD.fid;



------------------------------------------------------------
-- SAMPLE CONFIGURATION (for toy_dtp.py topo)
------------------------------------------------------------
/* Same as CLI command (h4's hid=8, h3's hid=7):
 *    fw addflow h4 h3
 */
-- INSERT INTO FW_policy_acl (8,7,1);

/* Same as CLI command:
 *    fw addhost h2
 *    fw addhost h4
 */
-- INSERT INTO FW_policy_user VALUES (6), (8);
