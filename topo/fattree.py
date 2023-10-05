from mininet.topo import Topo

class FattreeTopo(Topo):
    def __init__(self, k=4):
        super(FattreeTopo, self).__init__()
        self.size = k
        Topo.__init__(self)
        self._build()

    def _build(self):
        cores = (self.size/2)**2
        aggs = (self.size/2) * self.size
        edges = (self.size/2) * self.size
        hosts = (self.size/2)**2 * self.size

        switches = {}

        for pod in range(0, self.size):
            agg_offset = cores + self.size/2 * pod
            edge_offset = cores + aggs + self.size/2 * pod
            host_offset = cores + aggs + edges + (self.size/2)**2 * pod

            for agg in range(0, self.size/2):
                core_offset = agg * self.size/2
                aggname = "s{0}".format(agg_offset + agg)
                agg_sw = self.addSwitch(aggname)
                switches[aggname] = agg_sw

                # connect core and aggregate switches
                for core in range(0, self.size/2):
                    corename = "s{0}".format(core_offset + core)
                    core_sw = self.addSwitch(corename)
                    switches[corename] = core_sw
                    self.addLink(agg_sw, core_sw)

                # connect aggregate and edge switches
                for edge in range(0, self.size/2):
                    edgename = "s{0}".format(edge_offset + edge)
                    edge_sw = self.addSwitch(edgename)
                    switches[edgename] = edge_sw
                    self.addLink(agg_sw, edge_sw)

            # connect edge switches with hosts
            for edge in range(0, self.size/2):
                edgename = "s{0}".format(edge_offset + edge)
                edge_sw = switches[edgename]

                for h in range(0, self.size/2):
                    hostname = "h{0}".format(host_offset + self.size/2 * edge + h)
                    hostobj = self.addHost(hostname)
                    self.addLink(edge_sw, hostobj)

topos = { 'fattree' : FattreeTopo }
