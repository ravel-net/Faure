"""
Abstraction for communicating between Ravel's processes: the main CLI, the
OpenFlow manager, and the database triggers.
"""

import os
import pickle
import threading
import time
import xmlrpclib
import sysv_ipc
from SimpleXMLRPCServer import SimpleXMLRPCServer

import ravel.profiling
from ravel.log import logger
from ravel.of import OFPP_FLOOD, OFPFC_ADD, OFPFC_DELETE, OFPFC_DELETE_STRICT

def clear_queue(queue_id):
    try:
        mq = sysv_ipc.MessageQueue(queue_id,
                                   sysv_ipc.IPC_CREAT,
                                   mode=0777)
        mq.remove()
    except sysv_ipc.PermissionsError:
        logger.warning("could not clear clear message queue {0}"
                       .format(queue_id))

class ConsumableMessage(object):
    "A consumable message"

    def consume(self, consumer):
        """Consume the message
           consumer: an object containing a function to consume the message"""
        pass

class MessageSender(object):
    "A message sender"

    def send(self, msg):
        """Send the specified message
           msg: the message to send"""
        pass

class MessageReceiver(object):
    "A message receiver"

    def start(self):
        "Start a new thread to receive messages"
        pass

    def stop(self, event=None):
        """Stop the receiver thread
           event: an optional quit message"""
        pass

class MsgQueueSender(MessageSender):
    "A message queue-based message sender"

    def __init__(self, queue_id):
        "queue_id: the integer id of the queue to be used"
        self.queue_id = queue_id
        pc = ravel.profiling.PerfCounter("mq_connect")
        pc.start()
        try:
            self.mq = sysv_ipc.MessageQueue(self.queue_id,
                                            mode=0777)
        except sysv_ipc.ExistentialError, e:
            logger.warning("queue {0} does not exist: {1}"
                           .format(self.queue_id, e))
            self.mq = sysv_ipc.MessageQueue(self.queue_id,
                                            sysv_ipc.IPC_CREAT,
                                            mode=0777)
        pc.stop()

    def send(self, msg):
        """Send the specified message
           msg: the message to send"""
        pc = ravel.profiling.PerfCounter("mq_send")
        pc.start()
        logger.debug("mq: sending message %s", msg)
        self.mq.send(pickle.dumps(msg))
        pc.stop()

class MsgQueueReceiver(MessageReceiver):
    "A message queue-based message receiver"

    def __init__(self, queue_id, consumer=None):
        """queue_id: the integer id of the queue to receive messages from
           consumer: the consuming object for received messages"""
        self.queue_id = queue_id
        self.consumer = consumer
        self.running = False
        # clear message queue
        clear_queue(self.queue_id)
        self.mq = sysv_ipc.MessageQueue(self.queue_id,
                                        sysv_ipc.IPC_CREAT,
                                        mode=0777)

    def start(self):
        "Start a new thread to receive messages"
        logger.debug("mq_receiver starting")
        self.running = True
        self.t = threading.Thread(target=self._run)
        self.t.start()

    def _run(self):
        while self.running:
            s,_ = self.mq.receive()
            msg = s.decode()
            obj = pickle.loads(msg)
            logger.debug("mq: received message %s", msg)
            if obj is not None:
                obj.consume(self.consumer)

    def stop(self, event=None):
        """Stop the receiver thread
           event: an optional quit message"""
        self.running = False
        self.mq.send(pickle.dumps(None))

class RpcSender(MessageSender):
    "A remote procedure call-based message sender"

    def __init__(self, host, port):
        """host: the hostname or IP address of the RPC server
           port: the port for the RPC server"""
        self.addr = "http://{0}:{1}".format(host, port)
        pc = ravel.profiling.PerfCounter("rpc_connect")
        pc.start()
        self.proxy = xmlrpclib.ServerProxy(self.addr, allow_none=True)
        pc.stop()

    def send(self, msg):
        """Send the specified message
           msg: the message to send"""
        logger.debug("rpc: sending message %s", msg)
        pc = ravel.profiling.PerfCounter("rpc_send")
        pc.start()
        self.proxy.client_send(pickle.dumps(msg))
        pc.stop()

class RpcReceiver(MessageReceiver):
    "A remote procedure call-based message receiver"

    def __init__(self, host, port, consumer=None):
        """host: the hostname or IP address of the RPC server
           port: the port for the RPC server
           consumer: the consuming object for received messages"""
        self.host = host
        self.port = port
        self.consumer = consumer
        self.server = SimpleXMLRPCServer((host, port),
                                         logRequests=False,
                                         allow_none=True)
        self.server.register_function(self._client_send, "client_send")
        self.msg = None

    def _client_send(self, msg):
        obj = pickle.loads(msg)
        logger.debug("rpc: received message %s", msg)
        if obj is not None:
            print "CONSUMING MESSAGE", obj
            obj.consume(self.consumer)

    def start(self):
        "Start a new thread to receive messages"
        logger.debug("rpc_receiver starting")
        self.running = True
        self.t = threading.Thread(target=self._run)
        self.t.start()

    def _run(self):
        while self.running:
            self.server.handle_request()

    def stop(self, event=None):
        """Stop the receiver thread
           event: an optional quit message"""
        self.running = False
        addr = "http://{0}:{1}".format(self.host, self.port)
        self.proxy = xmlrpclib.ServerProxy(addr, allow_none=True)
        self.proxy.client_send(pickle.dumps(None))

class OvsSender(MessageSender):
    "A message sender using ovs-ofctl to communicate with switches"

    command = "/usr/bin/sudo /usr/bin/ovs-ofctl"
    subcmds = { OFPFC_ADD : "add-flow",
                OFPFC_DELETE : "del-flows",
                OFPFC_DELETE_STRICT : "--strict del-flows"
    }

    def __init__(self):
        pass

    def send(self, msg):
        """Send the specified OpenFlow message
           msg: the message to send"""

        # don't need to handle barrier messages
        if not hasattr(msg, 'command'):
            return

        pc = ravel.profiling.PerfCounter("ovs_send")
        pc.start()

        subcmd = OvsSender.subcmds[msg.command]

        # TODO: this is different for remote switches (ie, on physical network)
        dest = msg.switch.name

        params = []
        if msg.match.nw_src is not None:
            params.append("nw_src={0}".format(msg.match.nw_src))
        if msg.match.nw_dst is not None:
            params.append("nw_dst={0}".format(msg.match.nw_dst))
        if msg.match.dl_src is not None:
            params.append("dl_src={0}".format(msg.match.dl_src))
        if msg.match.dl_dst is not None:
            params.append("dl_dst={0}".format(msg.match.dl_dst))
        if msg.match.dl_type is not None:
            params.append("dl_type={0}".format(msg.match.dl_type))

        params.append("priority={0}".format(msg.priority))
        actions = ["flood" if a == OFPP_FLOOD else str(a) for a in msg.actions]

        if msg.command == OFPFC_ADD:
            params.append("action=output:" + ",".join(actions))

        paramstr = ",".join(params)
        cmd = "{0} {1} {2} {3}".format(OvsSender.command,
                                       subcmd,
                                       dest,
                                       paramstr)
        ret = os.system(cmd)
        pc.stop()
        return ret
