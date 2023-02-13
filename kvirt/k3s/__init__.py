#!/usr/bin/env python

from kvirt.common import success, pprint, error, warning, get_kubectl, info2, container_mode
import os
import re
import sys
import yaml
from random import choice
from string import ascii_letters, digits
from shutil import which

cloudplatforms = ['aws', 'gcp']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'kube': cluster, 'kubetype': 'k3s', 'image': 'ubuntu2004', 'sdn': 'flannel',
            'extra_scripts': []}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    sdn = data['sdn']
    client = config.client
    pprint(f"Scaling on client {client}")
    if os.path.exists(clusterdir):
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
            yaml.safe_dump(data, paramfile)
    vmrules_all_names = []
    if data.get('vmrules', config.vmrules) and data.get('vmrules_strict', config.vmrules_strict):
        vmrules_all_names = [list(entry.keys())[0] for entry in data.get('vmrules', config.vmrules)]
    for role in ['ctlplanes', 'workers']:
        install_k3s_args = []
        for arg in data:
            if arg.startswith('install_k3s'):
                install_k3s_args.append(f"{arg.upper()}={data[arg]}")
        overrides = data.copy()
        overrides['scale'] = True
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        if role == 'ctlplanes':
            if overrides.get('ctlplanes', 1) == 1:
                continue
            if 'virtual_router_id' not in overrides or 'auth_pass' not in overrides:
                warning("Scaling up of ctlplanes won't work without virtual_router_id and auth_pass")
            if sdn is None or sdn != 'flannel':
                install_k3s_args.append("INSTALL_K3S_EXEC='--flannel-backend=none'")
            install_k3s_args = ' '.join(install_k3s_args)
        if role == 'workers' and overrides.get('workers', 0) == 0:
            continue
        if vmrules_all_names:
            reg = re.compile(f'{cluster}-{role[:-1]}-[0-9]+')
            vmrules_names = [name for name in vmrules_all_names if reg.match(name)]
            if len(vmrules_names) != overrides.get(role, 1):
                warning(f"Adjusting {role} number to vmrule entries")
                overrides[role] = len(vmrules_names)
            overrides['vmrules_names'] = sorted(vmrules_names)
        overrides['install_k3s_args'] = install_k3s_args
        config.plan(plan, inputfile=f'{plandir}/{role}.yml', overrides=overrides, threaded=threaded)


def create(config, plandir, cluster, overrides):
    platform = config.type
    data = {'kubetype': 'k3s', 'sdn': 'flannel', 'extra_scripts': []}
    data.update(overrides)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'myk3s')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    ctlplanes = data.get('ctlplanes', 1)
    workers = data.get('workers', 0)
    network = data.get('network', 'default')
    sdn = None if 'sdn' in overrides and overrides['sdn'] is None else data.get('sdn')
    image = data.get('image', 'ubuntu2004')
    api_ip = data.get('api_ip')
    if ctlplanes > 1:
        if platform in cloudplatforms:
            domain = data.get('domain', 'karmalabs.corp')
            api_ip = f"{cluster}-ctlplane.{domain}"
        elif api_ip is None:
            if network == 'default' and platform == 'kvm':
                warning("Using 192.168.122.253 as api_ip")
                data['api_ip'] = "192.168.122.253"
                api_ip = "192.168.122.253"
            elif platform == 'kubevirt':
                selector = {'kcli/plan': plan, 'kcli/role': 'ctlplane'}
                api_ip = config.k.create_service(f"{cluster}-api", config.k.namespace, selector,
                                                 _type="LoadBalancer", ports=[6443])
                if api_ip is None:
                    sys.exit(1)
                else:
                    pprint(f"Using api_ip {api_ip}")
                    data['api_ip'] = api_ip
            else:
                error("You need to define api_ip in your parameters file")
                sys.exit(1)
        if data.get('virtual_router_id') is None:
            data['virtual_router_id'] = hash(data['cluster']) % 254 + 1
            pprint(f"Using keepalived virtual_router_id {data['virtual_router_id']}")
    virtual_router_id = data.get('virtual_router_id')
    if data.get('auth_pass') is None:
        auth_pass = ''.join(choice(ascii_letters + digits) for i in range(5))
        data['auth_pass'] = auth_pass
    install_k3s_args = []
    for arg in data:
        if arg.startswith('install_k3s'):
            install_k3s_args.append(f"{arg.upper()}={data[arg]}")
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        error(f"Please remove existing directory {clusterdir} first...")
        sys.exit(1)
    if which('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['api_ip'] = api_ip
            installparam['plan'] = plan
            installparam['kubetype'] = 'k3s'
            installparam['image'] = image
            installparam['auth_pass'] = auth_pass
            installparam['virtual_router_id'] = virtual_router_id
            installparam['cluster'] = cluster
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    for arg in data.get('extra_ctlplane_args', []):
        if arg.startswith('--data-dir='):
            data['data_dir'] = arg.split('=')[1]
    bootstrap_overrides = data.copy()
    if os.path.exists("manifests") and os.path.isdir("manifests"):
        bootstrap_overrides['files'] = [{"path": "/root/manifests", "currentdir": True, "origin": "manifests"}]
    bootstrap_install_k3s_args = install_k3s_args.copy()
    if sdn is None or sdn != 'flannel':
        bootstrap_install_k3s_args.append("INSTALL_K3S_EXEC='--flannel-backend=none'")
    bootstrap_install_k3s_args = ' '.join(bootstrap_install_k3s_args)
    bootstrap_overrides['install_k3s_args'] = bootstrap_install_k3s_args
    result = config.plan(plan, inputfile=f'{plandir}/bootstrap.yml', overrides=bootstrap_overrides)
    if result['result'] != "success":
        sys.exit(1)
    for role in ['ctlplanes', 'workers']:
        if (role == 'ctlplanes' and ctlplanes == 1) or (role == 'workers' and workers == 0):
            continue
        nodes_overrides = data.copy()
        nodes_install_k3s_args = install_k3s_args.copy()
        nodes_overrides['install_k3s_args'] = nodes_install_k3s_args
        if role == 'ctlplanes':
            if sdn is None or sdn != 'flannel':
                nodes_install_k3s_args.append("INSTALL_K3S_EXEC='--flannel-backend=none'")
            nodes_install_k3s_args = ' '.join(nodes_install_k3s_args)
            nodes_overrides['install_k3s_args'] = nodes_install_k3s_args
            pprint("Deploying extra ctlplanes")
            threaded = data.get('threaded', False) or data.get('ctlplanes_threaded', False)
            config.plan(plan, inputfile=f'{plandir}/ctlplanes.yml', overrides=nodes_overrides, threaded=threaded)
        if role == 'workers':
            pprint("Deploying workers")
            os.chdir(os.path.expanduser("~/.kcli"))
            threaded = data.get('threaded', False) or data.get('workers_threaded', False)
            config.plan(plan, inputfile=f'{plandir}/workers.yml', overrides=nodes_overrides, threaded=threaded)
    success(f"K3s cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
