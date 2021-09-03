"""
Ravel application abstractions
"""

import cmd
import importlib
import os
import re
import sys
import time
import tempfile

import psycopg2
import sqlparse
from sqlparse.tokens import Keyword

import ravel.util
from ravel.log import logger
from ravel.cmdlog import cmdLogger

def mk_watchcmd(db, args):
    """Construct a watch command for a psql query given a list of tables
       db: ravel.db.RavelDb instance on which to execute the SQL query
       args: list of tables and (optionally) limit on number or fows"""
    tables = []
    for arg in args:
        split = arg.split(",")
        if len(split) > 1:
            tables.append((split[0], split[1]))
        else:
            tables.append((split[0], None))

    queries = []
    for t in tables:
        limit = ""
        if t[1] is not None:
            limit = "LIMIT {0}".format(t[1])

        header = "*" * (15 - len(t[0])/2)
        queries.append("\echo '{0} {1} {0}'".format(header, t[0], header))
        query = "SELECT * FROM {0} {1};".format(t[0], limit)
        queries.append(query)

    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write("\n".join(queries))
    temp.close()
    os.chmod(temp.name, 0666)

    watch_arg = "echo db: {0}; psql -U{1} -d {0} -f {2}".format(
        db.name, db.user, temp.name)
    watch = 'watch -c -n 2 --no-title "{0}"'.format(watch_arg)
    cmd = "xterm -e " + watch
    return cmd, temp.name

class SqlObjMatch(object):
    """Regular expression for matching a SQL component within an application's
       SQL implementation"""

    def __init__(self, typ, regex, group):
        """typ: the object type,
           regex: the regex to match the type
           group: list of matching groups to construct the component's name"""
        self.typ = typ
        self.regex = regex
        if not isinstance(group, list):
            self.group = [group]
        else:
            self.group = group

    def match(self, stmt):
        """Search for a match in the specified SQL statement
           stmt: a SQL statement"""
        m = re.search(self.regex, stmt, re.IGNORECASE)
        if m:
            name = ""
            for num in self.group:
                name += m.group(num)
            return name
        return None

sqlComponents = []
sqlComponents.append(SqlObjMatch(
    "view",
    r"(create|drop).* view( if exists)? (\w+)",
    3))
sqlComponents.append(SqlObjMatch(
    "function",
    r"(create|drop).* function.*? (\w+)(\(.*\)) RETURNS",
    [2,3]))
sqlComponents.append(SqlObjMatch(
    "table",
    r"(create|drop).* table( if exists)?( if not exists)? (\w+)",
    4))
sqlComponents.append(SqlObjMatch(
    "rule",
    r"(create).* rule (\w+) AS( ON )(\w+) TO (\w+)",
    [2, 3, 5]))

def discoverComponents(sql):
    """Search for installable/removable components within a string containing
       one or more SQL statemnets"""
    components = []
    parsed = sqlparse.parse(sql)
    for statement in parsed:
        for token in statement.tokens:
            name = None
            typ = None

            # remove newlines, extra spaces for regex
            stmt = str(statement).replace("\n", " ")
            stmt = " ".join(stmt.split())

            for comp in sqlComponents:
                if token.match(Keyword, comp.typ):
                    name = comp.match(stmt)
                    typ = comp.typ

            if name is not None:
                component = AppComponent(name, typ)
                if component not in components:
                    components.append(component)

    # sort alphabetically, should fix drop issues when 'rule on table'
    # is dropped before 'table'
    return sorted(components, key=lambda x: x.typ)

class AppConsole(cmd.Cmd):
    "Superclass for an application's sub-shell"

    def __init__(self, db, env, components):
        """db: a ravel.db.RavelDb instance
           env: a ravel.env.Environment instance of the CLI's executing environment
           components: list of the app's SQL components (tables, view, etc.)"""
        self.db = db
        self.env = env
        self.components = components
        self.logOn = False
        cmd.Cmd.__init__(self)

    def emptyline(self):
        "Don't repeat the last line when hitting return on empty line"
        return

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

    def do_cmdlogger(self, line):
        if str(line).lower() == 'on':
            self.logOn = True
            logger.info('Cmd logger on.')
        elif str(line).lower() == 'off':
            self.logOn = False
            logger.info('Cmd logger off.')
        else:
            logger.info("Input 'on' to turn on cmd logger and 'off' to turn it off.")

    def do_list(self, line):
        "List application components"
        print self.name, "components:"
        for comp in self.components:
            print "   ", comp

    def do_watch(self, line):
        "Watch application components"
        w = [c.name for c in self.components if c.watchable]
        cmd, cmdfile = mk_watchcmd(self.db, w)
        self.env.mkterm(cmd, cmdfile)

    def do_EOF(self, line):
        "Quit application console"
        sys.stdout.write("\n")
        return True

    def do_exit(self, line):
        "Quit application console"
        return True

