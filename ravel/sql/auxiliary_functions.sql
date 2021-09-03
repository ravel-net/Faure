CREATE EXTENSION IF NOT EXISTS intarray;

CREATE OR REPLACE FUNCTION next_id(tabname VARCHAR, colname VARCHAR)
    RETURNS INTEGER AS
$$
DECLARE
    numAray INT[];
    numItr INT;
    cnt INT;
BEGIN
    EXECUTE format('SELECT COUNT(*) FROM %I', tabname) INTO cnt;
    IF cnt  = 0 THEN
        RETURN 1;
    ELSE
        EXECUTE format('SELECT ARRAY_AGG(%I) FROM %I',colname, tabname) INTO numAray;
        FOR numItr IN 1..icount(numAray) LOOP
            IF idx(numAray, numItr) = 0 THEN
                RETURN numItr;
            END IF;
        END LOOP;
        RETURN icount(numAray) + 1;
    END IF;
END;
$$
LANGUAGE PLPGSQL;

CREATE OR REPLACE FUNCTION pv_to_cf_entries(pv INT[])
RETURNS TABLE (
    pid INT,
    sid INT,
    nid INT
)
AS
$$
DECLARE
    pvidx INT;
BEGIN
    IF icount(pv) > 1 THEN
        pid := NULL;
        sid := pv[1];
        nid := pv[2];
        RETURN NEXT;
        IF icount(pv) > 2 THEN
            FOR pvidx IN 2..icount(pv) - 1
            LOOP
                pid := pv[pvidx-1];
                sid := pv[pvidx];
                nid := pv[pvidx+1];
                RETURN NEXT;
            END LOOP;
        END IF;
    END IF;
END;
$$
LANGUAGE PLPGSQL;

CREATE OR REPLACE FUNCTION my_warning(msg VARCHAR)
RETURNS VOID AS
$$
BEGIN
    RAISE NOTICE '%', msg;
END;
$$
LANGUAGE PLPGSQL;