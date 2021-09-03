#!/usr/bin/env python

from unittest import defaultTestLoader, TextTestRunner
import os
import sys

def addRavelPath():
    # add ravel to path
    path = ""
    if 'PYTHONPATH' in os.environ:
        path = os.environ['PYTHONPATH']

    sys.path = path.split(':') + sys.path
    cwd = os.path.dirname(os.path.abspath(__file__))
    raveldir = os.path.normpath(os.path.join(cwd, "..", ".."))
    sys.path.append(os.path.abspath(raveldir))

def runTests(path):
    tests = defaultTestLoader.discover(path)
    TextTestRunner(verbosity=1).run(tests)

if __name__ == "__main__":
    addRavelPath()
    runTests(os.path.dirname(os.path.realpath(__file__)))
