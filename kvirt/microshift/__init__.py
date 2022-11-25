from kvirt.common import success, info2, error
from kvirt.common import get_ssh_pub_key
import os
from shutil import copyfile
import sys
import yaml


def create(config, plandir, cluster, overrides, dnsconfig=None):
    data = {'kubetype': 'microshift', 'sslip': True}
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        error("No usable public key found, which is required for the deployment. Create one using ssh-keygen")
        sys.exit(1)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    cluster = data.get('cluster')
    nodes = data.get('nodes', 1)
    if nodes == 0:
        error("Invalid number of nodes")
        sys.exit(1)
    register_acm = data.get('register_acm', False)
    if register_acm:
        pull_secret = data.get('pull_secret')
        if pull_secret is not None:
            if not os.path.isabs(pull_secret):
                pull_secret = os.path.abspath(pull_secret)
                data['pull_secret'] = pull_secret
            if not os.path.exists(pull_secret):
                error(f"pull_secret path {pull_secret} not found")
                sys.exit(1)
        else:
            error("pull_secret is required when using register_acm")
            sys.exit(1)
        kubeconfig_acm = data.get('kubeconfig_acm')
        if kubeconfig_acm is not None:
            if not os.path.isabs(kubeconfig_acm):
                kubeconfig_acm = os.path.abspath(kubeconfig_acm)
                data['kubeconfig_acm'] = kubeconfig_acm
            if not os.path.exists(kubeconfig_acm):
                error(f"kubeconfig_acm path {kubeconfig_acm} not found")
                sys.exit(1)
        else:
            error("kubeconfig_acm is required when using register_acm")
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
            installparam['cluster'] = cluster
            installparam['kubetype'] = 'microshift'
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    threaded = data.get('threaded', False)
    result = config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=data, threaded=threaded)
    if result['result'] != 'success':
        sys.exit(1)
    KUBECONFIG = '/var/lib/microshift/resources/kubeadmin/kubeconfig'
    for index in range(nodes):
        name = f"{cluster}-{index}"
        config.wait_finish(name)
        finishfiles = [{'origin': KUBECONFIG, 'path': f"~/.kcli/clusters/{cluster}/auth/kubeconfig.{index}"}]
        config.handle_finishfiles(name, finishfiles)
        ip = config.k.info(name).get('ip')
        destination = f"{clusterdir}/auth/kubeconfig.{index}"
        os.system(f"sed -i -e 's/127.0.0.1/{ip}/' {destination}")
        if index == 0:
            copyfile(f"{clusterdir}/auth/kubeconfig.0", f"{clusterdir}/auth/kubeconfig")
    success(f"Kubernetes cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
