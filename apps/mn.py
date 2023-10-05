"""
Mininet sub-shell

Mininet sub-shell is a core application that is enabled by default.
"""

from ravel.app import AppConsole

class MininetConsole(AppConsole):
    def default(self, line):
        "Execute a command in Mininet"
        self.env.provider.cli(line)

shortcut = "m"
description = "execute a command in Mininet"
console = MininetConsole
