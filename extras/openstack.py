from kvirt.config import Kconfig

cluster = 'testk'
network = "default"
api_ip = "12.0.0.253"
cidr = "12.0.0.0/24"

config = Kconfig()
config.k.delete_network_port(f"{cluster}-vip" % cluster)
config.k.create_network(name=network, cidr=cidr, overrides={'port_security_enabled': True})
config.k.create_network_port(f"{cluster}-vip" % cluster, network, ip=api_ip, floating=True)
