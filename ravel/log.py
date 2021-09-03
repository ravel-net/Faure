#!/usr/bin/env python

import logging
import types
from logging import Logger

LEVELS = { "debug" : logging.DEBUG,
           "info" : logging.INFO,
           "warning" : logging.WARNING,
           "error" : logging.ERROR,
           "critical" : logging.CRITICAL
       }

DEFAULT_LEVEL = logging.ERROR
MSG_FORMAT = "%(levelname)s:%(funcName)s: %(message)s"

class Singleton(type):
    def __init__(cls, name, bases, dict_):
        super(Singleton, cls).__init__(name, bases, dict_)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance

class RavelLogger(Logger, object):
    __metaclass__ = Singleton
    
    def __init__(self):
        Logger.__init__(self, "ravel")
        ch = logging.StreamHandler()
        formatter = logging.Formatter(MSG_FORMAT)
        ch.setFormatter(formatter)
        self.addHandler(ch)
        self.setLogLevel()

    def setLogLevel(self, levelname=None):
        level = DEFAULT_LEVEL
        if levelname is not None:
            if levelname not in LEVELS:
                raise Exception("Unknown log level {0}".format(levelname))
            else:
                level = LEVELS.get(levelname, level)

        self.setLevel(level)

logger = RavelLogger()
