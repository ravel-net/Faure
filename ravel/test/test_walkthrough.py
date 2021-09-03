#!/usr/bin/env python

import os
import pexpect
import sys
import time
import unittest
from runner import addRavelPath

addRavelPath()

from ravel.util import resource_file

class testCommands(unittest.TestCase):
    ravelCmd = "python {0} --topo single,3".format(resource_file("ravel.py"))

    # Part 1 - Startup Options
    def testStartup(self):
        cmd = "python {0} ".format(resource_file("ravel.py"))
        p = pexpect.spawn(cmd + "--help")
        p.expect("Usage")
        p.sendeof()

        time.sleep(1)
        p = pexpect.spawn(cmd + "--topo=single,2")
        p.expect("ravel>")
        p.sendline("exit")
        p.sendeof()

        time.sleep(1)
        p = pexpect.spawn(cmd + "--topo=single,2 --onlydb")
        p.expect("ravel>")
        p.sendline("exit")
        p.sendeof()

        time.sleep(1)
        p = pexpect.spawn(cmd + "--topo=single,2 --verbosity=debug")
        p.expect("DEBUG")
        p.sendline("exit")
        p.sendeof()
        time.sleep(1)

    # Part 2 - Ravel Commands
    def testCommands(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")
        p.sendline("help")
        p.expect("Commands")

        p.sendline("p SELECT * FROM hosts;")
        p.expect("hid")

        p.sendline("stat")
        p.expect("app path")

        p.sendline("apps")
        p.expect("offline")

        p.sendline("exit")
        p.sendeof()
        time.sleep(1)

    # Part 3 - Orchestratioon
    def testOrchestration(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")
        
        p.sendline("orch load routing")
        p.sendline("rt addflow h1 h2")
        p.expect("Success")
        p.sendline("p select count(*) from rm")
        p.expect("1")
        p.sendline("p select count(*) from cf")
        p.expect("0")

        p.sendline("orch run")
        p.sendline("p select count(*) from rm")
        p.expect("1")
        p.sendline("p select count(*) from cf")
        p.expect("1")
        p.sendline("m h1 ping -c 1 h2")
        p.expect(" 0% packet loss")

        p.sendline("rt delflow h1 h2")
        p.expect("Success")
        p.sendline("orch run")
        p.sendline("p select count(*) from rm")
        p.expect("0")
        p.sendline("p select count(*) from cf")
        p.expect("0")

        p.sendline("orch auto on")
        p.sendline("rt addflow h1 h2")
        p.expect("Success")
        p.sendline("p select count(*) from rm")
        p.sendline("p select count(*) from cf")
        p.expect("1")
        p.sendline("m h1 ping -c 1 h2")
        p.expect(" 0% packet loss")

        p.sendline("exit")
        p.sendeof()
        time.sleep(1)

    # Part 4 - App Sub-shells
    def testApplications(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")

        p.sendline("orch load sample")
        p.sendline("sample echo Hello World")
        p.expect("SampleConsole says: Hello World")

        p.sendline("sample")
        p.expect("sample>")
        p.sendline("echo Hello World")
        p.expect("SampleConsole says: Hello World")
        p.sendline("exit")
        p.expect("ravel>")

        p.sendline("sample")
        p.sendline("help echo")
        p.expect("echo arguments")
        p.sendline("exit")
        p.expect("ravel>")

        p.sendline("help sample echo")
        p.expect("echo arguments")

        p.sendline("help sample")
        p.expect("sample commands")

        p.sendline("orch load routing")
        p.sendline("rt addflow h1 h2")
        p.expect("Success")
        p.sendline("orch run")
        p.sendline("m h1 ping -c 1 h2")
        p.expect(" 0% packet loss")
        p.sendline("rt delflow h1 h2")
        p.expect("Success")
        p.sendline("orch run")
        p.sendline("m h1 ping -c 1 h2")
        p.expect("100% packet loss")

        p.sendline("orch auto on")
        p.sendline("rt addflow h1 h2")
        p.expect("Success")
        p.sendline("m h1 ping -c 1 h2")
        p.expect(" 0% packet loss")
        p.sendline("rt delflow h1 h2")
        p.expect("Success")
        p.sendline("m h1 ping -c 1 h2")
        p.expect("100% packet loss")

        p.sendline("time rt addflow h1 h2")
        p.expect("Time:")
        p.sendline("profile rt delflow h1 h2")
        p.expect("db_select")
        p.sendline("profile rt addflow h1 h2")
        p.expect("db_select")

        p.sendline("orch load fw")
        p.sendline("fw addflow h1 h2")
        p.sendline("p select count(*) from fw_policy_acl")
        p.expect("1")
        p.sendline("fw addhost h1")
        p.sendline("p select count(*) from fw_policy_user")
        p.expect("1")

        p.sendline("exit")
        p.sendeof()
        time.sleep(1)

    # Part 5 - Orchestration Demo
    def testDemo(self):
        p = pexpect.spawn("python {0} --topo=linear,4".format(resource_file("ravel.py")))
        p.expect("ravel>")

        p.sendline("orch load routing fw")
        p.expect("ravel>")
        p.sendline("fw addhost h4")
        p.expect("Success")
        p.sendline("fw addhost h2")
        p.expect("Success")
        p.sendline("fw addflow h4 h3")
        p.expect("Success")

        p.sendline("rt addflow h4 h3 1")
        p.expect("Success")
        p.sendline("orch run")
        p.sendline("p select count(*) from rm")
        p.expect("1")
        p.sendline("p select count(*) from cf")
        p.expect("2")
        p.sendline("m h4 ping -c 1 h3")
        p.expect(" 0% packet loss")

        p.sendline("rt addflow h1 h2 1")
        p.expect("Success")
        p.sendline("p select count(*) from rm")
        p.expect("2")
        p.sendline("p select count(*) from fw_violation")
        p.expect("1")
        p.sendline("orch run")
        p.sendline("p select count(*) from fw_violation")
        p.expect("0")
        p.sendline("p select count(*) from rm")
        p.expect("1")
        p.sendline("p select count(*) from cf")
        p.expect("2")
        p.sendline("m h1 ping -c 1 h2")
        p.expect("100% packet loss")

        p.sendline("exit")
        p.sendeof()
        time.sleep(1)

    def tearDown(self):
        # kill pox if it's still running
        os.system("sudo killall -9 python2.7 > /dev/null 2>&1")

if __name__ == "__main__":
    unittest.main()
