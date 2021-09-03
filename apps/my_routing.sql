DROP TABLE IF EXISTS rt_violation CASCADE;
CREATE TABLE rt_violation
(
    fid INT,
    src INT,
    dst INT,
    status INT,/*1: missing path, 2: wild path, 3: broken path, -1: a cancelled out entry*/
    PRIMARY KEY(fid, status)
);

CREATE OR REPLACE FUNCTION get_my_routing_violation ()
RETURNS TABLE(fid INT, src INT, dst INT, status INT) AS $$
SELECT * FROM rt_violation ORDER BY status DESC;
$$ LANGUAGE SQL;

CREATE OR REPLACE VIEW my_routing_violation AS SELECT * FROM get_my_routing_violation ();

CREATE OR REPLACE FUNCTION my_routing_repair_fun() RETURNS TRIGGER AS
$$
BEGIN   
    PERFORM my_routing_task();
    RETURN NULL;
END;
$$
LANGUAGE PLPGSQL;

DROP TRIGGER IF EXISTS my_routing_repair ON my_routing_violation;
CREATE TRIGGER my_routing_repair INSTEAD OF DELETE ON my_routing_violation
FOR EACH ROW
EXECUTE PROCEDURE my_routing_repair_fun();


CREATE OR REPLACE FUNCTION rm_update_to_rt_fun() RETURNS TRIGGER AS
$$
BEGIN
    IF EXISTS (SELECT * FROM rt_violation WHERE fid = NEW.fid AND status = 1) THEN /*a traffic request is updated before a path is installed*/
        UPDATE rt_violation SET src = NEW.src, dst = NEW.dst WHERE fid = NEW.fid AND status = 1;
    ELSE /*update an existing flow*/
        INSERT INTO rt_violation VALUES(NEW.fid, NEW.src, NEW.dst, 1), (OLD.fid, OLD.src, OLD.dst, 2);
    END IF;
    RETURN NULL;
END;
$$
LANGUAGE PLPGSQL;

DROP TRIGGER IF EXISTS rm_update_to_rt ON my_rm;
CREATE TRIGGER rm_update_to_rt AFTER UPDATE ON my_rm
FOR EACH ROW WHEN (OLD IS DISTINCT FROM NEW)
EXECUTE PROCEDURE rm_update_to_rt_fun();

CREATE OR REPLACE FUNCTION rm_insert_to_rt_fun() RETURNS TRIGGER AS
$$
BEGIN
    IF EXISTS (SELECT * FROM rt_violation WHERE fid = NEW.fid AND src = NEW.src AND dst = NEW.dst AND status = 2) THEN /*a flow is deleted and then added back*/
        UPDATE rt_violation SET status = -1 WHERE fid = NEW.fid AND status = 2;
    ELSE
        INSERT INTO rt_violation VALUES(NEW.fid, NEW.src, NEW.dst, 1);
    END IF;
    RETURN NULL;
END;
$$
LANGUAGE PLPGSQL;

DROP TRIGGER IF EXISTS rm_insert_to_rt ON my_rm;
CREATE TRIGGER rm_insert_to_rt AFTER INSERT ON my_rm
FOR EACH ROW
EXECUTE PROCEDURE rm_insert_to_rt_fun();

CREATE OR REPLACE FUNCTION rm_delete_to_rt_fun() RETURNS TRIGGER AS
$$
BEGIN
    IF EXISTS (SELECT * FROM rt_violation WHERE fid = OLD.fid AND status = 1) THEN /*delete a new traffic request or an updated flow*/
        UPDATE rt_violation SET status = -1 WHERE fid = OLD.fid AND status = 1;
    ELSE
        INSERT INTO rt_violation VALUES(OLD.fid, OLD.src, OLD.dst, 2);
    END IF;
    RETURN NULL;
END;
$$
LANGUAGE PLPGSQL;

DROP TRIGGER IF EXISTS rm_delete_to_rt ON my_rm;
CREATE TRIGGER rm_delete_to_rt AFTER DELETE ON my_rm
FOR EACH ROW
EXECUTE PROCEDURE rm_delete_to_rt_fun();

CREATE OR REPLACE FUNCTION cf_update_to_rt_fun() RETURNS TRIGGER AS
$$
BEGIN
    raise warning 'update on cf is not allowed!';
    RETURN NULL;
END;
$$
LANGUAGE PLPGSQL;

DROP TRIGGER IF EXISTS cf_update_to_rt ON cf;
CREATE TRIGGER cf_update_to_rt BEFORE UPDATE ON cf
FOR EACH STATEMENT
EXECUTE PROCEDURE cf_update_to_rt_fun();

CREATE OR REPLACE FUNCTION cf_delete_to_rt_fun() RETURNS TRIGGER AS
$$
BEGIN
    IF NOT EXISTS(SELECT fid FROM rt_violation WHERE fid = OLD.fid AND status = 2 OR status = 3) THEN
        INSERT INTO rt_violation VALUES(OLD.fid, NULL, NULL, 3);
    END IF;
    RETURN NULL;
