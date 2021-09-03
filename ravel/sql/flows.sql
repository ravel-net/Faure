------------------------------------------------------------
-- FLOW MODIFICATION FUNCTIONS
------------------------------------------------------------

/* Add flow preprocessing - gather match fields to install a flow
 * in a single switch (a flow with n hops will invoke this function
 * n times)
 * NEW.fid: flow id
 * NEW.sid: id of the switch where the flow is to be installed
 * NEW.pid: host1, the previous-hop node
 * NEW.nid: host2, the next-hop node
 */
CREATE OR REPLACE FUNCTION add_flow_pre ()
RETURNS TRIGGER
AS $$
    DECLARE
        sw_name varchar(16);
        sw_ip varchar(16);
        sw_dpid varchar(16);

        src_id int;
        src_ip varchar(16);
        src_mac varchar(17);

        dst_id int;
        dst_ip varchar(16);
        dst_mac varchar(17);

        outport int;
        revoutport int;

        start_time timestamptz;
        end_time timestamptz;
        diff interval;

    BEGIN
        start_time := clock_timestamp();

        SELECT port INTO outport
               FROM ports
               WHERE sid=NEW.sid AND nid=NEW.nid;

        SELECT port INTO revoutport
               FROM ports
               WHERE sid=NEW.sid AND nid=NEW.pid;

        /* get src, dst host uids */
        SELECT src, dst INTO src_id, dst_id
               FROM rm
               WHERE fid=NEW.fid;

        SELECT name, ip, dpid INTO sw_name, sw_ip, sw_dpid
               FROM switches
               WHERE sid=NEW.sid;

        /* get src, dst addresses */
        SELECT ip, mac INTO src_ip, src_mac
               FROM hosts
               WHERE hid=src_id;

        SELECT ip, mac INTO dst_ip, dst_mac
               FROM hosts
               WHERE hid=dst_id;

        /* for profiling */
        end_time := clock_timestamp();
        diff := (EXTRACT(epoch FROM end_time) - EXTRACT(epoch FROM start_time));

        PERFORM add_flow_fun(NEW.fid,
                             sw_name, sw_ip, sw_dpid,
                             src_ip, src_mac,
                             dst_ip, dst_mac,
                             outport, revoutport,
                             to_char(diff, 'MS.US'));

        return NEW;
    END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;


/* Add flow - proxy for ravel.flow.installFlow
 * flow_id: id of flow to be installed
 * sw_name: switch name (in Mininet)
 * sw_ip: switch IP address (if a physical, remote switch)
 * sw_mac: switch MAC address
 * src_ip: source IP address
 * src_mac: source MAC address
 * dst_ip: destination IP address
 * src_mac: destination MAC address
 * outport: outport on sw_name for the forward flow (src->dst)
 * revoutport: outport on sw_name for the reverse flow (dst->src)
 * diff: time to query for flow fields
 */
CREATE OR REPLACE FUNCTION add_flow_fun (flow_id integer,
       sw_name varchar(16), sw_ip varchar(16), sw_dpid varchar(16),
       src_ip varchar(16), src_mac varchar(17),
       dst_ip varchar(16), dst_mac varchar(17),
       outport integer, revoutport integer,
       diff varchar(16))
RETURNS integer
AS $$
import os
import sys
import time

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.flow import installFlow, Switch
from ravel.profiling import PerfCounter

pc = PerfCounter("db_select", float(diff))
pc.report()
sw = Switch(sw_name, sw_ip, sw_dpid)
installFlow(flow_id, sw, src_ip, src_mac, dst_ip, dst_mac, outport, revoutport)

return 0
$$ LANGUAGE plpythonu VOLATILE SECURITY DEFINER;


/* Add flow trigger - for each per-switch rule, invoke add_flow_pre
 * to install flow in that switch
 */
