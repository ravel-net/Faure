#!/usr/bin/env python

import os
import sys
from optparse import OptionParser

# add ravel to path
if "PYTHONPATH" in os.environ:
    sys.path = os.environ["PYTHONPATH"].split(":") + sys.path
    raveldir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.abspath(raveldir))

from ravel.clean import clean
from ravel.cli import RavelCLI
from ravel.log import LEVELS, logger
from ravel.util import Config

def optParser():
    desc = "Ravel console"
    usage = "%prog [options]\ntype %prog -h for details"

    parser = OptionParser(description=desc, usage=usage)
    parser.add_option("--clean", "-c", action="store_true", default=False,
                      help="cleanup Ravel and Mininet")
    parser.add_option("--onlydb", "-o", action="store_true", default=False,
                      help="start without Mininet")
    parser.add_option("--reconnect", "-r", action="store_true", default=False,
                      help="reconnect to existing database, skipping db reinit")
    parser.add_option("--noctl", "-n", action="store_true", default=False,
                      help="start without controller (Mininet will still "
                      "attempt to connect to a remote controller)")
    parser.add_option("--db", "-d", type="string", default=Config.DbName,
                      help="Postgresql database name (default: %s)" % Config.DbName)
    parser.add_option("--user", "-u", type="string", default=Config.DbUser,
                      help="Postgresql username (default: %s)" % Config.DbUser)
    parser.add_option("--password", "-p", action="store_true", default=False,
                      help="prompt for postgresql password")
    parser.add_option("--custom", type="string", default=None,
                     help="read custom classes or params from py file(s) for Mininet")
    parser.add_option("--topo", "-t", type="string", default=None,
                      help="Mininet topology argument")
    parser.add_option("--script", "-s", type="string", default=None,
                      help="execute a Ravel script")
    parser.add_option("--exit", "-e", action="store_true", default=False,
                      help="exit after executing a Ravel script")
    parser.add_option("--verbosity", "-v",  type="choice",
                      choices=LEVELS.keys(), default="info",
                      help="|".join(LEVELS.keys()))

    return parser

if __name__ == "__main__":
    parser = optParser()
    #if len(sys.argv) == 1:
    #    parser.print_help()
    #    sys.exit(0)

    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        sys.exit(0)

    logger.setLogLevel(opts.verbosity)

    if opts.clean:
        clean()
        sys.exit(0)

    #if not opts.topo:
    #    parser.error("No topology specified")

    RavelCLI(opts)
