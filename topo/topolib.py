from igraph import Graph
from ravel.log import logger
import os, sys

class Topo( object ):

    def __init__( self, *args, **params ):
        """Topo object.
           Optional named parameters:
           hinfo: default host options
           sopts: default switch options
           lopts: default link options
           calls build()"""
        self.g = Graph()
        self.hopts = params.pop( 'hopts', {} )
        self.sopts = params.pop( 'sopts', {} )
        self.lopts = params.pop( 'lopts', {} )
        # ports[src][dst][sport] is port on dst that connects to src
        self.ports = {}
        self.build( *args, **params )

    def build( self, *args, **params ):
        "Override this method to build your topology."
        pass

    def addNode( self, name, **opts ):
        """Add Node to graph.
           name: name
           opts: node options
           returns: node name"""
        self.g.add_vertex( name, **opts )
        return name

    def addHost( self, name, **opts ):
        """Convenience method: Add host to graph.
           name: host name
           opts: host options
           returns: host name"""
        if not opts and self.hopts:
            opts = self.hopts
        return self.addNode( name, isSwitch=False, **opts )

    def addSwitch( self, name, **opts ):
        """Convenience method: Add switch to graph.
           name: switch name
           opts: switch options
           returns: switch name"""
        if not opts and self.sopts:
            opts = self.sopts
        return self.addNode( name, isSwitch=True, **opts )

    def addLink( self, node1, node2, port1=None, port2=None, key=None, **opts ):
        """node1, node2: nodes to link together
           port1, port2: ports (optional)
           opts: link options (optional)
           key: useless, kept for compatibility with mininet"""
        if not opts and self.lopts:
            opts = self.lopts
        port1, port2 = self.addPort( node1, node2, port1, port2 )
        opts = dict( opts )
        opts.update( node1=node1, node2=node2, port1=port1, port2=port2 )
        self.g.add_edge(node1, node2, **opts)

    def nodes( self, sort=True ):
        """Return a list of nodes in graph"""
        nodes = self.g.vs["name"]
        if sort:
            nodes.sort()
        return nodes

    def isSwitch( self, n ):
        """Return true if node is a switch."""
        return self.g.vs.find(name=n)['isSwitch']

    def switches( self, sort=True ):
        """Return a list of switches."""
        #return [ n for n in self.nodes() if self.isSwitch( n ) ]
        switches = self.g.vs.select(isSwitch=True)["name"]
        if sort:
            switches.sort()
        return switches

    def hosts( self, sort=True ):
        """Return a list of hosts."""
        hosts =  self.g.vs.select(isSwitch=False)["name"]
        if sort:
            hosts.sort()
        return hosts

    def links( self, sort=False, withKeys=False, withInfo=False ):
        """Return a list of links
           sort: sort links alphabetically, preserving (src, dst) order
           withKeys: return link keys
           withInfo: return link info
           returns: list of ( src, dst [,key, info ] )"""
        
        if withKeys:
            if withInfo:
                links = [(self.g.vs[e[0]]["name"], self.g.vs[e[1]]["name"], e, self.g.es[self.g.get_eid(e[0],e[1])].attributes()) for e in self.g.get_edgelist()]
            else:
                links = [(self.g.vs[e[0]]["name"], self.g.vs[e[1]]["name"], e) for e in self.g.get_edgelist()]
        else:
            if withInfo:
                links = [(self.g.vs[e[0]]["name"], self.g.vs[e[1]]["name"], self.g.es[self.g.get_eid(e[0],e[1])].attributes()) for e in self.g.get_edgelist()]
            else:
                links = [(self.g.vs[e[0]]["name"], self.g.vs[e[1]]["name"]) for e in self.g.get_edgelist()]
        if sort:
            links.sort()
        return links

    def addPort( self, src, dst, sport=None, dport=None ):
        """Generate port mapping for new edge.
            src: source switch name
            dst: destination switch name"""
        # Initialize if necessary
        ports = self.ports
        ports.setdefault( src, {} )
        ports.setdefault( dst, {} )
        # New port: number of outlinks + base
        if sport is None:
            src_base = 1 if self.isSwitch( src ) else 0
            sport = len( ports[ src ] ) + src_base
        if dport is None:
            dst_base = 1 if self.isSwitch( dst ) else 0
            dport = len( ports[ dst ] ) + dst_base
        ports[ src ][ sport ] = ( dst, dport )
        ports[ dst ][ dport ] = ( src, sport )
        return sport, dport

    def port( self, src, dst ):
        """Get port numbers.
            src: source switch name
            dst: destination switch name
            returns: tuple (sport, dport), where
                sport = port on source switch leading to the destination switch
                dport = port on destination switch leading to the source switch"""
        e = self.g.es.find(node1_in=[src,dst], node2_in=[src,dst])
        (sport, dport) = (e["port1"], e["port2"]) if e["node1"] == src else (e["port2"], e["port1"])
        return (sport, dport)

    def _linkEntry( self, src, dst, key=None ):
        """Helper function: return link entry and key."""
        entry = self.g.es.find(node1_in=[src,dst], node2_in=[src,dst]).attributes()
        if key is None:
            key = min( entry )
        return entry, key

    def linkInfo( self, src, dst, key=None ):
        """Return link metadata dict
           We use simple graph, a (src,dst) tuple maps to one edge if exists."""
        #entry, key = self._linkEntry( src, dst, key )
        return self.g.es.find(node1_in=[src,dst], node2_in=[src,dst]).attributes()

    def setlinkInfo( self, src, dst, info, key=None ):
        """Set link metadata dict"""
        edgeIdx = self.g.es.find(node1_in=[src,dst], node2_in=[src,dst]).index
        for k in info.keys():
            self.g.es[edgeIdx][k] = info[k]

    def nodeInfo( self, name ):
        """Return metadata (dict) for node"""
        info = self.g.vs.find(name_eq=name).attributes()
        info.pop('name', None)#the name attribute will cause multiple value assigment for a key word argument 'name' in Mininet, it's redundant anyway.
        return info

    def setNodeInfo( self, name, info ):
        "Set metadata (dict) for node"
        self.g.node[ name ] = info
        vertexIdx = self.g.vs.find(name_eq=name).index
        for k in info.keys():
            self.g.vs[vertexIdx][k] = info[k]

