"""
Creating topologies from command-line parameters.
"""

import os
import re
from ravel.util import splitArgs
from topo.topolib import (EmptyTopo, SingleSwitchTopo, SingleSwitchReversedTopo, MinimalTopo, LinearTopo, TreeTopo, FatTreeTopo, ISPTopo)


TOPOS = { "empty": EmptyTopo,
          "minimal": MinimalTopo,
          "linear": LinearTopo,
          "reversed": SingleSwitchReversedTopo,
          "single": SingleSwitchTopo,
          "tree": TreeTopo,
          "fattree": FatTreeTopo,
          "isp": ISPTopo
      }

def setCustom(name, value):
    """Set custom parameters for Mininet
       name: parameter name
       value: parameter value"""
    if name in ("topos", "switches", "hosts", "controllers"):
        param = name.upper()
        globals()[param].update(value)
    elif name == "validate":
        validate = value
    else:
        globals()[name] = value

def custom(value):
    """Parse custom parameters
       value: string containing custom parameters"""
    files = []
    if os.path.isfile(value):
        files.append(value)
    else:
        files += value.split(",")

    for filename in files:
        customs = {}
        if os.path.isfile(filename):
            execfile(filename, customs, customs)
            for name, val in customs.iteritems():
                setCustom(name, val)
        else:
            print "Could not find custom file", filename

def build(topoStr):
    """Build topology from string with format (object, arg1, arg2,...).
       topoStr: topology string"""
    try:
        topo, args, kwargs = splitArgs( topoStr )
        if topo not in TOPOS:
            raise Exception( 'Invalid topo name %s' % topo )
        return TOPOS[ topo ]( *args, **kwargs )
    except Exception, e:
        print e
        return None