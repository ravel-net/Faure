"""
Orchestration sub-shell.

Orchestration is a core application that is enabled by default.
"""

import os
from itertools import tee, izip
from ravel.app import AppConsole, discoverComponents
from ravel.log import logger
from ravel.util import resource_file

routing = """
DROP TABLE IF EXISTS p_routing CASCADE;
CREATE UNLOGGED TABLE p_routing (
    counts    integer,
    status    text,
    PRIMARY key (counts)
);

CREATE TRIGGER run_routing_trigger
     AFTER INSERT ON p_routing
     FOR EACH ROW
   EXECUTE PROCEDURE spv_constraint1_fun();

CREATE OR REPLACE RULE run_routing AS
    ON INSERT TO p_routing
    WHERE (NEW.status = 'on')
    DO ALSO (
         UPDATE p_routing SET status = 'off' WHERE counts = NEW.counts;
         );
"""

ptable_template = """
DROP TABLE IF EXISTS p_{0} CASCADE;
CREATE UNLOGGED TABLE p_{0} (
       counts integer,
       status text,
       PRIMARY key (counts)
);
"""

runrule_template = """
CREATE OR REPLACE RULE run_{0} AS
    ON INSERT TO p_{0}
    WHERE (NEW.status = 'on')
    DO ALSO (
        DELETE FROM {1};
        UPDATE p_{0} SET status = 'off' WHERE counts = NEW.counts;
        );
"""

orderrule_template = """
CREATE OR REPLACE RULE {0}2{1} AS
    ON UPDATE TO p_{0}
    WHERE (NEW.status = 'off')
    DO ALSO
        INSERT INTO p_{1} values (NEW.counts, 'on');
"""

clock_template = """
CREATE OR REPLACE RULE {0}2Clock AS
    ON UPDATE TO p_{0}
    WHERE (NEW.status = 'off')
    DO ALSO
        INSERT INTO clock values (NEW.counts);
"""

def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

class OrchConsole(AppConsole):
    def __init__(self, db, env, components):
        self.ordering = None
        self.sql = None
        self._auto = False
        AppConsole.__init__(self, db, env, components)

    @property
    def auto(self):
        "returns: true if auto-orchestration is enabled, false otherwise"
        return self._auto

    def do_auto(self, line):
        """Set or unset automated orchestration (run "orch run" after
           each command automatically
           Usage: auto [on/off]"""
        args = line.split()
        if len(args) == 0:
            if self._auto:
                status = "\033[92m[enabled]\033[0m"
            else:
                status = "\033[91m[disabled]\033[0m"

            print "Auto-orchestration:", status
            return

        if len(args) != 1:
            print "Invalid syntax"

        arg = args[0]
        if arg.lower() not in ["on", "off"]:
            print "Invalid option: {0}.  Valid options: on or off".format(arg)
            return

        if arg.lower() == "on":
            self._auto = True
        else:
            self._auto = False

    def do_run(self, line):
        "Execute the orchestration protocol"
        if self.ordering is None:
            print "Must first set ordering"
            return

        try:
            self.db.cursor.execute("SELECT MAX(counts) FROM clock;")
            count = self.db.cursor.fetchall()[0][0] + 1
            hipri = self.ordering[-1]

            self.db.cursor.execute("INSERT INTO p_{0} VALUES ({1}, 'on');"
                                   .format(hipri, count))
        except Exception, e:
            print e

    def do_list(self, line):
        "List orchestrated applications and their priority"
        if self.ordering is None:
            print "No app under orchestration."
            return
        print "Priority: low -> high"
        for num, app in enumerate(self.ordering):
            print "   {0}: {1}".format(num, app)

    def do_reset(self, line):
        "Reset orchestration protocol function"
        if self.sql is None:
            return

        components = discoverComponents(self.sql)
        for component in components:
            component.drop(self.db)

    def do_load(self, line):
        """Start one or more applications with orchestration
           Usage: load [app1] [app2] ... (priority: low -> high)"""
        ordering = [app.lower() for app in line.split()]
        if len(ordering) == 0:
            return
        for app in ordering:
            if app.lower() not in self.env.apps:
                print "Unrecognized app", app
                return

        # load unloaded apps
        loads = [app for app in ordering if app not in self.env.loaded]
        for app in loads:
            logger.debug("loading unloaded app %s", app)
            self.env.load_app(app)

        # unload unlisted apps: if it's loaded but not a shortcut or core app
        unlisted = [app for app in self.env.loaded if app not in ordering
                    and app not in self.env.coreapps and app in self.env.apps]
        # for app in unlisted:
        #     logger.info("unloading unlisted app %s", app)
        #     self.env.unload_app(app)

        # processing in ascending order of priority
        ordering.reverse()

        sql = ""
        for app in [x for x in ordering if x != "routing"]:
            sql += ptable_template.format(app)
            try:
                self.db.cursor.execute("SELECT violation FROM app_violation WHERE app = '{0}';".format(app))
                violations = self.db.cursor.fetchall()
                if len(violations) > 0:
                    vtable = violations[0][0]
                    for v in violations[1:]:
                        vtable += "; DELETE FROM {0}".format(v[0])
                else:
                    vtable = "{0}_violation".format(app)
            except Exception, e:
                print e
            sql += runrule_template.format(app, vtable)

        if "routing" in ordering:
            sql += routing

        for app1, app2 in pairwise(ordering):
            sql += orderrule_template.format(app1, app2)

        sql += clock_template.format(ordering[-1])

        self.ordering = [x for x in reversed(ordering)]
        self.sql = sql

        log = resource_file("orch_log.sql")
        f = open(log, 'w')
        f.write(self.sql)
        f.close()

        logger.debug("logged orchestration protocol to %s", log)

        try:
            self.db.cursor.execute(self.sql)
        except Exception, e:
            print e

    def do_unload(self, line):
        """Stop one or more applications
           Usage: unload [app1] [app2] ..."""

        self.do_reset("")
        apps = line.split()
        for app in apps:
            try:
                self.db.cursor.execute("DELETE FROM app_violation WHERE app = '{0}'".format(app))
            except Exception, e:
                print e
            self.ordering.remove(app.lower())
            if app in self.env.apps:
                self.env.unload_app(app)
            else:
                print "Unknown application", app

        # reload orchestration with remaining applications
        self.do_load(" ".join(self.ordering))

    def help_load(self):
        print "syntax: load [app1] [app2] ..."
        print "-- set (ascending) priority for one or more applications"
        print "-- Note: A total ordering is needed for loaded applications."
        print "         Any unlisted applications that are loaded will be"
        print "         unloaded.  Any listed applications that are unloaded"
        print "         will be loaded."

    def complete_load(self, text, line, begidx, endidx):
        "Complete loaded applications' names for load command"
        apps = self.env.apps.keys()
        if not text:
            completions = apps
        else:
            completions = [d for d in apps if d.startswith(text)]

        return completions

    def complete_unload(self, text, line, begidx, endidx):
        "Complete unloaded applications' names for unload command"
        apps = self.env.apps.loaded.keys()
        if not text:
            completions = apps
        else:
            completions = [d for d in apps if d.startswith(text)]

        return completions

shortcut = "o"
description = "an automated orchestration protocol application"
console = OrchConsole
