from kvirt.common import success, info2
from kvirt.common import get_ssh_pub_key
import os
from yaml import safe_dump, safe_load


def valid_rhn_credentials(config, overrides):
    rhnuser = config.rhnuser or overrides.get('rhnuser')
    rhnpassword = config.rhnpassword or overrides.get('rhnpassword')
    rhnactivationkey = config.rhnactivationkey or overrides.get('rhnactivationkey')
    rhnorg = config.rhnorg or overrides.get('rhnorg')
    return (rhnuser is not None and rhnpassword is not None) or (rhnactivationkey is not None and rhnorg is not None)


def create(config, plandir, cluster, overrides, dnsconfig=None):
    data = safe_load(open(f'{plandir}/kcli_default.yml'))
    data.update(overrides)
    if 'rhel' not in data['image'].lower():
        msg = "A rhel image is currently required for deployment"
        return {'result': 'failure', 'reason': msg}
    if not valid_rhn_credentials(config, overrides):
        msg = "Using rhel image requires setting rhnuser/rhnpassword or rhnorg/rhnactivationkey "
        msg += "in your conf or as parameters"
        return {'result': 'failure', 'reason': msg}
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        msg = "No usable public key found, which is required for the deployment. Create one using ssh-keygen"
        return {'result': 'failure', 'reason': msg}
    data['cluster'] = cluster
    plan = cluster
    data['kube'] = data['cluster']
    data['kubetype'] = 'microshift'
    cluster = data.get('cluster')
    register_acm = data.get('register_acm', False)
    pull_secret = data.get('pull_secret')
    if not os.path.isabs(pull_secret):
        pull_secret = os.path.abspath(pull_secret)
        data['pull_secret'] = pull_secret
    if not os.path.exists(pull_secret):
        msg = f"pull_secret path {pull_secret} not found"
        return {'result': 'failure', 'reason': msg}
    if register_acm:
        kubeconfig_acm = data.get('kubeconfig_acm')
        if kubeconfig_acm is not None:
            if not os.path.isabs(kubeconfig_acm):
                kubeconfig_acm = os.path.abspath(kubeconfig_acm)
                data['kubeconfig_acm'] = kubeconfig_acm
            if not os.path.exists(kubeconfig_acm):
                msg = f"kubeconfig_acm path {kubeconfig_acm} not found"
                return {'result': 'failure', 'reason': msg}
        else:
            msg = "kubeconfig_acm is required when using register_acm"
            return {'result': 'failure', 'reason': msg}
        check = f"KUBECONGIG={kubeconfig_acm} oc get secret -n open-cluster-management"
        check += " open-cluster-management-image-pull-credentials"
        if os.popen(check).read() == '':
            msg = "Missing open-cluster-management-image-pull-credentials secret on acm cluster"
            return {'result': 'failure', 'reason': msg}
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        msg = f"Remove existing directory {clusterdir} or use --force"
        return {'result': 'failure', 'reason': msg}
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['cluster'] = cluster
            installparam['kubetype'] = 'microshift'
            safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    threaded = data.get('threaded', False)
    result = config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=data, threaded=threaded)
    if result['result'] != 'success':
        return result
    KUBECONFIG = '/root/kubeconfig'
    name = f"{cluster}-0"
    config.wait_finish(name)
    finishfiles = [{'origin': KUBECONFIG, 'path': f"~/.kcli/clusters/{cluster}/auth/kubeconfig"}]
    config.handle_finishfiles(name, finishfiles)
    ip = config.k.info(name).get('ip')
    destination = f"{clusterdir}/auth/kubeconfig"
    os.system(f"sed -i -e 's/127.0.0.1/{ip}/' {destination}")
    success(f"Kubernetes cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
    return {'result': 'success'}
