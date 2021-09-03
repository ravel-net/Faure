"""
Routing sub-shell.
"""

from ravel.app import AppConsole
from ravel.log import logger

class MyRoutingConsole(AppConsole):
    def __init__(self, db, env, components):
        AppConsole.__init__(self, db, env, components)

    def do_addflow(self, line):
        """Add a flow between two hosts, using Mininet hostnames
           Usage: addflow [host1] [host2]"""
        args = line.split()
        if len(args) != 2 and len(args) != 3:
            print "Invalid syntax"
            return

        hostnames = self.env.provider.cache_name
        src = args[0]
        dst = args[1]
        if src not in hostnames:
            print "Unknown host", src
            return

        if dst not in hostnames:
            print "Unknown host", dst
            return

        fw = 1
        if len(args) == 3:
            try:
                fw = int(args[2])
            except Exception:
                print "Invalid firewall option", args[2]
                return

            if fw not in [0,1]:
                print "Invalid firewall option:", fw
                return

        src = hostnames[src]
        dst = hostnames[dst]
        try:
            self.db.cursor.execute("SELECT MAX(fid) FROM my_rm;")
            fid = self.db.cursor.fetchall()[0][0]
            if fid is None:
                fid = 0

            fid += 1
            self.db.cursor.execute("INSERT INTO my_rm (fid, src, dst, FW) "
                                   "VALUES ({0}, {1}, {2}, {3});"
                                   .format(fid, src, dst, fw))
        except Exception, e:
            print "Failure: flow not installed --", e
            return

        print "Success: installed flow with fid", fid

    def _delFlowByName(self, src, dst):
        hostnames = self.env.provider.cache_name

        if src not in hostnames:
            print "Unknown host", src
            return

        if dst not in hostnames:
            print "Unknown host", dst
            return

        src = hostnames[src]
        dst = hostnames[dst]
        self.db.cursor.execute("SELECT fid FROM my_rm WHERE src={0} and dst={1};"
                               .format(src, dst))
        result = self.db.cursor.fetchall()

        if len(result) == 0:
            logger.warning("no flow installed for hosts {0},{1}".format(src, dst))
            return None

        fids = [res[0] for res in result]
        for fid in fids:
            self._delFlowById(fid)

        return fids

    def _delFlowById(self, fid):
        try:
            # does the flow exist?
            self.db.cursor.execute("SELECT fid FROM my_rm WHERE fid={0}".format(fid))
            if len(self.db.cursor.fetchall()) == 0:
                logger.warning("no flow installed with fid %s", fid)
                return None

            self.db.cursor.execute("DELETE FROM my_rm WHERE fid={0}".format(fid))
            return fid
        except Exception, e:
            print e
            return None

    def do_delflow(self, line):
        """Delete a flow between two hosts, using flow ID or Mininet hostnames"
           Usage: delflow [host1] [host2]
                  delflow [flow id]"""
        args = line.split()
        if len(args) == 1:
            fid = self._delFlowById(args[0])
        elif len(args) == 2:
            fid = self._delFlowByName(args[0], args[1])
        else:
            print "Invalid syntax"
            return

        if fid is not None:
            print "Success: removed flow with fid", fid
        else:
            print "Failure: flow not removed"

shortcut = "myrt"
description = "IP routing"
console = MyRoutingConsole
