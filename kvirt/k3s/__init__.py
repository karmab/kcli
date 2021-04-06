#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import success, pprint, error, warning, get_kubectl, scp, _ssh_credentials, info2
import os
import sys
import yaml

cloudplatforms = ['aws', 'gcp']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'kube': cluster, 'kubetype': 'k3s'}
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    client = config.client
    k = config.k
    pprint("Scaling on client %s" % client)
    image = k.info("%s-master-0" % cluster).get('image')
    if image is None:
        error("Missing image...")
        sys.exit(1)
    else:
        pprint("Using image %s" % image)
    data['image'] = image
    os.chdir(os.path.expanduser("~/.kcli"))
    # config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=data)
    for role in ['masters', 'workers']:
        overrides = data.copy()
        # if overrides.get(role, 0) == 0:
        #    continue
        config.plan(plan, inputfile='%s/%s.yml' % (plandir, role), overrides=overrides)


def create(config, plandir, cluster, overrides):
    platform = config.type
    data = {'kubetype': 'k3s'}
    data.update(overrides)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    masters = data.get('masters', 1)
    network = data.get('network', 'default')
    token = data.get('token', 'supersecret')
    api_ip = data.get('api_ip')
    if masters > 1:
        if platform in cloudplatforms:
            domain = data.get('domain', 'karmalabs.com')
            api_ip = "%s-master.%s" % (cluster, domain)
        elif api_ip is None:
            if network == 'default' and platform == 'kvm':
                warning("Using 192.168.122.253 as api_ip")
                data['api_ip'] = "192.168.122.253"
                api_ip = "192.168.122.253"
            elif platform == 'kubevirt':
                selector = {'kcli/plan': plan, 'kcli/role': 'master'}
                api_ip = config.k.create_service("%s-api" % cluster, config.k.namespace, selector,
                                                 _type="LoadBalancer", ports=[6443])
                if api_ip is None:
                    os._exit(1)
                else:
                    pprint("Using api_ip %s" % api_ip)
                    data['api_ip'] = api_ip
            else:
                error("You need to define api_ip in your parameters file")
                os._exit(1)
    install_k3s_channel = data.get('install_k3s_channel', 'stable')
    if install_k3s_channel not in ['stable', 'latest', 'testing']:
        error("Invalid K3S install channel %s" % install_k3s_channel)
        os._exit(1)
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    firstmaster = "%s-master-0" % cluster
    if os.path.exists(clusterdir):
        error("Please remove existing directory %s first..." % clusterdir)
        sys.exit(1)
    if find_executable('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir("%s/auth" % clusterdir)
        with open("%s/kcli_parameters.yml" % clusterdir, 'w') as p:
            installparam = overrides.copy()
            installparam['api_ip'] = api_ip
            installparam['plan'] = plan
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    if os.path.exists("manifests") and os.path.isdir("manifests"):
        data['files'] = [{"path": "/root/manifests", "currentdir": True, "origin": "manifests"}]
    k = config.k
    result = config.plan(plan, inputfile='%s/bootstrap.yml' % plandir, overrides=data)
    if result['result'] != "success":
        os._exit(1)
    if masters > 1:
        pprint("Deploying extra masters")
        if 'name' in data:
            del data['name']
        config.plan(plan, inputfile='%s/masters.yml' % plandir, overrides=data)
    firstmasterip, firstmastervmport = _ssh_credentials(k, firstmaster)[1:]
    with open("%s/join.sh" % clusterdir, 'w') as f:
        if api_ip is None:
            api_ip = k.info(firstmaster)['ip']
        joincmd = "curl -sfL https://get.k3s.io | K3S_URL=https://%s:6443 K3S_TOKEN=%s" % (api_ip, token)
        if data['sdn'] != "flannel":
            joincmd += " INSTALL_K3S_EXEC='--no-flannel'"
        f.write("%s sh -\n" % joincmd)
    source, destination = "/root/kubeconfig", "%s/auth/kubeconfig" % clusterdir
    scpcmd = scp(firstmaster, ip=firstmasterip, user='root', source=source, destination=destination,
                 tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                 tunneluser=config.tunneluser, download=True, insecure=True, vmport=firstmastervmport)
    os.system(scpcmd)
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers")
        if 'name' in data:
            del data['name']
        os.chdir(os.path.expanduser("~/.kcli"))
        config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=data)
    success("K3s cluster %s deployed!!!" % cluster)
    info2("export KUBECONFIG=$HOME/.kcli/clusters/%s/auth/kubeconfig" % cluster)
    info2("export PATH=$PWD:$PATH")
