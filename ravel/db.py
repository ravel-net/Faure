"""
The Ravel backend PostgreSQL database
"""

import psycopg2

from ravel.log import logger
from ravel.util import resource_file

ISOLEVEL = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT

BASE_SQL = resource_file("ravel/sql/base.sql")
FLOW_SQL = resource_file("ravel/sql/flows.sql")
NOFLOW_SQL = resource_file("ravel/sql/noflows.sql")
TOPO_SQL = resource_file("ravel/sql/topo.sql")
AUXILIARY_FUN_SQL = resource_file("ravel/sql/auxiliary_functions.sql")

class RavelDb():
    """A representation of Ravel's backend PostgreSQL database."""

    def __init__(self, name, user, base, passwd=None, reconnect=False):
        """name: the name of the database to connect to
           user: the username to use to connect
           base: a file containing the SQL implementation for Ravel's base
           passwd: the password to connect to the database
           reconnect: true to connect to an existing database setup, false
           to load a new instance of Ravel's base into the database"""
        self.name = name
        self.user = user
        self.passwd = passwd
        self.base = base
        self.cleaned = not reconnect
        self._cursor = None
        self._conn = None

        if not reconnect and self.num_connections() > 0:
            logger.warning("existing connections to database, skipping reinit")
            self.cleaned = False
        elif not reconnect:
            self.init()
            self.cleaned = True

    @property
    def conn(self):
        "returns: a psycopg2 connection to the PostgreSQL database"
        if not self._conn or self._conn.closed:
            self._conn = psycopg2.connect(database=self.name,
                                          user=self.user,
                                          password=self.passwd)
            self._conn.set_isolation_level(ISOLEVEL)
        return self._conn

    @property
    def cursor(self):
        """returns: a psycopg2 cursor from RavelDb.conn for the PostgreSQL
           database"""
        if not self._cursor or self._cursor.closed:
            self._cursor = self.conn.cursor()
        return self._cursor

    def num_connections(self):
        """Returns the number of existing connections to the database.  If
           there are >1 connections, a new Ravel base implementation cannot be
           loaded into the database.
           returns: the number of existing connections to the database"""
        try:
            self.cursor.execute("SELECT * FROM pg_stat_activity WHERE "
                                "datname='{0}'".format(self.name))

            # ignore cursor connection
            return len(self.cursor.fetchall()) - 1
        except psycopg2.DatabaseError, e:
            logger.warning("error loading schema: %s", self.fmt_errmsg(e))

        return 0

    def init(self):
        """Initialize the database with the base Ravel SQL implementation.
           Removes any existing Ravel objects from the database"""
        self.clean()
        self.create()
        self.add_extensions()
        self.load_schema(self.base)

    def load_schema(self, script):
        """Load the specified schema into the database"
           script: path to a SQL script"""
        try:
            s = open(script, "r").read()
            logger.debug("loaded schema %s", script)
            self.cursor.execute(s)
        except psycopg2.DatabaseError, e:
            logger.warning("error loading schema: %s", self.fmt_errmsg(e))

    def load_topo(self, provider):
        """Load a topology from the specified network provider
           provider: a ravel.network.NetworkProvider instance"""
        topo = provider.topo
        try:
            node_count = 0
            nodes = {}
            for sw in topo.switches():
                node_count += 1
                dpid = provider.getNodeByName(sw).dpid
                ip = provider.getNodeByName(sw).IP()
                mac = provider.getNodeByName(sw).MAC()
                nodes[sw] = node_count
                self.cursor.execute("INSERT INTO switches (sid, dpid, ip, mac, name) "
                                    "VALUES ({0}, '{1}', '{2}', '{3}', '{4}');"
                                    .format(node_count, dpid, ip, mac, sw))

            for host in topo.hosts():
                node_count += 1
                ip = provider.getNodeByName(host).IP()
                mac = provider.getNodeByName(host).MAC()
                nodes[host] = node_count
                self.cursor.execute("INSERT INTO hosts (hid, ip, mac, name) "
                                    "VALUES ({0}, '{1}', '{2}', '{3}');"
                                    .format(node_count, ip, mac, host))

            for link in topo.links():
                h1,h2 = link
                if h1 in topo.switches() and h2 in topo.switches():
                    ishost = 0
                else:
                    ishost = 1

                sid = nodes[h1]
                nid = nodes[h2]
                self.cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                                    "VALUES ({0}, {1}, {2}, {3});"
                                    .format(sid, nid, ishost, 1))

                # bidirectional edges
                self.cursor.execute("INSERT INTO tp(sid, nid, ishost, isactive) "
                                    "VALUES ({1}, {0}, {2}, {3});"
                                    .format(sid, nid, ishost, 1))

                self.cursor.execute("INSERT INTO ports(sid, nid, port) "
                                    "VALUES ({0}, {1}, {2}), ({1}, {0}, {3});"
                                    .format(sid, nid,
                                            topo.port(h1, h2)[0],
                                            topo.port(h1, h2)[1]))

        except psycopg2.DatabaseError, e:
            logger.warning("error loading topology: %s", self.fmt_errmsg(e))

    def create(self):
        """If not created, create a database with the name specified in
           the constructor"""
        conn = None
        try:
            conn = psycopg2.connect(database="postgres",
                                    user=self.user,
                                    password=self.passwd)
            conn.set_isolation_level(ISOLEVEL)
            cursor = conn.cursor()
            cursor.execute("SELECT datname FROM pg_database WHERE " +
                           "datistemplate = false;")
            fetch = cursor.fetchall()
            
            dblist = [fetch[i][0] for i in range(len(fetch))]
            if self.name not in dblist:
                cursor.execute("CREATE DATABASE %s;" % self.name)
                logger.debug("created databse %s", self.name)
        except psycopg2.DatabaseError, e:
            logger.warning("error creating database: %s", self.fmt_errmsg(e))
        finally:
            conn.close()

    def add_extensions(self):
        """If not already added, add extensions required by Ravel (plpythonu,
           postgis, pgrouting)"""
        try:
            self.cursor.execute("SELECT 1 FROM pg_catalog.pg_namespace n JOIN " +
                                "pg_catalog.pg_proc p ON pronamespace = n.oid " +
                                "WHERE proname = 'pgr_dijkstra';")
            fetch = self.cursor.fetchall()

            if fetch == []:
                self.cursor.execute("CREATE EXTENSION IF NOT EXISTS plpythonu;")
                self.cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                self.cursor.execute("CREATE EXTENSION IF NOT EXISTS pgrouting;")
                self.cursor.execute("CREATE EXTENSION plsh;")
                logger.debug("created extensions")
        except psycopg2.DatabaseError, e:
            logger.warning("error loading extensions: %s", self.fmt_errmsg(e))
            
    def clean(self):
        """Clean the database of any existing Ravel components"""
        # close existing connections
        self.conn.close()

        conn = None
        try:
            conn = psycopg2.connect(database="postgres",
                                    user=self.user,
                                    password=self.passwd)
            conn.set_isolation_level(ISOLEVEL)
            cursor = conn.cursor()
            cursor.execute("drop database %s" % self.name)
        except psycopg2.DatabaseError, e:
            logger.warning("error cleaning database: %s", self.fmt_errmsg(e))
        finally:
            if conn:
                conn.close()

    def truncate(self):
        """Clean the database of any state Ravel components, except for 
           topology tables.  This rolls back the database to the state after
           the topology is first loaded"""
        try:
            tables = ["cf", "clock", "p_spv", "spatial_ref_sys", "spv_tb_del",
                      "spv_tb_ins", "rm", "rm_delta", "urm"]

            self.cursor.execute("truncate %s;" % ", ".join(tables))
            logger.debug("truncated tables")
            self.cursor.execute("INSERT INTO clock values (0);")
        except psycopg2.DatabaseError, e:
            logger.warning("error truncating databases: %s", self.fmt_errmsg(e))

    def fmt_errmsg(self, exception):
        return str(exception).strip()
