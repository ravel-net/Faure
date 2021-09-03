"""
Clean up Ravel and Mininet.
"""

import os
import mininet.clean
from ravel.log import logger

def clean():
    "Try to kill Pox controller and clean Mininet"
    logger.info("killing Pox controller instance")
    os.system("pkill -9 -f pox.py")

    logger.info("cleaning Mininet")
    mininet.clean.cleanup()