END;
$$
LANGUAGE PLPGSQL;

DROP TRIGGER IF EXISTS cf_delete_to_rt ON cf;
CREATE TRIGGER cf_delete_to_rt AFTER DELETE ON cf
FOR EACH ROW 
EXECUTE PROCEDURE cf_delete_to_rt_fun();

CREATE OR REPLACE FUNCTION rt_repair_fun() RETURNS TRIGGER AS
$$
#variable_conflict use_variable
DECLARE
    pv INT[];
BEGIN
    IF OLD.status = 1 THEN /*missing path*/
        SELECT array_agg(node) INTO pv FROM pgr_dijkstra('SELECT 1 AS id,
                                                            sid AS source,
                                                            nid AS target,
                                                            1.0::float8 AS cost
                                                        FROM tp
                                                        WHERE isactive = 1', OLD.src, OLD.dst,FALSE);
        IF pv IS NULL THEN
            raise notice 'No path exists between % and %', OLD.src, OLD.dst;
            DELETE FROM my_rm WHERE fid = OLD.fid;
        ELSE
            INSERT INTO cf (SELECT OLD.fid, * FROM pv_to_cf_entries(pv));
        END IF;
    ELSEIF OLD.status = 2 THEN /*wild path*/
        DELETE FROM cf WHERE fid = OLD.fid;
    ELSEIF OLD.status = 3 THEN /*broken path*/
        DELETE FROM my_rm WHERE fid = OLD.fid;
    ELSE
        raise warning '% is a invalid rt violation status!', OLD.status;
    END IF;
    RETURN OLD;
END;
$$
LANGUAGE PLPGSQL;

DROP TRIGGER IF EXISTS rt_repair ON rt_violation;
CREATE TRIGGER rt_repair BEFORE DELETE ON rt_violation
FOR EACH ROW WHEN (OLD.status != -1)
EXECUTE PROCEDURE rt_repair_fun();

CREATE OR REPLACE FUNCTION my_routing_task()
    RETURNS void AS
$$
BEGIN
    DELETE FROM rt_violation WHERE status = 3;
    DELETE FROM rt_violation WHERE status = 2;
    DELETE FROM rt_violation WHERE status = 1;
    DELETE FROM rt_violation WHERE status = -1;
END;
$$
LANGUAGE PLPGSQL;

CREATE OR REPLACE FUNCTION load_rt() RETURNS VOID AS
$$
BEGIN
    TRUNCATE rt_violation;
    
    DROP TRIGGER IF EXISTS rm_update_to_rt ON my_rm;
    CREATE TRIGGER rm_update_to_rt AFTER UPDATE ON my_rm
    FOR EACH ROW WHEN (OLD IS DISTINCT FROM NEW)
    EXECUTE PROCEDURE rm_update_to_rt_fun();

    DROP TRIGGER IF EXISTS rm_insert_to_rt ON my_rm;
    CREATE TRIGGER rm_insert_to_rt AFTER INSERT ON my_rm
    FOR EACH ROW
    EXECUTE PROCEDURE rm_insert_to_rt_fun();

    DROP TRIGGER IF EXISTS rm_delete_to_rt ON my_rm;
    CREATE TRIGGER rm_delete_to_rt AFTER DELETE ON my_rm
    FOR EACH ROW
    EXECUTE PROCEDURE rm_delete_to_rt_fun();

    DROP TRIGGER IF EXISTS cf_update_to_rt ON cf;
    CREATE TRIGGER cf_update_to_rt BEFORE UPDATE ON cf
    FOR EACH STATEMENT
    EXECUTE PROCEDURE cf_update_to_rt_fun();

    DROP TRIGGER IF EXISTS cf_delete_to_rt ON cf;
    CREATE TRIGGER cf_delete_to_rt AFTER DELETE ON cf
    FOR EACH ROW 
    EXECUTE PROCEDURE cf_delete_to_rt_fun();

    DROP TRIGGER IF EXISTS rt_repair ON rt_violation;
    CREATE TRIGGER rt_repair BEFORE DELETE ON rt_violation
    FOR EACH ROW EXECUTE PROCEDURE rt_repair_fun();
END;
$$
LANGUAGE PLPGSQL;

CREATE OR REPLACE FUNCTION unload_rt() RETURNS VOID AS
$$
BEGIN
    DROP TRIGGER IF EXISTS rm_update_to_rt ON my_rm;

    DROP TRIGGER IF EXISTS rm_insert_to_rt ON my_rm;

    DROP TRIGGER IF EXISTS rm_delete_to_rt ON my_rm;

    DROP TRIGGER IF EXISTS cf_update_to_rt ON cf;

    DROP TRIGGER IF EXISTS cf_delete_to_rt ON cf;

    DROP TRIGGER IF EXISTS rt_repair ON rt_violation;
END;
$$
LANGUAGE PLPGSQL;
