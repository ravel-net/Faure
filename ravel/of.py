"""
Classes for the communicating with and controlling the underlying OpenFlow
network.
"""

import os
import re
import signal
import subprocess
import sys
import time

import ravel.util
from ravel.log import logger

OFPC_FLOW_STATS = 1
OFPC_TABLE_STATS = 2
OFPC_PORT_STATS = 4

OFPFC_ADD = 0
OFPFC_MODIFY = 1
OFPFC_MODIFY_STRICT = 2
OFPFC_DELETE = 3
OFPFC_DELETE_STRICT = 4

OFPP_MAX = 65280
OFPP_IN_PORT = 65528
OFPP_TABLE = 65529
OFPP_NORMA = 65530
OFPP_FLOOD = 65531
OFPP_ALL = 65532
OFPP_CONTROLLER = 65533
OFPP_LOCAL = 65534
OFPP_NONE = 65535

def preexec_fn():
    # don't forward signals to child process
    # we need this when starting a Pox subprocess, so that SIGINTs from the CLI
    # aren't forwarded to Pox, causing it to terminate early
    os.setpgrp()

class OfManager(object):
    """Manange communication with an OpenFlow controller.  The manager receives
       flow modification messages from the database triggers on changes to
       database tables.  The underlying controller implementation
       serves as a proxy for sending the switches messages and receiving
       link status updates from the network"""

    def __init__(self):
        self.receiver = []

    def registerReceiver(self, receiver):
        """Add a new message receiver
           receiver: a ravel.messaging.MessageReceiver instance"""
        self.receiver.append(receiver)

    def stop(self):
        "Stop the manager (and stop receiving messages from the database)"
        for receiver in self.receiver:
            receiver.stop()

    def isRunning(self):
        "returns: true if the manager is running"
        pass

    def sendBarrier(self, dpid):
        """Send a barrier to the underlying controller implementation
           dpid: the datapath ID of the switch to receive the message"""
        pass

    def sendFlowmod(self, msg):
        """Send a flow modification to the underlying controller implementation
           msg: a ravel.flow.OfMessage instance"""
        pass

    def requestStats(self):
        """Send the switches a port stats request"""
        pass

class PoxInstance(object):
    "A representation of a Pox process"

    def __init__(self, app):
        "app: the Pox application to be run"
        self.app = app
        self.proc = None

    @classmethod
    def is_running(cls):
        """Check if this or another Pox instance is running
           returns: true if pox is running, false otherwise"""
        output = os.popen("ps awx").read()
        if "pox.py" in output:
            return True
        else:
            return False

    def start(self, cargs=None):
        """Start the Pox process
           cargs: arguments to pass to the controller"""
        pox = os.path.join(ravel.util.Config.PoxDir, "pox.py")
        if not os.path.exists(pox):
            logger.error("cannot find pox.py at: {0}. "
                         "Is PoxDir set correctly in ravel.cfg?"
                         .format(pox))
            sys.exit(0)

        if cargs is None:
            cargs = ["log.level",
                     "--DEBUG",
                     "openflow.of_01",
                     "--port={0}".format(ravel.util.Config.PoxPort),
                     self.app,
                     "openflow.discovery"]

        ravel.util.append_path(ravel.util.resource_file())
        env = os.environ.copy()
        env["PYTHONPATH"] = ":".join(sys.path)
        logger.debug("pox with params: %s", " ".join(cargs))
        self.proc = subprocess.Popen([pox] + cargs,
                                     env=env,
                                     preexec_fn = preexec_fn,
                                     stdout=open("/tmp/pox.log", "wb"),
                                     stderr=open("/tmp/pox.err", "wb"))

    def stop(self):
        "Stop the Pox process"
        if self.proc is not None:
            os.kill(self.proc.pid, signal.SIGINT)
