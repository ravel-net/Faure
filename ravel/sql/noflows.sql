------------------------------------------------------------
-- FLOW MODIFICATION FUNCTIONS
------------------------------------------------------------

/* When running without network provider (e.g., Mininet), remove
   flow triggers
*/

DROP FUNCTION IF EXISTS add_flow_pre() CASCADE;

DROP FUNCTION IF EXISTS add_flow_fun(flow_id integer,
       sw_name varchar(16), sw_ip varchar(16), sw_dpid varchar(16),
       src_ip varchar(16), src_mac varchar(17),
       dst_ip varchar(16), dst_mac varchar(17),
       outport integer, revoutport integer,
       diff varchar(16)) CASCADE;

DROP TRIGGER IF EXISTS add_flow_trigger ON cf CASCADE;

DROP FUNCTION IF EXISTS del_flow_pre() CASCADE;

DROP FUNCTION IF EXISTS del_flow_fun (flow_id integer,
       sw_name varchar(16), sw_ip varchar(16), sw_dpid varchar(16),
       src_ip varchar(16), src_mac varchar(17),
       dst_ip varchar(16), dst_mac varchar(17),
       outport integer, revoutport integer,
       diff varchar(16)) CASCADE;

DROP TRIGGER IF EXISTS del_flow_trigger ON cf CASCADE;
