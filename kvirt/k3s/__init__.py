#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import success, pprint, error, warning, get_kubectl, info2, container_mode
import os
import sys
import yaml

cloudplatforms = ['aws', 'gcp']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'kube': cluster, 'kubetype': 'k3s'}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    with open("%s/kcli_parameters.yml" % clusterdir, 'w') as paramfile:
        yaml.safe_dump(data, paramfile)
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
    for role in ['masters', 'workers']:
        overrides = data.copy()
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        if role == 'masters' and overrides.get('masters', 1) == 1:
            continue
        config.plan(plan, inputfile='%s/%s.yml' % (plandir, role), overrides=overrides, threaded=threaded)


def create(config, plandir, cluster, overrides):
    platform = config.type
    data = {'kubetype': 'k3s', 'sdn': 'flannel'}
    data.update(overrides)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    masters = data.get('masters', 1)
    network = data.get('network', 'default')
    sdn = None if 'sdn' in overrides and overrides['sdn'] is None else data.get('sdn')
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
                    sys.exit(1)
                else:
                    pprint("Using api_ip %s" % api_ip)
                    data['api_ip'] = api_ip
            else:
                error("You need to define api_ip in your parameters file")
                sys.exit(1)
        if data.get('virtual_router_id') is None:
            data['virtual_router_id'] = hash(data['cluster']) % 254 + 1
            pprint("Using keepalived virtual_router_id %s" % data['virtual_router_id'])
    data['basedir'] = '/workdir' if container_mode() else '.'
    install_k3s_args = []
    for arg in data:
        if arg.startswith('install_k3s'):
            install_k3s_args.append("%s=%s" % (arg.upper(), data[arg]))
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
            installparam['kubetype'] = 'k3s'
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    if os.path.exists("manifests") and os.path.isdir("manifests"):
        data['files'] = [{"path": "/root/manifests", "currentdir": True, "origin": "manifests"}]
    k = config.k
    bootstrap_overrides = data.copy()
    bootstrap_install_k3s_args = install_k3s_args.copy()
    if sdn is None or sdn != 'flannel':
        bootstrap_install_k3s_args.append("INSTALL_K3S_EXEC='--flannel-backend=none'")
    bootstrap_install_k3s_args = ' '.join(bootstrap_install_k3s_args)
    bootstrap_overrides['install_k3s_args'] = bootstrap_install_k3s_args
    result = config.plan(plan, inputfile='%s/bootstrap.yml' % plandir, overrides=bootstrap_overrides)
    if result['result'] != "success":
        sys.exit(1)
    nodes_overrides = data.copy()
    nodes_install_k3s_args = install_k3s_args.copy()
    if sdn is None or sdn != 'flannel':
        nodes_install_k3s_args.append("INSTALL_K3S_EXEC='--flannel-backend=none'")
    nodes_install_k3s_args = ' '.join(nodes_install_k3s_args)
    nodes_overrides['install_k3s_args'] = nodes_install_k3s_args
    if masters > 1:
        pprint("Deploying extra masters")
        threaded = data.get('threaded', False) or data.get('masters_threaded', False)
        config.plan(plan, inputfile='%s/masters.yml' % plandir, overrides=nodes_overrides, threaded=threaded)
    with open("%s/join.sh" % clusterdir, 'w') as f:
        if api_ip is None:
            api_ip = k.info(firstmaster)['ip']
        joincmd = f"curl -sfL https://get.k3s.io | K3S_URL=https://{api_ip}:6443 K3S_TOKEN={token} "
        joincmd += ' '.join(install_k3s_args)
        extra_args = data['extra_worker_args'] if data.get('extra_worker_args', []) else data.get('extra_args', [])
        extra_args = ' '.join(extra_args)
        f.write("%s sh -s - agent %s \n" % (joincmd, extra_args))
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers")
        if 'name' in data:
            del data['name']
        os.chdir(os.path.expanduser("~/.kcli"))
        threaded = data.get('threaded', False) or data.get('workers_threaded', False)
        config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=data, threaded=threaded)
    success("K3s cluster %s deployed!!!" % cluster)
    info2("export KUBECONFIG=$HOME/.kcli/clusters/%s/auth/kubeconfig" % cluster)
    info2("export PATH=$PWD:$PATH")
