import cmd
from ravel.app import AppConsole

class FirewallConsole(AppConsole):
    def _getHostId(self, hname):
        hostnames = self.env.provider.cache_name
        if hname not in hostnames:
            print "Unknown host", hname
            return None

        return hostnames[hname]

    def do_addhost(self, line):
        """Add a host to the whitelist
           Usage: addhost [hostname]"""
        args = line.split()
        if len(args) != 1:
            print "Invalid syntax"
            return

        hostid = self._getHostId(args[0])
        if hostid is None:
            return

        try:
            self.db.cursor.execute("INSERT INTO FW_policy_user VALUES ({0});"
                                   .format(hostid))
        except Exception, e:
            print "Failure: host not added --", e
            return

        print "Success: host {0} added to whitelist".format(hostid)

    def do_delhost(self, line):
        """Remove a host from the whitelist
           Usage: delhost [hostname]"""
        args = line.split()
        if len(args) != 1:
            print "Invalid syntax"
            return

        hostid = self._getHostId(args[0])
        if hostid is None:
            return

        try:
            self.db.cursor.execute("DELETE FROM FW_policy_user WHERE uid={0};"
                                   .format(hostid))
        except Exception, e:
            print "Failure: host not removed --", e
            return

        print "Success: host {0} removed from whitelist".format(hostid)

    def do_addflow(self, line):
        """Add a flow to the whitelist
           Usage: addflow [fid]"""
        args = line.split()
        if len(args) != 2:
            print "Invalid syntax"
            return

        src = self._getHostId(args[0])
        dst = self._getHostId(args[1])
        if src is None or dst is None:
            return

        try:
            self.db.cursor.execute("INSERT INTO FW_policy_acl VALUES "
                                   "({0},{1},1);"
                                   .format(src, dst))
        except Exception, e:
            print "Failure: flow not added --", e
            return

        print "Success: flow ({0},{1}) added to whitelist".format(src, dst)

    def do_delflow(self, line):
        """Remove a flow from the whitelist
           Usage: delflow [fid]"""
        args = line.split()
        if len(args) != 2:
            print "Invalid syntax"
            return

        src = self._getHostId(args[0])
        dst = self._getHostId(args[1])
        if src is None or dst is None:
            return

        try:
            self.db.cursor.execute("DELETE FROM FW_policy_acl VALUES WHERE "
                                   "end1={0} AND end2={1};"
                                   .format(src, dst))
        except Exception, e:
            print "Failure: flow not removed --", e
            return

        print "Success: flow ({0},{1}) removed from whitelist".format(src, dst)

shortcut = "fw"
description = "a stateful firewall application"
console = FirewallConsole
