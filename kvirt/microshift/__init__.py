from kvirt.common import success, info2, error
from kvirt.common import scp, _ssh_credentials, get_ssh_pub_key
import os
import sys
import yaml


def create(config, plandir, cluster, overrides, dnsconfig=None):
    k = config.k
    data = {'kubetype': 'microshift'}
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        error("No usable public key found, which is required for the deployment")
        sys.exit(1)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    nodes = data.get('nodes', 1)
    if nodes == 0:
        error("Invalid number of nodes")
        sys.exit(1)
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists(clusterdir):
        error("Please remove existing directory %s first..." % clusterdir)
        sys.exit(1)
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir("%s/auth" % clusterdir)
        with open("%s/kcli_parameters.yml" % clusterdir, 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['kubetype'] = 'microshift'
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    result = config.plan(plan, inputfile='%s/kcli_plan.yml' % plandir, overrides=data)
    if result['result'] != 'success':
        sys.exit(1)
    microshiftnode = "%s-microshift" % cluster
    microshiftnodeip, microshiftnodevmport = _ssh_credentials(k, microshiftnode)[1:]
    source, destination = data['KUBECONFIG'], "%s/auth/kubeconfig" % clusterdir
    scpcmd = scp(microshiftnode, ip=microshiftnodeip, user='root', source=source, destination=destination,
                 tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                 tunneluser=config.tunneluser, download=True, insecure=True, vmport=microshiftnodevmport)
    os.system(scpcmd)
    sedcmd = "sed -i -e 's/127.0.0.1/%s/' %s" % (microshiftnode, destination)
    os.system(sedcmd)
    success("Kubernetes cluster %s deployed!!!" % cluster)
    info2("export KUBECONFIG=$HOME/.kcli/clusters/%s/auth/kubeconfig" % cluster)
    info2("export PATH=$PWD:$PATH")
