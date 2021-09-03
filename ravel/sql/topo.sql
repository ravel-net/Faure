------------------------------------------------------------
-- TOPOLOGY MODIFICATION FUNCTIONS
------------------------------------------------------------

/* Add a new link in the network provider
 * NEW.sid: switch end of the link
 * NEW.nid: other end of the link (host or switch)
 * NEW.isHost: if the node connected to the switch is a host
 */
CREATE OR REPLACE FUNCTION add_link_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import AddLinkMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["new"]["sid"]
nid = TD["new"]["nid"]
isHost = TD["new"]["ishost"]
isActive = TD["new"]["ishost"]

msg = AddLinkMessage(sid, nid, isHost, isActive)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


/* Add link trigger */
CREATE TRIGGER add_link_trigger
       AFTER INSERT ON tp
       FOR EACH ROW
       EXECUTE PROCEDURE add_link_fun();


/* Remove a new link from the network provider
 * OLD.sid: switch end of the link
 * OLD.nid: other end of the link (host or switch)
 */
CREATE OR REPLACE FUNCTION del_link_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import RemoveLinkMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["old"]["sid"]
nid = TD["old"]["nid"]

msg = RemoveLinkMessage(sid, nid)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


/* Delete link trigger */
CREATE TRIGGER del_link_trigger
       AFTER DELETE ON tp
       FOR EACH ROW
       EXECUTE PROCEDURE del_link_fun();


/* Add a new switch in the network provider
 * NEW.sid: switch id
 * NEW.name: switch name (in Mininet)
 * NEW.dpid: datapath id
 * NEW.ip: switch IP address (if a physical, remote switch)
 * NEW.mac: switch MAC address
 */
CREATE OR REPLACE FUNCTION add_switch_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import AddSwitchMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["new"]["sid"]
name = TD["new"]["name"]
dpid = TD["new"]["dpid"]
ip = TD["new"]["ip"]
mac = TD["new"]["mac"]

msg = AddSwitchMessage(sid, name, dpid, ip, mac)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


/* Add switch trigger */
CREATE TRIGGER add_switch_trigger
       AFTER INSERT ON switches
       FOR EACH ROW
       EXECUTE PROCEDURE add_switch_fun();


/* Remove a new switch from the network provider
 * OLD.sid: switch id
 * OLD.name: switch name (in Mininet)
 */
CREATE OR REPLACE FUNCTION del_switch_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import RemoveSwitchMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

sid = TD["old"]["sid"]
name = TD["old"]["name"]

msg = RemoveSwitchMessage(sid, name)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


/* Delete switch trigger */
CREATE TRIGGER del_switch_trigger
       AFTER DELETE ON switches
       FOR EACH ROW
       EXECUTE PROCEDURE del_switch_fun();


/* Add a new host in the network provider
 * NEW.hid: host id
 * NEW.ip: host's IP address
 * NEW.mac: host's MAC address
 * NEW.name: hostname (in Mininet)
 */
CREATE OR REPLACE FUNCTION add_host_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import AddHostMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

hid = TD["new"]["hid"]
name = TD["new"]["name"]
ip = TD["new"]["ip"]
mac = TD["new"]["mac"]

msg = AddHostMessage(hid, name, ip, mac)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


/* Add host trigger */
CREATE TRIGGER add_host_trigger
       AFTER INSERT ON hosts
       FOR EACH ROW
       EXECUTE PROCEDURE add_host_fun();


/* Remove a  host from the network provider
 * OLD.hid: host id
 * OLD.name: hostname (in Mininet)
 */
CREATE OR REPLACE FUNCTION del_host_fun ()
RETURNS TRIGGER
AS $$
import os
import sys

if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
sys.path.append("/home/ravel/ravel")

from ravel.network import RemoveHostMessage, NetworkProvider
from ravel.messaging import MsgQueueSender

hid = TD["old"]["hid"]
name = TD["old"]["name"]

msg = RemoveHostMessage(hid, name)
sender = MsgQueueSender(NetworkProvider.QueueId)
sender.send(msg)

return None;
$$ LANGUAGE 'plpythonu' VOLATILE SECURITY DEFINER;


/* Delete host trigger */
CREATE TRIGGER del_host_trigger
       AFTER DELETE ON hosts
       FOR EACH ROW
       EXECUTE PROCEDURE del_host_fun();
