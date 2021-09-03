from mininet.topo import Topo

class DiamondTopo(Topo):
    def __init__( self ):
        Topo.__init__( self )
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        self.addLink(s1,h1)
        self.addLink(s4,h2)
        self.addLink(s1,s2)
        self.addLink(s1,s3)
        self.addLink(s2,s4)
        self.addLink(s3,s4)

topos = { 'diamond': ( lambda: DiamondTopo() ) }
