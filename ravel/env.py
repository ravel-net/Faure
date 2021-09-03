"""
The executing environment for the Ravel CLI
"""

import os
import subprocess

import ravel.db
import ravel.messaging
import ravel.util
from ravel.app import Application
from ravel.log import logger
from ravel.util import Config

class Environment(object):
    """The executing environment for the Ravel CLI"""

    def __init__(self, db, provider, appdirs, opts):
        """db: a ravel.db.RavelDb instance
           provider: a ravel.network.NetworkProvider instance
           appdirs: a list of directories to search for applications
           opts: startup options, such as db name, user"""
        self.db = db
        self.appdirs = appdirs
        self.apps = {}
        self.loaded = {}
        self.coreapps = ["psql", "mn", "orch"]
        self.xterms = []
        self.xterm_files = []
        self.maincli = None
        self.provider = provider
        self.opts = opts
        self.params = { "topology" : opts.topo,
                        "pox" : "offline" if opts.noctl else "running",
                        "mininet" : "offline" if opts.onlydb else "running",
                        "database" : opts.db,
                        "username" : opts.user,
                        "app path" : Config.AppDirs
        }

        self.discover()

    def set_cli(self, cli):
        self.maincli = cli

    def start(self):
        "Start the environment, initialize the database and network provider"
        self.provider.start()

        # only load topo if connecting to a clean db
        if self.db.cleaned:
            self.db.load_topo(self.provider)
            ravel.util.update_trigger_path(ravel.db.FLOW_SQL,
                                           ravel.util.resource_file())
            self.db.load_schema(ravel.db.FLOW_SQL)

            # delay loading topo triggers until after db is loaded
            # we only want to catch updates after initial load
            ravel.util.update_trigger_path(ravel.db.TOPO_SQL,
                                           ravel.util.resource_file())
            self.db.load_schema(ravel.db.TOPO_SQL)

            self.db.load_schema(ravel.db.AUXILIARY_FUN_SQL)
        else:
            logger.debug("connecting to existing db, skipping load_topo()")

        # if running onlydb mode, remove network flow triggers
        if self.opts.onlydb:
            self.db.load_schema(ravel.db.NOFLOW_SQL)

        self.provider.cacheNodes()

        core_shortcuts = []
        for app in self.coreapps:
            self.load_app(app)
            if self.loaded[app].shortcut is not None:
                core_shortcuts.append(self.loaded[app].shortcut)
        self.coreapps.extend(core_shortcuts)

    def stop(self):
        "Stop the environment, including the database and network provider"
        self.provider.stop()
        if len(self.xterms) > 0:
            logger.debug("waiting for xterms")

        for t in self.xterms:
            t.wait()

        # delete xterm temp files
        for f in self.xterm_files:
            os.unlink(f)

        ravel.messaging.clear_queue(Config.QueueId)

    def mkterm(self, cmds, cmdfile=None):
        """Create a new xterm process for the specified command
           cmds: string containing the command(s) to pass to xterm
           cmdfile: if the command requires a temporary file, a path
           to the file, which should be deleted when the environment stops"""
        p = subprocess.Popen(cmds,
                             shell=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)

        self.xterms.append(p)
        if cmdfile is not None:
            self.xterm_files.append(cmdfile)

    def unload_app(self, appname):
        """Unload an application from the environment
           appname: the application to load"""

        # don't unload coreapps
        if appname in self.coreapps:
            logger.warning("cannot unload core apps {0}".format(self.coreapps))
            return

        app = self.apps[appname]
        app.unload(self.db)

        if app.name in self.loaded:
            del self.loaded[app.name]

        if app.shortcut is not None and app.shortcut in self.loaded:
            del self.loaded[app.shortcut]

    def load_app(self, appname):
        """Load an application in the environment
           appname: the application to unload"""
        if appname in self.loaded:
            return

        # look for newly-added applications
        self.discover()

        if appname in self.apps:
            app = self.apps[appname]
            app.load(self.db)
            if app.is_loadable():
                self.loaded[app.name] = app
                if app.shortcut is not None and app.shortcut != app.name:
                    if app.shortcut in self.loaded:
                        logger.warning("shortcut {0} for {1} already in use"
                                       .format(app.shortcut, app.name))
                    else:
                        self.loaded[app.shortcut] = app

    def discover(self):
        """Search for new applications in the list of directories specified
           in the constructor"""
        new = []

        for d in self.appdirs:
            for f in os.listdir(d):
                if f.endswith(".py") or f.endswith(".sql"):
                    name = os.path.splitext(f)[0]
                    path = os.path.join(d, f)
                    if name not in self.apps:
                        self.apps[name] = Application(name)
                        new.append(name)
                    self.apps[name].link(path)

        for name in new:
            self.apps[name].init(self.db, self)

    def pprint(self):
        "Pretty print the list of startup parameters"
        out = ""
        pad = max([len(k) for k in self.params.keys()]) + 2
        for k,v in self.params.iteritems():
            key = "{0}:".format(k).ljust(pad, " ")
            out += "  {0} {1}\n".format(key, v)
        return out