class EmptyTopo(Topo):
    "Empty topology. This topology is to allow user to start Ravel without specifying any topology."

    def build( self ):
        self.g.vs["isSwitch"] = False
        self.g.vs["name"]=None

class SingleSwitchTopo( Topo ):
    "Single switch connected to k hosts."

    def build( self, k=2, **_opts ):
        "k: number of hosts"
        self.k = k
        switch = self.addSwitch( 's1' )
        for h in range( 1, k+1 ):
            host = self.addHost( 'h%s' % h )
            self.addLink( host, switch )

class SingleSwitchReversedTopo( Topo ):
    """Single switch connected to k hosts, with reversed ports.
       The lowest-numbered host is connected to the highest-numbered port.
       Useful to verify that Mininet properly handles custom port
       numberings."""

    def build( self, k=2 ):
        "k: number of hosts"
        self.k = k
        switch = self.addSwitch( 's1' )
        for h in range( 1, k+1 ):
            host = self.addHost( 'h%s' % h )
            self.addLink( host, switch,
                          port1=0, port2=( k - h + 1 ) )

class MinimalTopo( SingleSwitchTopo ):
    "Minimal topology with two hosts and one switch"
    def build( self ):
        return SingleSwitchTopo.build( self, k=2 )

class LinearTopo( Topo ):
    "Linear topology of k switches, with n hosts per switch."

    def build( self, k=2, n=1, **_opts):
        """k: number of switches
           n: number of hosts per switch"""
        self.k = k
        self.n = n

        if n == 1:
            genHostName = lambda i, j: 'h%s' % i
        else:
            genHostName = lambda i, j: 'h%ss%d' % ( j, i )

        lastSwitch = None
        for i in range( 1, k+1 ):
            # Add switch
            switch = self.addSwitch( 's%s' % i )
            # Add hosts to switch
            for j in range( 1, n+1 ):
                host = self.addHost( genHostName( i, j ) )
                self.addLink( host, switch )
            # Connect switch to previous
            if lastSwitch:
                self.addLink( switch, lastSwitch )
            lastSwitch = switch

class TreeTopo( Topo ):
    "Topology for a tree network with a given depth and fanout."

    def build( self, depth=1, fanout=2 ):
        # Numbering:  h1..N, s1..M
        self.hostNum = 1
        self.switchNum = 1
        # Build topology
        self.addTree( depth, fanout )

    def addTree( self, depth, fanout ):
        """Add a subtree starting with node n.
           returns: last node added"""
        isSwitch = depth > 0
        if isSwitch:
            node = self.addSwitch( 's%s' % self.switchNum )
            self.switchNum += 1
            for _ in range( fanout ):
                child = self.addTree( depth - 1, fanout )
                self.addLink( node, child )
        else:
            node = self.addHost( 'h%s' % self.hostNum )
            self.hostNum += 1
        return node

