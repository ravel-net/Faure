"""
Flow modification functions for external processes.

Database triggers that install or remove flows in response to insertion
or deletion of rows execute in a separate process from the Ravel CLI
process and the OpenFlow manager.  This module contains functions for
connecting to the OpenFlow manager, which can send flow modification
messages to the switches.
"""

import os
import pickle
import threading
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

import sysv_ipc
from mininet.net import macColonHex, netParse, ipAdd

import ravel.messaging
from ravel.log import logger
from ravel.of import OFPP_FLOOD, OFPFC_ADD, OFPFC_DELETE, OFPFC_DELETE_STRICT
from ravel.profiling import PerfCounter
from ravel.messaging import MsgQueueSender, RpcSender, OvsSender
from ravel.util import Config, append_path, ConnectionType

def connectionFactory(conn):
    """Create a new message sender instance using the specified connection
       conn: a ConnectionType specifying the type of connection to be used"""
    if conn == ConnectionType.Mq:
        return MsgQueueSender(Config.QueueId)
    elif conn == ConnectionType.Rpc:
        return RpcSender(Config.RpcHost, Config.RpcPort)
    elif conn == ConnectionType.Ovs:
        return OvsSender()
    else:
        raise Exception("Unrecognized messaging protocol %s", conn)

def _send_msg(command, flow_id, sw, src_ip, src_mac, dst_ip, dst_mac, outport,
              revoutport):
    pc = PerfCounter("msg_create")
    pc.start()
    conn = connectionFactory(Config.Connection)
    msg1 = OfMessage(command=command,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=src_ip, nw_dst=dst_ip, dl_type=0x0800),
                     actions=[outport])

    msg2 = OfMessage(command=command,
                     priority=10,
                     switch=sw,
                     match=Match(nw_src=dst_ip, nw_dst=src_ip, dl_type=0x0800),
                     actions=[revoutport])

    arp1 = OfMessage(command=command,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=src_mac, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    arp2 = OfMessage(command=command,
                     priority=1,
                     switch=sw,
                     match=Match(dl_src=dst_mac, dl_type=0x0806),
                     actions=[OFPP_FLOOD])

    pc.stop()
    conn.send(msg1)
    conn.send(msg2)
    conn.send(arp1)
    conn.send(arp2)
    conn.send(BarrierMessage(sw.dpid))

def installFlow(flowid, sw, src_ip, src_mac, dst_ip, dst_mac, outport,
                revoutport):
    """Construct a new add-flow message and send to the OpenFlow manager.
       Installs the forward and reverse path
       flowid: the flow id
       sw: an instance of Switch
       src_ip: the source host's IP address as a string
       src_mac: the source host's MAC address as a string
       dst_ip: the destination host's IP address as a string
       dst_mac: the destination host's MAC address as a string
       outport: the outport from sw for the forward flow
       revoutoprt: the outport from sw for the reverse flow"""
    _send_msg(OFPFC_ADD,
              flowid,
              sw,
              src_ip,
              src_mac,
              dst_ip,
              dst_mac,
              outport,
              revoutport)

def removeFlow(flowid, sw, src_ip, src_mac, dst_ip, dst_mac, outport,
               revoutport):
    """Construct a new delete-flow message and send to the OpenFlow manager.
       Removes the forward and reverse path
       flowid: the flow id
       sw: an instance of Switch
       src_ip: the source host's IP address as a string
       src_mac: the source host's MAC address as a string
       dst_ip: the destination host's IP address as a string
       dst_mac: the destination host's MAC address as a string
       outport: the outport from sw for the forward flow
       revoutoprt: the outport from sw for the reverse flow"""
    _send_msg(OFPFC_DELETE_STRICT,
              flowid,
              sw,
              src_ip,
              src_mac,
              dst_ip,
              dst_mac,
              outport,
              revoutport)

class Switch(object):
    "A representation of an OpenFlow switch"

    def __init__(self, name, ip, dpid):
        """name: a Mininet-style name for the switch
           ip: the IP address of the switch, if it is remote
           dpid: the datapath ID of the switch"""
        self.name = name
        self.ip = ip
        self.dpid = dpid

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.dpid)

class Match(object):
    "A match object for an OpenFlow flow modification message"

    def __init__(self, nw_src=None, nw_dst=None,
                dl_src=None, dl_dst=None, dl_type=None):
       """nw_src: the source node's network address
          nw_dst: the destination node's network address
          dl_src: the source node's datalink address
          dl_dst: the destination node's datalink address
          dl_type: the datalink type"""
       self.nw_src = nw_src
       self.nw_dst = nw_dst
       self.dl_src = dl_src
       self.dl_dst = dl_dst
       self.dl_type = dl_type

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "[{0},{1},{2},{3},{4}]".format(self.nw_src,
                                              self.nw_dst,
                                              self.dl_src,
                                              self.dl_dst,
                                              self.dl_type)

class OfMessage(ravel.messaging.ConsumableMessage):
    "A OpenFlow flow modification message"

    def __init__(self, command=None, priority=1, switch=None,
                 match=None, actions=None):
        """command: an OpenFlow flow modification command
           priority: the flow priority
           switch: the switch to send the message
           match: a match for the flow
           actions: a list of ports to forward matching packets"""
        self.command = command
        self.priority = priority
        self.switch = switch
        self.match = match
        self.actions = actions
        if actions is None:
            self.actions = []

    def consume(self, consumer):
        """Consume the message
           consumer: a ravel.of.OfManager instance to consume the message"""
        consumer.sendFlowmod(self)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}: {1} {2}".format(self.command,
                                     self.switch,
                                     self.match)

class BarrierMessage(ravel.messaging.ConsumableMessage):
    """An OpenFlow barrier message"""

    def __init__(self, dpid):
        "dpid: the dpid of the switch to send the barrier message"
        self.dpid = dpid

    def consume(self, consumer):
        """Consume the message
           consumer: a ravel.of.OfManager instance to consume the message"""
        consumer.sendBarrier(self.dpid)
