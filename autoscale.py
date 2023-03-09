from kvirt.config import Kconfig
import os

cluster = os.environ['CLUSTER']
config = Kconfig()
config.loop_autoscale_cluster(cluster)
