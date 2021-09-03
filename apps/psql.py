"""
PostgreSQL sub-shell

PostgreSQL sub-shell is a core application that is enabled by default.
"""

import psycopg2
import tabulate

from ravel.app import AppConsole

class PSqlConsole(AppConsole):
    def default(self, line):
        "Execute a PostgreSQL statement"
        try:
            self.db.cursor.execute(line)
        except psycopg2.ProgrammingError, e:
            print e
            return

        try:
            data = self.db.cursor.fetchall()
            if data is not None:
                names = [row[0] for row in self.db.cursor.description]
                print tabulate.tabulate(data, headers=names)
        except psycopg2.ProgrammingError:
            # no results, eg from an insert/delete
            pass
        except TypeError, e:
            print e

shortcut = "p"
description = "execute a PostgreSQL statement"
console = PSqlConsole

