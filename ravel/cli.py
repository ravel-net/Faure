"""
A command-line interface for Ravel.

Ravel's CLI provides a user-friendly way to interact the backend
PostgreSQL database and Mininet.
"""

import cmd
import getpass
import os
import sys
import time
from functools import partial

import ravel.mndeps
import ravel.profiling
from ravel.db import RavelDb, BASE_SQL
from ravel.env import Environment
from ravel.log import logger
from ravel.of import PoxInstance
from ravel.util import Config, resource_file
from ravel.cmdlog import cmdLogger

class RavelConsole(cmd.Cmd):
    "Command line interface for Ravel."

    prompt = "ravel> "
    doc_header = "Commands (type help <topic>):"

    def __init__(self, env, quiet=False):
        self.env = env

        if not quiet:
            self.intro = "RavelConsole: interactive console for Ravel.\n" \
                         "Configuration:\n" + self.env.pprint()

        cmd.Cmd.__init__(self)
        self.env.set_cli(self)
        self.logOn = False

    def default(self, line):
        "Check loaded applications before raising unknown command error"

        # should we execute a script?
        if os.path.isfile(line):
            self.do_exec(line)
            return

        if "orch" in self.env.loaded:
            auto_orch = self.env.loaded["orch"].console.auto

        cmd = line.strip().split()[0]
        if cmd in self.env.loaded:
            self.env.loaded[cmd].cmd(line[len(cmd):])
            if auto_orch:
                self.env.loaded["orch"].console.onecmd("run")
        else:
            print "*** Unknown command:", line

    def onecmd(self, line):
        "Run command and report execution time for each execution line"  
        if line:
            if self.logOn:
                startTime = time.time()
                stop = cmd.Cmd.onecmd(self, line)
                endTime = time.time()
                elapsed = round((endTime - startTime)*1000, 3)
                cmdLogger.logline('cmd: '+line)
                logger.info("Execution time: {0}ms".format(elapsed))
                cmdLogger.logline('start time: {0}'.format(time.asctime(time.localtime(startTime))))
                cmdLogger.logline('time span: {0}ms'.format(elapsed))
                return stop
            else:
                return cmd.Cmd.onecmd(self, line)

    def emptyline(self):
        "Don't repeat the last line when hitting return on empty line"
        return

    def do_load(self, line):
        """Start one or more applications
           Usage: load [app1] [app2] ..."""
        apps = line.split()
        for app in apps:
            if app in self.env.apps:
                self.env.load_app(app)
            else:
                print "Unknown application", app

    def do_unload(self, line):
        """Stop one or more applications
           Usage: unload [app1] [app2] ..."""
        apps = line.split()
        for app in apps:
            if app in self.env.apps:
                self.env.unload_app(app)
            else:
                print "Unknown application", app

    def do_exec(self, line):
        "Execute a Ravel script"

        if os.path.isdir(line):
            print "ravel: {0}: Is a directory".format(line)
            return

        if not os.path.isfile(line):
            print "ravel: {0}: No such file or directory".format(line)
            return

        with open(line) as f:
            for cmd in f.readlines():
                cmd = cmd.strip()

                if cmd == "" or cmd[0] == "#":
                    continue

                print "{0}{1}".format(RavelConsole.prompt, cmd)
                self.onecmd(cmd)

                # may need to wait for flows/database changes
                time.sleep(0.5)

    def do_cmdlogger(self, line):
        if str(line).lower() == 'on':
            self.logOn = True
            logger.info('Cmd logger on.')
        elif str(line).lower() == 'off':
            self.logOn = False
            logger.info('Cmd logger off.')
        else:
            logger.info("Input 'on' to turn on cmd logger and 'off' to turn it off.")

    def do_apps(self, line):
        "List available applications and their status"
        for app in self.env.apps.values():
            shortcut = ""
            description = ""

            status = "\033[91m[offline]\033[0m"
            if app.name in self.env.loaded:
                status = "\033[92m[online]\033[0m"
            if app.shortcut:
                shortcut = " ({0})".format(app.shortcut)
            if app.description:
                description = ": {0}".format(app.description)

            print "  {0} {1}{2}{3}".format(status, app.name,
                                           shortcut, description)

    def do_profile(self, line):
        """Run command and report detailed execution time.
           Note - if no counters are found, try enabling auto-orchestration
           with orch auto on"""
        if line:
            pe = ravel.profiling.ProfiledExecution()
            pe.start()
            self.onecmd(line)

            # wait for straggling counters to report
            time.sleep(0.5)

            pe.stop()
            sys.stdout.write("\n")
            pe.print_summary()

    def do_reinit(self, line):
        "Reinitialize the database, deleting all data except topology"
        self.env.db.truncate()

    def do_stat(self, line):
        "Show running configuration, state"
        print self.env.pprint()

    def do_time(self, line):
        "Run command and report execution time"
        elapsed = time.time()
        if line:
            self.onecmd(line)
        elapsed = time.time() - elapsed
        print "\nTime: {0}ms".format(round(elapsed * 1000, 3))

    def do_watch(self, line):
        """Launch an xterm window to watch database tables in real-time
           Usage: watch [table1(,max_rows)] [table2(,max_rows)] ...
           Example: watch hosts switches cf,5"""
        if not line:
            return

        args = line.split()
        if len(args) == 0:
            print "Invalid syntax"
            return

        cmd, cmdfile = ravel.app.mk_watchcmd(self.env.db, args)
        self.env.mkterm(cmd, cmdfile)

    def do_EOF(self, line):
        "Quit Ravel console"
        sys.stdout.write("\n")
        return True

    def do_exit(self, line):
        "Quit Ravel console"
        return True

    def do_help(self, arg):
        "List available commands with 'help' or detailed help with 'help cmd'"
        # extend to include loaded apps and their help methods
        tokens = arg.split()
        if len(tokens) > 0 and tokens[0] in self.env.loaded:
            app = self.env.apps[tokens[0]]
            if len(tokens) <= 1:
                print app.description
                app.console.do_help("")
            else:
                app.console.do_help(" ".join(tokens[1:]))
        else:
            cmd.Cmd.do_help(self, arg)

    def completenames(self, text, *ignored):
        "Add loaded application names/shortcuts to cmd name completions"
        completions = cmd.Cmd.completenames(self, text, ignored)

        apps = self.env.loaded.keys()
        if not text:
            completions.extend(apps)
        else:
            completions.extend([d for d in apps if d.startswith(text)])

        return completions