class AppComponent(object):
    """A component in an application's SQL implementation.  Any addition
       to the database is considered a 'component' that must be removed
       when the application is unloaded.  A component could be a table,
       view, function, etc."""

    def __init__(self, name, typ):
        """name: the name of the component
           typ: the type of component (table, view, function)"""
        self.name = name
        self.typ = typ

    def drop(self, db):
        """Drop the component from the specified database
           db: a ravel.db.RavelDb instance containing the component"""
        try:
            cmd = "DROP {0} IF EXISTS {1} CASCADE;".format(self.typ, self.name)
            db.cursor.execute(cmd)
            logger.debug("removing component: %s", cmd)
        except Exception, e:
            logger.error("error removing component {0}: {1}"
                         .format(self.name, e))

    @property
    def watchable(self):
        """returns: true if the component is an object that can be watched with
           a select query"""
        return self.typ.lower() in ["table", "view"]

    def __eq__(self, other):
        return (isinstance(other, self.__class__)) \
            and self.name == other.name and self.typ == other.typ

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{1}:{0}".format(self.name, self.typ)

class Application(object):
    """A Ravel application.  In Ravel, an application contains a SQL
       implementation and, optionally, a sub-shell implemented in Python to
       monitor and control the application.  Application sub-shells are accesible
       from the main Ravel CLI by loading the application and typing its name
       or shortcut."""

    def __init__(self, name):
        "name: the name of the application"
        self.name = name
        self.shortcut = None
        self.description = ""
        self.pyfile = None
        self.sqlfile = None
        self.module = None
        self.components = []
        self.console = None

    def link(self, filename):
        """Link a resource or implementation file to the application
           filename: path to the file containing an application's resource"""
        if filename.endswith(".py"):
            self.pyfile = filename
        elif filename.endswith(".sql"):
            self.sqlfile = filename

    def is_loadable(self):
        """returns: true if the application's Python component (it's sub-shell)
           can be imported and instantiated"""
        return self.module is not None

    def load(self, db):
        """Load the application from the specified database
           db: a ravel.db.RavelDb instance into which the application will be loaded"""
        if self.sqlfile is None:
            logger.debug("loaded application %s with no SQL file", self.name)
            return

        with open(self.sqlfile) as f:
            try:
                db.cursor.execute(f.read())
            except psycopg2.ProgrammingError, e:
                print "Error loading app {0}: {1}".format(self.name, e)

        logger.debug("loaded application %s", self.name)

    def unload(self, db):
        """Unload the application from the specified database
           db: a ravel.db.RavelDb instance containing the application"""
        for component in self.components:
            component.drop(db)

        logger.debug("unloaded application %s", self.name)

    def init(self, db, env):
        """Initialize the application without loading it into the database.
           db: a ravel.db.RavelDb instance to be passed to the application's
           sub-shell
           env: a ravel.env.Environment instance of the CLI's executing
           environment to be passed to the application's sub-shell"""
        if not self.pyfile:
            return

        # discover sql components (tables, views, functions)
        if self.sqlfile is not None:
            with open(self.sqlfile) as f:
                self.components = discoverComponents(f.read())

        logger.debug("discovered {0} components: {1}"
                     .format(self.name, self.components))

        # if needed, add path
        filepath = os.path.dirname(self.pyfile)
        ravel.util.append_path(filepath)

        try:
            self.module = importlib.import_module(self.name)
            self.console =  self.module.console(db, env, self.components)

            # force module prompt to app name
            self.console.prompt = self.name + "> "
            self.console.doc_header = self.name + \
                                      " commands (type help <topic>):"
        except BaseException, e:
            errstr = "{0}: {1}".format(type(e).__name__, str(e))
            logger.warning("error loading %s console: %s",
                           self.name, e)

        try:
            self.shortcut = self.module.shortcut
            self.description = self.module.description
        except BaseException:
            pass

    def cmd(self, line):
        """Execute a command in the application's sub-shell.  If an empty
           command is passed, start the application's sub-shell in a cmdloop
           line: a command in the application's sub-shell, or an empty
           string"""
        if self.console:
            if line:
                self.console.onecmd(line)
            else:
                self.console.cmdloop()
