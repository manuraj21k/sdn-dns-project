#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def create_dns_topo():
    net = Mininet(controller=RemoteController, switch=OVSSwitch)

    info("*** Adding Remote SDN Controller\n")
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    info("*** Adding Switch\n")
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    info("*** Adding Hosts\n")
    # Clients
    c1 = net.addHost('client1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    c2 = net.addHost('client2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')

    # DNS Servers
    dns1 = net.addHost('dns1', ip='10.0.0.10/24', mac='00:00:00:00:00:10')
    dns2 = net.addHost('dns2', ip='10.0.0.11/24', mac='00:00:00:00:00:11')
    dns3 = net.addHost('dns3', ip='10.0.0.12/24', mac='00:00:00:00:00:12')

    info("*** Creating Links\n")
    for host in [c1, c2, dns1, dns2, dns3]:
        net.addLink(host, s1)

    info("*** Starting Network\n")
    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_dns_topo()