def RavelCLI(opts):
    """Start a RavelConsole instance given a list of command line options
       opts: parsed OptionParser object"""
    if opts.custom:
        ravel.mndeps.custom(opts.custom)

    if opts.topo:
        topo = ravel.mndeps.build(opts.topo)
        if topo is None:
            print "Invalid mininet topology", opts.topo
            return
    else: 
        topo = ravel.mndeps.build("empty")

    if opts.script is not None and not os.path.isfile(opts.script):
        print "{0}: no such script file".format(opts.script)
        return

    passwd = None
    if opts.password:
        passwd = getpass.getpass("Enter password: ")

    raveldb = ravel.db.RavelDb(opts.db,
                               opts.user,
                               ravel.db.BASE_SQL,
                               passwd,
                               opts.reconnect)

    if opts.noctl:
        controller = None
    else:
        if PoxInstance.is_running():
            print "Pox instance is already running.  Please shut down " \
                "existing controller first (or run ravel.py --clean)."
            return

        controller = PoxInstance("ravel.controller.poxmgr")

    from ravel.network import MininetProvider, EmptyNetProvider
    if opts.onlydb:
        net = EmptyNetProvider(raveldb, topo)
    else:
        net = MininetProvider(raveldb, topo, controller)

    if net is None:
        print "Cannot start network"

    env = Environment(raveldb, net, Config.AppDirs, opts)
    env.start()

    while True:
        try:
            if opts.script is not None:
                RavelConsole(env).do_exec(opts.script)

                if opts.exit:
                    break

            RavelConsole(env, quiet=opts.script).cmdloop()
            break
        except Exception, e:
            logger.warning("console crashed: %s", e)

    env.stop()
