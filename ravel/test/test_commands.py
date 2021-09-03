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

    def testStartupOptions(self):
        cmd = "python {0} ".format(resource_file("ravel.py"))
        p = pexpect.spawn(cmd + "--help")
        p.expect("Usage")
        p.sendeof()

        time.sleep(1)
        p = pexpect.spawn(cmd + "--topo=single,3")
        p.expect("ravel>")
        p.sendeof()

        time.sleep(1)
        p = pexpect.spawn(cmd + "--topo=single,3 --onlydb")
        p.expect("ravel>")
        p.sendline("m")
        p.sendline("net")
        p.expect("no CLI available")
        p.sendline("exit")
        p.sendeof()

        time.sleep(1)
        p = pexpect.spawn(cmd + "--topo single,3 --noctl")
        p.expect("Unable to contact the remote controller")
        p.expect("ravel>")
        p.sendline("exit")
        p.sendeof()
        
    def testCommands(self):
        p = pexpect.spawn(self.ravelCmd)
        p.expect("ravel>")
        p.sendline("exit")
        p.expect(pexpect.EOF)

    def tearDown(self):
        # kill pox if it's still running
        os.system("sudo killall -9 python2.7 > /dev/null 2>&1")

if __name__ == "__main__":
    unittest.main()
