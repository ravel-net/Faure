"""
Reset ravel's underlying topology under onlydb mode.
"""
from distutils.util import strtobool
from ravel.app import AppConsole
import ravel.mndeps

class TopoManagerConsole(AppConsole):
    def do_loadtp(self, line):
        if(not self.env.opts.onlydb):
            print "This application only runs under onlydb mode."
            return
        topo = ravel.mndeps.build(line)
        if(topo is None):
            print "Invalid mininet topology: ", topo
            return
        self.topo = topo
        self.env.loaded = {} #clear loaded apps records
        self.env.apps['orch'].console.ordering = None #clear ordering records
        self.env.stop()
        self.db.init()
        self.db.cleaned = True
        self.env.provider.topo = topo
        self.env.start()

shortcut = "tpmgr"
description = "Load a new topology under onlydb mode."
console = TopoManagerConsole




