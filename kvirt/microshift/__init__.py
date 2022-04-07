from kvirt.common import success, info2, error
from kvirt.common import get_ssh_pub_key
import os
from shutil import copyfile
import sys
import yaml


def create(config, plandir, cluster, overrides, dnsconfig=None):
    data = {'kubetype': 'microshift', 'KUBECONFIG': '/var/lib/microshift/resources/kubeadmin/kubeconfig', 'sslip': True}
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        error("No usable public key found, which is required for the deployment")
        sys.exit(1)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    cluster = data.get('cluster')
    nodes = data.get('nodes', 1)
    if nodes == 0:
        error("Invalid number of nodes")
        sys.exit(1)
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        error(f"Please remove existing directory {clusterdir} first...")
        sys.exit(1)
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['kubetype'] = 'microshift'
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    result = config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=data)
    if result['result'] != 'success':
        sys.exit(1)
    for index in range(nodes):
        ip = config.k.info(f"{cluster}-{index}").get('ip')
        destination = f"{clusterdir}/auth/kubeconfig.{index}"
        os.system(f"sed -i -e 's/127.0.0.1/{ip}/' {destination}")
        if index == 0:
            copyfile(f"{clusterdir}/auth/kubeconfig.0", f"{clusterdir}/auth/kubeconfig")
    success(f"Kubernetes cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
