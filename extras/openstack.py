from kvirt.config import Kconfig

cluster = 'testk'
network = "mynet"
api_ip = "12.0.0.251"
ingress_ip = "12.0.0.252"
cidr = "12.0.0.0/24"

config = Kconfig()
config.k.delete_network_port(f"{cluster}-api-vip")
config.k.delete_network_port(f"{cluster}-ingress-vip")
config.k.create_network(name=network, cidr=cidr, overrides={'port_security_enabled': True})
config.k.create_network_port(f"{cluster}-api-vip", network, ip=api_ip, floating=True)
config.k.create_network_port(f"{cluster}-ingress-vip", network, ip=ingress_ip, floating=True)
