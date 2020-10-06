from kvirt.config import Kconfig

private = "default"
api_ip = "13.0.0.253"
cidr = "13.0.0.0/24"

config = Kconfig()
config.k.create_network(name=private, cidr=cidr, overrides={'port_security_enabled': False})
config.k.create_network_port("karmab-vip", private, ip=api_ip, floating=True, security=False)