CREATE TRIGGER add_flow_trigger
       AFTER INSERT ON cf
       FOR EACH ROW
       EXECUTE PROCEDURE add_flow_pre();


/* Delete flow preprocessing - gather match fields to install a flow
 * in a single switch (a flow with n hops will invoke this function
 * n times)
 * OLD.fid: flow id
 * OLD.sid: id of the switch where the flow is to be removed
 * OLD.pid: host1, the previous-hop node
 * OLD.nid: host2, the next-hop node
 */
CREATE OR REPLACE FUNCTION del_flow_pre ()
RETURNS TRIGGER
AS $$
    DECLARE
        sw_name varchar(16);
        sw_ip varchar(16);
        sw_dpid varchar(16);

        src_id int;
        src_ip varchar(16);
        src_mac varchar(17);

        dst_id int;
        dst_ip varchar(16);
        dst_mac varchar(17);

        outport int;
        revoutport int;

        start_time timestamptz;
        end_time timestamptz;
        diff interval;
    BEGIN
        start_time := clock_timestamp();

        SELECT port INTO outport
               FROM ports
               WHERE sid=OLD.sid and nid=OLD.nid;

        SELECT port INTO revoutport
               FROM ports
               WHERE sid=OLD.sid and nid=OLD.pid;

        /* get src, dst host uids */
        SELECT src, dst INTO src_id, dst_id
               FROM rm_delta
               WHERE fid=OLD.fid;

        /* get src, dst addresses */
        SELECT name, ip, dpid INTO sw_name, sw_ip, sw_dpid
               FROM switches
               WHERE sid=OLD.sid;

        /* get src, dst addresses */
        SELECT ip, mac INTO src_ip, src_mac
               FROM hosts
               WHERE hid=src_id;

        SELECT ip, mac INTO dst_ip, dst_mac
               FROM hosts
               WHERE hid=dst_id;

        /* for profiling */
        end_time := clock_timestamp();
        diff := (extract(epoch from end_time) - extract(epoch from start_time));

        PERFORM del_flow_fun(OLD.fid,
                             sw_name, sw_ip, sw_dpid,
                             src_ip, src_mac,
                             dst_ip, dst_mac,
                             outport, revoutport,
                             to_char(diff, 'MS.US'));

        return OLD;
    END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;


/* Delete flow - proxy for ravel.flow.removeFlow
 * flow_id: id of flow to be removed
 * sw_name: switch name (in Mininet)
 * sw_ip: switch IP address (if a physical, remote switch)
 * sw_mac: switch MAC address
 * src_ip: source IP address
 * src_mac: source MAC address
 * dst_ip: destination IP address
 * src_mac: destination MAC address
 * outport: outport on sw_name for the forward flow (src->dst)
 * revoutport: outport on sw_name for the reverse flow (dst->src)
 * diff: time to query for flow fields
 */
CREATE OR REPLACE FUNCTION del_flow_fun (flow_id integer,
       sw_name varchar(16), sw_ip varchar(16), sw_dpid varchar(16),
       src_ip varchar(16), src_mac varchar(17),
       dst_ip varchar(16), dst_mac varchar(17),
       outport integer, revoutport integer,
       diff varchar(16))
RETURNS integer
AS $$
import os
import sys
import time

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.flow import removeFlow, Switch
from ravel.profiling import PerfCounter

pc = PerfCounter("db_select", float(diff))
pc.report()

sw = Switch(sw_name, sw_ip, sw_dpid)
removeFlow(flow_id, sw, src_ip, src_mac, dst_ip, dst_mac, outport, revoutport)

return 0
$$ LANGUAGE plpythonu VOLATILE SECURITY DEFINER;


/* Delete flow trigger - for each per-switch rule, invoke del_flow_pre
 * to delete flow from that switch
 */
CREATE TRIGGER del_flow_trigger
       AFTER DELETE ON cf
       FOR EACH ROW
       EXECUTE PROCEDURE del_flow_pre();
