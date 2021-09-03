"""
Utility and helper functions
"""

import ConfigParser
import os
import re
import sys

from ravel.log import logger

class ConnectionType:
    """A enum for connection protocols between database triggers and the
       OpenFlow manager.  Types include Rpc (remote procedure call), Mq
       (message queues), and ovs (ovs-ofctl tool)."""

    Ovs = 0
    Rpc = 1
    Mq = 2
    Name = { "ovs" : Ovs,
             "rpc" : Rpc,
             "mq" : Mq
         }


def update_trigger_path(filename, path):
    """Update PYTHONPATH within a Python-based trigger implemented within the
       SQL file specified in filename.
       filename: the file containing the SQL trigger implementation
       path: the path to append to PYTHONPATH"""
    path = os.path.expanduser(path)
    if not os.path.isfile(filename):
        logger.warning("cannot find sql file %s", filename)
        return

    with open(filename, "r") as f:
        lines = []
        content = f.read()

    newstr = 'sys.path.append("{0}")'.format(path)
    pattern = re.compile(r"sys.path.append\(\S+\)")
    content = re.sub(pattern, newstr, content)

    open(filename, "w").write(content)

def append_path(path):
    """Append a path to PYTHONPATH
       path: the path to append to PYTHONPATH"""
    path = os.path.expanduser(path)
    if "PYTHONPATH" not in os.environ:
        os.environ["PYTHONPATH"] = ""

    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path

    if path is None or path == "":
        path = "."

    if path not in sys.path:
        sys.path.append(path)

def resource_string(name):
    """Search for a file within the distribution and return it as a string
       name: the name of the file as a relative path from the top-level
       directory
       returns: the contents of the file as a string, if it exists"""
    path = resource_file(name)
    if os.path.isfile(name):
        return open(path, "r").read()
    else:
        logger.error("cannot read file %s", path)
        return None

def resource_file(name=None):
    """Search for a file within the distribution and return its absolute path.
       If no name is passed, returns the absolute path to the distribution's
       top-level directory
       name: the name of the file
       returns: absolute path to the file"""
    install_path = os.path.dirname(os.path.abspath(__file__))
    install_path = os.path.normpath(
        os.path.join(install_path, ".."))

    if name is None:
        return install_path

    return os.path.abspath(os.path.join(install_path, name))

def splitArgs( argstr ):
    """Split argument string into usable python arguments
       argstr: argument string with format fn,arg2,kw1=arg3...
       returns: fn, args, kwargs
       This function is adapted from Mininet (https://github.com/mininet/mininet/blob/8af3f28b67ca27077d8082ae25c4800870df6109/mininet/util.py#L511)."""

    def makeNumeric( s ):
        "Convert string to int or float if numeric."
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s

    split = argstr.split( ',' )
    fn = split[ 0 ]
    params = split[ 1: ]
    # Convert int and float args; removes the need for function
    # to be flexible with input arg formats.
    args = [ makeNumeric( s ) for s in params if '=' not in s ]
    kwargs = {}
    for s in [ p for p in params if '=' in p ]:
        key, val = s.split( '=', 1 )
        kwargs[ key ] = makeNumeric( val )
    return fn, args, kwargs

class ConfigParameters(object):
    "Class containing parameters parsed from Ravel's configuration file"
    def __init__(self):
        self.AppDirs = []
        self.DbName = None
        self.DbUser = None
        self.RpcHost = None
        self.RpcPort = None
        self.QueueId = None
        self.Connection = None
        self.PoxDir = None
        self.PoxPort = None
        self.read(resource_file("ravel.cfg"))

    def read(self, cfg):
        """Read the configuration file
           cfg: the path to the configuration file"""
        parser = ConfigParser.SafeConfigParser()
        parser.read(cfg)

        if parser.has_option("apps", "directories"):
            dirlist = parser.get("apps", "directories")
            dirlist = dirlist.split(",")
            dirlist = [d.strip() for d in dirlist]

            # if path doesn't start with / or ~, assume it's relative to
            # ravel directory
            dirlist = [x if x[0] == "/" or x[0] == "~"
                       else resource_file(x) for x in dirlist]

            # remove duplicates
            self.AppDirs.extend(list(set(dirlist)))

        if parser.has_option("of_manager", "poxdir"):
            self.PoxDir = parser.get("of_manager", "poxdir")

        if parser.has_option("of_manager", "poxport"):
            self.PoxPort = parser.get("of_manager", "poxport")

        if parser.has_option("of_manager", "connection"):
            name = parser.get("of_manager", "connection").lower()
            self.Connection = ConnectionType.Name[name]

        if parser.has_option("db", "db"):
            self.DbName = parser.get("db", "db")

        if parser.has_option("db", "user"):
            self.DbUser = parser.get("db", "user")

        if parser.has_option("rpc", "rpchost"):
            self.RpcHost = parser.get("rpc", "rpchost")
        if parser.has_option("rpc", "rpcport"):
            self.RpcPort = parser.getint("rpc", "rpcport")

        if parser.has_option("mq", "queueid"):
            self.QueueId = parser.getint("mq", "queueid")

Config = ConfigParameters()
