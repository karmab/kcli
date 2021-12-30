from kvirt.common import success, info2, error
from kvirt.common import scp, _ssh_credentials, get_ssh_pub_key
import os
import sys
import yaml


def create(config, plandir, cluster, overrides, dnsconfig=None):
    k = config.k
    data = {'kubetype': 'kind'}
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        error("No usable public key found, which is required for the deployment")
        sys.exit(1)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    masters = data.get('masters', 1)
    if masters == 0:
        error("Invalid number of masters")
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
            installparam['kubetype'] = 'kind'
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    result = config.plan(plan, inputfile='%s/kcli_plan.yml' % plandir, overrides=data)
    if result['result'] != 'success':
        sys.exit(1)
    kindnode = "%s-kind" % cluster
    kindnodeip = "%s-kind" % cluster
    kindnodeip, kindnodevmport = _ssh_credentials(k, kindnode)[1:]
    source, destination = data['KUBECONFIG'], "%s/auth/kubeconfig" % clusterdir
    scpcmd = scp(kindnode, ip=kindnodeip, user='root', source=source, destination=destination,
                 tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                 tunneluser=config.tunneluser, download=True, insecure=True, vmport=kindnodevmport)
    os.system(scpcmd)
    success("Kubernetes cluster %s deployed!!!" % cluster)
    info2("export KUBECONFIG=$HOME/.kcli/clusters/%s/auth/kubeconfig" % cluster)
    info2("export PATH=$PWD:$PATH")
