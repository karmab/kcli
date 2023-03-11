from kvirt.config import Kconfig
from kvirt.common import error
import os
import sys

for variable in ['CLUSTER', 'CLUSTERTYPE', 'MAXIMUM', 'MINIMUM']:
    if f"AUTOSCALE_{variable}" not in os.environ:
        error(f"AUTOSCALE_{variable} env variable not set")
        sys.exit(1)
kube = os.environ['AUTOSCALE_CLUSTER']
kubetype = os.environ['AUTOSCALE_CLUSTERTYPE']
workers = int(os.environ['AUTOSCALE_WORKERS'])
threshold = int(os.environ['AUTOSCALE_MAXIMUM'])
idle = int(os.environ['AUTOSCALE_MINIMUM'])
config = Kconfig()
config.loop_autoscale_cluster(kube, kubetype, workers, threshold, idle)
