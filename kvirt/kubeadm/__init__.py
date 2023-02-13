#!/usr/bin/env python

from kvirt.common import success, error, pprint, warning, info2, container_mode
from kvirt.common import get_kubectl, kube_create_app, get_ssh_pub_key, _ssh_credentials, scp
from kvirt.defaults import UBUNTUS
import os
from random import choice
from shutil import which
from string import ascii_letters, digits
import sys
from time import sleep
import yaml

# virtplatforms = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere']
cloudplatforms = ['aws', 'gcp', 'ibm']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'sslip': False, 'kube': cluster, 'kubetype': 'generic', 'image': 'centos8stream',
            'extra_scripts': []}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if not os.path.exists(clusterdir):
        warning(f"Creating {clusterdir} from your input (auth creds will be missing)")
        overrides['cluster'] = cluster
        api_ip = overrides.get('api_ip')
        if config.type not in cloudplatforms and api_ip is None:
            error("Missing api_ip...")
            sys.exit(1)
        domain = overrides.get('domain')
        if domain is None:
            error("Missing domain...")
            sys.exit(1)
        os.mkdir(clusterdir)
        source = "/root/join.sh"
        destination = f"{clusterdir}/join.sh"
        first_ctlplane_vm = f"{cluster}-ctlplane-0"
        first_ctlplane_ip, first_ctlplane_vmport = _ssh_credentials(config.k, first_ctlplane_vm)[1:]
        scpcmd = scp(first_ctlplane_vm, ip=first_ctlplane_ip, user='root', source=source, destination=destination,
                     tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                     tunneluser=config.tunneluser, download=True, insecure=True, vmport=first_ctlplane_vmport)
        os.system(scpcmd)
        source = "/root/ctlplanecmd.sh"
        destination = f"{clusterdir}/ctlplanecmd.sh"
        scpcmd = scp(first_ctlplane_vm, ip=first_ctlplane_ip, user='root', source=source, destination=destination,
                     tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                     tunneluser=config.tunneluser, download=True, insecure=True, vmport=first_ctlplane_vmport)
        os.system(scpcmd)
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    if os.path.exists(clusterdir):
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
            yaml.safe_dump(data, paramfile)
    client = config.client
    pprint(f"Scaling on client {client}")
    image = data.get('image')
    if 'ubuntu' not in data:
        data['ubuntu'] = 'ubuntu' in image.lower() or len([u for u in UBUNTUS if u in image]) > 0
    os.chdir(os.path.expanduser("~/.kcli"))
    for role in ['ctlplanes', 'workers']:
        overrides = data.copy()
        overrides['scale'] = True
        if overrides.get(role, 0) == 0:
            continue
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        config.plan(plan, inputfile=f'{plandir}/{role}.yml', overrides=overrides, threaded=threaded)


def create(config, plandir, cluster, overrides):
    platform = config.type
    k = config.k
    data = {'kubetype': 'generic', 'sslip': False, 'domain': 'karmalabs.corp', 'wait_ready': False, 'extra_scripts': []}
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        error("No usable public key found, which is required for the deployment. Create one using ssh-keygen")
        sys.exit(1)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'mykube')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    cloud_lb = data.get('cloud_lb', True)
    ctlplanes = data.get('ctlplanes', 1)
    if ctlplanes == 0:
        error("Invalid number of ctlplanes")
        sys.exit(1)
    if ctlplanes > 1 and platform in cloudplatforms and not cloud_lb:
        error("multiple ctlplanes require cloud_lb to be set to True")
        sys.exit(1)
    network = data.get('network', 'default')
    api_ip = data.get('api_ip')
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
            service_type = "LoadBalancer" if k.access_mode == 'LoadBalancer' else 'ClusterIP'
            api_ip = config.k.create_service(f"{cluster}-api", config.k.namespace, selector, _type=service_type,
                                             ports=[6443])
            if api_ip is None:
                sys.exit(1)
            else:
                pprint(f"Using api_ip {api_ip}")
                data['api_ip'] = api_ip
        else:
            error("You need to define api_ip in your parameters file")
            sys.exit(1)
    if platform not in cloudplatforms:
        if data.get('virtual_router_id') is None:
            data['virtual_router_id'] = hash(data['cluster']) % 254 + 1
        virtual_router_id = data['virtual_router_id']
        pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
        auth_pass = ''.join(choice(ascii_letters + digits) for i in range(5))
        data['auth_pass'] = auth_pass
    version = data.get('version')
    if version is not None and not str(version).startswith('1.'):
        error(f"Invalid version {version}")
        sys.exit(1)
    if data.get('eksd', False) and data.get('engine', 'containerd') != 'docker':
        warning("Forcing engine to docker for eksd")
        data['engine'] = 'docker'
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    image = data.get('image', 'centos8stream')
    data['ubuntu'] = 'ubuntu' in image.lower() or len([u for u in UBUNTUS if u in image]) > 0
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        error(f"Please remove existing directory {clusterdir} first")
        sys.exit(1)
    if which('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['api_ip'] = api_ip
            if 'virtual_router_id' in data:
                installparam['virtual_router_id'] = data['virtual_router_id']
            if 'auth_pass' in data:
                installparam['auth_pass'] = auth_pass
            installparam['plan'] = plan
            installparam['cluster'] = cluster
            installparam['kubetype'] = 'generic'
            installparam['image'] = image
            installparam['ubuntu'] = 'ubuntu' in image.lower() or len([u for u in UBUNTUS if u in image]) > 1
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    result = config.plan(plan, inputfile=f'{plandir}/bootstrap.yml', overrides=data)
    if result['result'] != "success":
        sys.exit(1)
    if ctlplanes > 1:
        ctlplane_threaded = data.get('threaded', False) or data.get('ctlplanes_threaded', False)
        result = config.plan(plan, inputfile=f'{plandir}/ctlplanes.yml', overrides=data, threaded=ctlplane_threaded)
        if result['result'] != "success":
            sys.exit(1)
    if cloud_lb and config.type in cloudplatforms:
        config.k.delete_dns(f'api.{cluster}', domain=domain)
        if config.type == 'aws':
            data['vpcid'] = config.k.get_vpcid_of_vm(f"{cluster}-ctlplane-0")
        result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_api.yml', overrides=data)
        if result['result'] != 'success':
            sys.exit(1)
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers")
        if 'name' in data:
            del data['name']
        os.chdir(os.path.expanduser("~/.kcli"))
        worker_threaded = data.get('threaded', False) or data.get('workers_threaded', False)
        config.plan(plan, inputfile=f'{plandir}/workers.yml', overrides=data, threaded=worker_threaded)
    prefile = 'pre_ubuntu.sh' if data['ubuntu'] else 'pre_el.sh'
    predata = config.process_inputfile(plan, f"{plandir}/{prefile}", overrides=data)
    with open(f"{clusterdir}/pre.sh", 'w') as f:
        f.write(predata)
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    apps = data.get('apps', [])
    if apps:
        os.environ["PATH"] += f":{os.getcwd()}"
        for app in apps:
            appdir = f"{plandir}/apps/{app}"
            if not os.path.exists(appdir):
                warning(f"Skipping unsupported app {app}")
            else:
                pprint(f"Adding app {app}")
                if f'{app}_version' not in overrides:
                    data[f'{app}_version'] = 'latest'
                kube_create_app(config, appdir, overrides=data)
    if data['wait_ready']:
        pprint("Waiting for all nodes to join cluster")
        while True:
            if len(os.popen("kubectl get node -o name").readlines()) == ctlplanes + workers:
                break
            else:
                sleep(10)
    success(f"Kubernetes cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
