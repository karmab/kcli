from kvirt.config import Kconfig

client = None

config = Kconfig(client)
config.k.reconnect_hosts()
