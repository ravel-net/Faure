#!/usr/bin/env python
"""
Pox-based OpenFlow manager
"""

import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.recoco import *
from pox.lib.revent import *
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_dpid

from ravel.util import Config
from ravel.db import RavelDb
from ravel.profiling import PerfCounter
from ravel.messaging import MsgQueueReceiver, RpcReceiver
from ravel.of import OfManager

log = core.getLogger()

class PoxManager(OfManager):
    "Pox-based OpenFlow manager"

    def __init__(self, log, dbname, dbuser):
        super(PoxManager, self).__init__()
        self.db = RavelDb(dbname, dbuser, None, reconnect=True)
        self.log = log
        self.datapaths = {}
        self.flowstats = []
        self.perfcounter = PerfCounter("sw_delay")
        self.dpid_cache = {}

        core.openflow.addListeners(self, priority=0)
        self.log.info("ravel: starting pox manager")

        def startup():
            self.log.info("registering handlers")
            core.openflow_discovery.addListeners(self)

        core.call_when_ready(startup, ("openflow", "openflow_discovery"))

    def update_switch_cache(self):
        self.db.cursor.execute("SELECT * FROM switches;")
        result = self.db.cursor.fetchall()
        for sw in result:
            self.dpid_cache[sw[1]] = { 'sid' : sw[0],
                                       'dpid' : sw[1],
                                       'ip' : sw[2],
                                       'mac': sw[3],
                                       'name': sw[4] }

    def _handle_ConnectionDown(self, event):
        dpid = "%0.16x" % event.dpid
        self.update_switch_cache()
        del self.datapaths[event.dpid]
        self.db.cursor.execute("DELETE FROM switches WHERE dpid='{0}';"
                               .format(dpid))
        self.log.info("ravel: dpid {0} removed".format(event.dpid))

    def _handle_ConnectionUp(self, event):
        dpid = "%0.16x" % event.dpid
        self.update_switch_cache()
        self.datapaths[event.dpid] = event.connection

        self.db.cursor.execute("SELECT COUNT(*) FROM switches WHERE dpid='{0}';"
                               .format(dpid))
        count = self.db.cursor.fetchall()[0][0]

        if count > 0:
            # switch already in db
            pass
        elif dpid in self.dpid_cache:
            sw = self.dpid_cache[dpid]
            self.db.cursor.execute("INSERT INTO switches (sid, dpid, ip, mac, name) "
                                   "VALUES ({0}, '{1}', '{2}', '{3}', '{4}');".format(
                                   sw['sid'], sw['dpid'], sw['ip'], sw['mac'], sw['name']))
        else:
            sid = len(self.dpid_cache) + 1
            name = "s{0}".format(sid)
            self.db.cursor.execute("INSERT INTO switches (sid, dpid, name) VALUES "
                                   "({0}, '{1}', '{2}')".format(sid, dpid, name))

        self.log.info("ravel: dpid {0} online".format(event.dpid))
        self.log.info("ravel: online dpids: {0}".format(self.datapaths))

    def _handle_LinkEvent(self, event):
        dpid1 = "%0.16x" % event.link.dpid1
        dpid2 = "%0.16x" % event.link.dpid2
        port1 = event.link.port1
        port2 = event.link.port2
        sid1 = self.dpid_cache[dpid1]['sid']
        sid2 = self.dpid_cache[dpid2]['sid']

        if event.removed:
            self.db.cursor.execute("UPDATE tp SET isactive=0 WHERE "
                                   " (sid={0} AND nid={1}) OR "
                                   " (sid={1} AND nid={0});"
                                   .format(sid1, sid2))

            self.log.info("Link down {0}".format(event.link))
        elif event.added:
            # does the forward link exist in Postgres?
            self.db.cursor.execute("SELECT COUNT(*) FROM tp WHERE "
                                   "sid={0} AND nid={1};"
                                   .format(sid1, sid2))
            count = self.db.cursor.fetchall()[0][0]
            if count == 0:
                self.db.cursor.execute("INSERT INTO tp (sid, nid, ishost, isactive) "
                                       "VALUES ({0}, {1}, 0, 1);"
                                       .format(sid1, sid2))
                self.db.cursor.execute("INSERT INTO ports (sid, nid, port) VALUES "
                                       "({0}, {1}, {2});"
                                       .format(sid1, sid2, port1))

            # does the reverse link already exist in Postgres?
            self.db.cursor.execute("SELECT COUNT(*) FROM tp WHERE "
                                   "sid={0} AND nid={1};"
                                   .format(sid2, sid1))
            count = self.db.cursor.fetchall()[0][0]
            if count == 0:
                self.db.cursor.execute("INSERT INTO tp (sid, nid, ishost, isactive) "
                                       "VALUES ({0}, {1}, 0, 1);"
                                       .format(sid2, sid1))
                self.db.cursor.execute("INSERT INTO ports (sid, nid, port) VALUES "
                                       "({0}, {1}, {2});"
                                       .format(sid2, sid1, port2))
            self.log.info("Link up {0}".format(event.link))

    def _handle_BarrierIn(self, event):
        self.perfcounter.stop()
        self.log.debug("received barrier")

    def _handle_FlowStatsReceived(self, event):
        self.log.info("ravel: flow stat received dpid={0}, len={1}".format(
            event.connection.dpid, len(event.stats)))
        for stat in event.stats:
            self.log.info("   flow: nw_src={0}, nw_dst={1}".format(
                stat.match.nw_src, stat.match.nw_dst))

    def requestStats(self):
        "Send all switches a flow statistics request"
        self.flowstats = []
        for connection in list(core.openflow._connections.values()):
            connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))

        self.log.debug("ravel: sent {0} flow stats requests".format(
            len(core.openflow._connections)))

        return True

    def sendBarrier(self, dpid):
        """Send a barrier message
           dpid: datapath id of the switch to receive the barrier"""
        dpid = int(dpid)
        if dpid in self.datapaths:
            dp = self.datapaths[dpid]
            msg = of.ofp_barrier_request()
            dp.send(msg)
            self.perfcounter.start()
            self.log.debug("dpid {0} sent barrier".format(dpid))
        else:
            self.log.debug("dpid {0} not in datapath list".format(dpid))
        return True

    def registerReceiver(self, receiver):
        """Register a new message receiver
           receiver: a ravel.messaging.MessageReceiver object"""
        self.log.info("registering receiver")
        self.receiver.append(receiver)
        receiver.start()
        core.addListener(pox.core.GoingDownEvent, receiver.stop)

    def isRunning(self):
        "returns: true if the controller is running, false otherwise"
        return core.running

    def mk_msg(self, flow):
        """Create a Pox flowmod message from ravel.flow.OfMessage
           flow: a ravel.flow.OfMessage object"""
        msg = of.ofp_flow_mod()
        msg.command = int(flow.command)
        msg.priority = int(flow.priority)
        msg.match = of.ofp_match()
        if flow.match.dl_type is not None:
            msg.match.dl_type = int(flow.match.dl_type)
        if flow.match.nw_src is not None:
            msg.match.nw_src = IPAddr(flow.match.nw_src)
        if flow.match.nw_dst is not None:
            msg.match.nw_dst = IPAddr(flow.match.nw_dst)
        if flow.match.dl_src is not None:
            msg.match.dl_src = EthAddr(flow.match.dl_src)
        if flow.match.dl_dst is not None:
            msg.match.dl_dst = EthAddr(flow.match.dl_dst)
        for outport in flow.actions:
            msg.actions.append(of.ofp_action_output(port=int(outport)))
        return msg

    def send(self, dpid, msg):
        """Send a message to a switch
           dpid: datapath id of the switch
           msg: OpenFlow message"""
        self.log.debug("ravel: flow mod dpid={0}".format(dpid))
        if dpid in self.datapaths:
            dp = self.datapaths[dpid]
            dp.send(msg)
        else:
            self.log.debug("dpid {0} not in datapath list".format(dpid))

    def sendFlowmod(self, flow):
        """Send a flow modification message
           flow: the flow modification message to send"""
        dpid = int(flow.switch.dpid)
        self.send(dpid, self.mk_msg(flow))

def launch():
    "Start the OpenFlow manager and message receivers"
    ctrl = PoxManager(log, Config.DbName, Config.DbUser)
    mq = MsgQueueReceiver(Config.QueueId, ctrl)
    ctrl.registerReceiver(mq)
    rpc = RpcReceiver(Config.RpcHost, Config.RpcPort, ctrl)
    ctrl.registerReceiver(rpc)
    core.register("ravelcontroller", ctrl)
