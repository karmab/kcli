from kvirt.common import success, info2, warning
from kvirt.common import scp, _ssh_credentials, get_ssh_pub_key
import os
import yaml

CNI_DIR = 'cni_bin'


def create(config, plandir, cluster, overrides, dnsconfig=None):
    k = config.k
    data = {'kubetype': 'kind'}
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        msg = "No usable public key found, which is required for the deployment. Create one using ssh-keygen"
        return {'result': 'failure', 'reason': msg}
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'mykind')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    ctlplanes = data.get('ctlplanes', 1)
    if ctlplanes == 0:
        msg = "Invalid number of ctlplanes"
        return {'result': 'failure', 'reason': msg}
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists(clusterdir):
        msg = f"Remove existing directory {clusterdir} or use --force"
        return {'result': 'failure', 'reason': msg}
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir("%s/auth" % clusterdir)
        with open("%s/kcli_parameters.yml" % clusterdir, 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['cluster'] = cluster
            installparam['kubetype'] = 'kind'
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    if os.path.exists(CNI_DIR) and os.path.isdir(CNI_DIR):
        warning("Disabling default CNI to use yours instead")
        if not os.listdir(CNI_DIR):
            msg = "No CNI plugin provided, aborting..."
            return {'result': 'failure', 'reason': msg}
        data['cni_bin_path'] = f"{os.getcwd()}/{CNI_DIR}"
        data['disable_default_cni'] = True
    result = config.plan(plan, inputfile='%s/kcli_plan.yml' % plandir, overrides=data)
    if result['result'] != 'success':
        return result
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
    return {'result': 'success'}
