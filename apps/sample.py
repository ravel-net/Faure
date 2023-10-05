"""
Sample (dummy) sub-shell application
"""

from ravel.app import AppConsole

class SampleConsole(AppConsole):
    def do_echo(self, line):
        "Test command, echo arguments"
        print(self.__class__.__name__, "says:", line)

    def do_sql(self, line):
        "Execute a sql statement"
        self.db.cursor.execute(line)

shortcut = "sp"
description = "a sample application"
console = SampleConsole