class FatTreeTopo( Topo ):
    "Fat tree topology with k pods."

    def build( self, k=4, **_opts ):
        try:
            self.size = int(k)
            if self.size <= 0 or self.size%2 != 0:
                raise ValueError
        except ValueError:
            print('The pod number of fat tree must be a positive even number!')
            return

        cores = (self.size/2)**2
        aggs = (self.size/2) * self.size
        edges = (self.size/2) * self.size
        hosts = (self.size/2)**2 * self.size
        switches = {}

        # add core switches
        for core in range(0, cores):
            corename = "s{0}".format(core)
            core_sw = self.addSwitch(corename)
            switches[corename] = core_sw

        for pod in range(0, self.size):
            agg_offset = cores + self.size/2 * pod
            edge_offset = cores + aggs + self.size/2 * pod
            host_offset = cores + aggs + edges + (self.size/2)**2 * pod

            # add aggregate switches
            for agg in range(0, self.size/2):
                aggname = "s{0}".format(agg_offset + agg)
                agg_sw = self.addSwitch(aggname)
                switches[aggname] = agg_sw
            
            # add edge switches
            for edge in range(0, self.size/2):
                edgename = "s{0}".format(edge_offset + edge)
                edge_sw = self.addSwitch(edgename)
                switches[edgename] = edge_sw

            for agg in range(0, self.size/2):
                core_offset = agg * self.size/2
                aggname = "s{0}".format(agg_offset + agg)
                agg_sw = switches[aggname]

                # connect core and aggregate switches
                for core in range(0, self.size/2):
                    corename = "s{0}".format(core_offset + core)
                    core_sw = switches[corename]
                    self.addLink(agg_sw, core_sw)

                # connect aggregate and edge switches
                for edge in range(0, self.size/2):
                    edgename = "s{0}".format(edge_offset + edge)
                    edge_sw = switches[edgename]
                    self.addLink(agg_sw, edge_sw)

            # connect edge switches with hosts
            for edge in range(0, self.size/2):
                edgename = "s{0}".format(edge_offset + edge)
                edge_sw = switches[edgename]

                for h in range(0, self.size/2):
                    hostname = "h{0}".format(host_offset + self.size/2 * edge + h)
                    hostobj = self.addHost(hostname)
                    self.addLink(edge_sw, hostobj)

class ISPTopo( Topo ):
    "ISP topology identified by its AS number"

    def build( self, k, **_opts ):
        self.asNumLst=[]
        pyPath = os.path.dirname(os.path.abspath(__file__))
        self.ISPTopoPath = os.path.join(pyPath, 'ISP_topo')
        try:
            asNumFile = open(os.path.join(self.ISPTopoPath, 'stat.txt'))
            asNumFile.readline()
            for line in asNumFile:
                for word in line.split():
                    self.asNumLst.append(int(word))
                    break
        except Exception, e:
            logger.error('unable to parse stat file: %s', e)
            return

        self.asNum = int(k)
        if self.asNum not in self.asNumLst:
            print('Invalid AS number: {0}!'.format(self.asNum))
            print('Please use the following available AS number:')
            for i in self.asNumLst:
                print(i)
            raise Exception

        switches = {}
        nodeMp = {}
        link = []
        nodeNmLst = []

        nodeFileNm = '{0}_nodes.txt'.format(self.asNum)
        edgeFileNm = '{0}_edges.txt'.format(self.asNum)
        try:
            nodeFile = open(os.path.join(self.ISPTopoPath, nodeFileNm))
        except Exception, e:
            logger.error('Unable to open nodes file: %s', e)
            return
        try:
            edgeFile = open(os.path.join(self.ISPTopoPath, edgeFileNm))
        except Exception, e:
            logger.error('Unable to open edges file: %s', e)
            return

        for line in nodeFile:
            for word in line.split():
                try:
                    nodeMp[int(word)] = 's{0}'.format(word)
                    nodeNmLst.append('s{0}'.format(word))
                except Exception, e:
                    logger.error("Unable to parse node number '{0}': ".format(word))
                    return
                break 

        for line in edgeFile:
            line=line.rstrip()
            words = line.split()
            if len(words) != 2:
                logger.error("Unrecognized format of edges file!")
                raise Exception
            try:
                if int(words[0]) not in nodeMp.keys():
                    logger.error("An edge connects to a nonexist switch {0} that is not exist!".format(words[0]))
                    raise Exception
                if int(words[1]) not in nodeMp.keys():
                    logger.error("An edge connects to a nonexist switch {0} that is not exist!".format(words[1]))
                    raise Exception
                if int(words[0]) != int(words[1]):
                    if ((int(words[0]), int(words[1])) not in link) and ((int(words[1]), int(words[0])) not in link):
                        #Edges in the edge file are unidirectional, but Ravel takes link in the topology as bidirectional. So, only one link is added for every edge.
                        link.append((int(words[0]), int(words[1])))
            except ValueError, e:
                logger.error("Unable to parse edge from switch '{0}' to switch '{1}'".format(words[0],words[1]))
                return None
        
        for sw in nodeNmLst:
            switches[sw] = self.addSwitch(sw)

        for i in range(len(link)):
            self.addLink(switches[nodeMp[link[i][0]]], switches[nodeMp[link[i][1]]])

