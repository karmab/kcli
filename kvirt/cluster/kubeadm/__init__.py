#!/usr/bin/env python

from binascii import hexlify
from ipaddress import ip_network
from kvirt.common import success, pprint, warning, info2, container_mode, wait_cloud_dns, update_etc_hosts
from kvirt.common import get_kubectl, kube_create_app, get_ssh_pub_key, _ssh_credentials, ssh, deploy_cloud_storage
from kvirt.defaults import UBUNTUS
import os
from random import choice
from re import match
from shutil import which
from string import ascii_lowercase, ascii_letters, digits
from subprocess import call
from tempfile import NamedTemporaryFile
from time import sleep
import yaml

cloudplatforms = ['aws', 'azure', 'gcp', 'ibm']


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
        first_vm = f"{cluster}-ctlplane-0"
        first_ip, first_vmport = _ssh_credentials(config.k, first_vm)[1:]
        data['first_ip'] = first_ip
        domain = overrides.get('domain')
        if domain is None:
            domaincmd = "grep DOMAIN= /root/bootstrap.sh"
            domaincmd = ssh(first_vm, ip=first_ip, user='root', tunnel=config.tunnel,
                            tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                            insecure=True, cmd=domaincmd, vmport=first_vmport)
            data['domain'] = os.popen(domaincmd).read().strip().split('=')[1]
        os.mkdir(clusterdir)
        tokencmd = "grep TOKEN= /root/bootstrap.sh"
        tokencmd = ssh(first_vm, ip=first_ip, user='root', tunnel=config.tunnel,
                       tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                       insecure=True, cmd=tokencmd, vmport=first_vmport)
        data['token'] = os.popen(tokencmd).read().strip().split('=')[1]
        certkeycmd = "grep CERTKEY= /root/bootstrap.sh"
        certkeycmd = ssh(first_vm, ip=first_ip, user='root', tunnel=config.tunnel,
                         tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                         insecure=True, cmd=certkeycmd, vmport=first_vmport)
        data['cert_key'] = os.popen(certkeycmd).read().strip().split('=')[1]
    if 'first_ip' not in data:
        first_info = config.k.info(f'{cluster}-ctlplane-0')
        first_ip = first_info.get('private_ip') or first_info.get('ip')
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
        result = config.plan(plan, inputfile=f'{plandir}/{role}.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            return result
    return {'result': 'success'}


def create(config, plandir, cluster, overrides):
    platform = config.type
    k = config.k
    data = {'kubetype': 'generic', 'sslip': False, 'domain': 'karmalabs.corp', 'wait_ready': False, 'extra_scripts': [],
            'calico_version': None, 'autoscale': False, 'token': None, 'async': False, 'cloud_lb': True,
            'cloud_dns': False, 'cloud_storage': True}
    async_install = data['async']
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        msg = "No usable public key found, which is required for the deployment. Create one using ssh-keygen"
        return {'result': 'failure', 'reason': msg}
    data['cluster'] = overrides.get('cluster') or cluster or 'mykube'
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    cloud_lb = data['cloud_lb']
    cloud_dns = data['cloud_dns']
    cloud_storage = data['cloud_storage']
    autoscale = data.get('autoscale')
    ctlplanes = data.get('ctlplanes', 1)
    if ctlplanes == 0:
        msg = "Invalid number of ctlplanes"
        return {'result': 'failure', 'reason': msg}
    if ctlplanes > 1 and platform in cloudplatforms and not cloud_lb:
        msg = "Multiple ctlplanes require cloud_lb to be set to True"
        return {'result': 'failure', 'reason': msg}
    network = data.get('network', 'default')
    api_ip = data.get('api_ip')
    if platform in cloudplatforms:
        domain = data.get('domain', 'karmalabs.corp')
        api_ip = f"{cluster}-ctlplane.{domain}"
    elif api_ip is None:
        network = data.get('network')
        networkinfo = k.info_network(network)
        if not networkinfo:
            msg = f"Issue getting network {network}"
            return {'result': 'failure', 'reason': msg}
        if platform == 'kvm' and networkinfo['type'] == 'routed':
            cidr = networkinfo['cidr']
            if cidr == 'N/A':
                msg = "Couldnt gather an api_ip from your specified network"
                return {'result': 'failure', 'reason': msg}
            api_index = 2 if ':' in cidr else -3
            api_ip = str(ip_network(cidr)[api_index])
            warning(f"Using {api_ip} as api_ip")
            data['api_ip'] = api_ip
        elif platform == 'kubevirt':
            selector = {'kcli/plan': plan, 'kcli/role': 'ctlplane'}
            service_type = "LoadBalancer" if k.access_mode == 'LoadBalancer' else 'ClusterIP'
            api_ip = config.k.create_service(f"{cluster}-api", config.k.namespace, selector, _type=service_type,
                                             ports=[6443])
            if api_ip is None:
                msg = "Couldnt get an kubevirt api_ip from service"
                return {'result': 'failure', 'reason': msg}
            else:
                pprint(f"Using api_ip {api_ip}")
                data['api_ip'] = api_ip
        else:
            msg = "You need to define api_ip in your parameters file"
            return {'result': 'failure', 'reason': msg}
    if platform not in cloudplatforms:
        if data.get('virtual_router_id') is None:
            data['virtual_router_id'] = hash(data['cluster']) % 254 + 1
        virtual_router_id = data['virtual_router_id']
        pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
        auth_pass = ''.join(choice(ascii_letters + digits) for i in range(5))
        data['auth_pass'] = auth_pass
    valid_characters = ascii_lowercase + digits
    token = data['token']
    if token is not None:
        if match(r"[a-z0-9]{6}.[a-z0-9]{16}", data['token']) is not None:
            msg = "Incorrect token format. It should be [a-z0-9]{6}.[a-z0-9]{16}"
            return {'result': 'failure', 'reason': msg}
    else:
        token1 = ''.join(choice(valid_characters) for i in range(6))
        token2 = ''.join(choice(valid_characters) for i in range(16))
        token = f'{token1}.{token2}'
        data['token'] = token
    cert_key = hexlify(os.urandom(32)).decode()
    data['cert_key'] = hexlify(os.urandom(32)).decode()
    version = data.get('version')
    if version is not None and not str(version).startswith('1.'):
        msg = f"Invalid version {version}"
        return {'result': 'failure', 'reason': msg}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    image = data.get('image', 'centos8stream')
    data['ubuntu'] = 'ubuntu' in image.lower() or len([u for u in UBUNTUS if u in image]) > 0
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        msg = f"Remove existing directory {clusterdir} or use --force"
        return {'result': 'failure', 'reason': msg}
    if which('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
    result = config.plan(plan, inputfile=f'{plandir}/bootstrap.yml', overrides=data)
    if result['result'] != "success":
        return result
    first_info = config.k.info(f'{cluster}-ctlplane-0')
    first_ip = first_info.get('private_ip') or first_info.get('ip')
    data['first_ip'] = first_ip
    with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
        installparam = overrides.copy()
        installparam['api_ip'] = api_ip
        if 'virtual_router_id' in data:
            installparam['virtual_router_id'] = data['virtual_router_id']
        if 'auth_pass' in data:
            installparam['auth_pass'] = auth_pass
        installparam['plan'] = plan
        installparam['token'] = token
        installparam['cert_key'] = cert_key
        installparam['cluster'] = cluster
        installparam['kubetype'] = 'generic'
        installparam['image'] = image
        installparam['ubuntu'] = 'ubuntu' in image.lower() or len([u for u in UBUNTUS if u in image]) > 1
        installparam['first_ip'] = first_ip
        yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    if ctlplanes > 1:
        ctlplane_threaded = data.get('threaded', False) or data.get('ctlplanes_threaded', False)
        result = config.plan(plan, inputfile=f'{plandir}/ctlplanes.yml', overrides=data, threaded=ctlplane_threaded)
        if result['result'] != "success":
            return result
    if cloud_lb and config.type in cloudplatforms:
        config.k.delete_dns(f'api.{cluster}', domain=domain)
        if config.type == 'aws':
            data['vpcid'] = config.k.get_vpcid_of_vm(f"{cluster}-ctlplane-0")
        result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_api.yml', overrides=data)
        if result['result'] != 'success':
            return result
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
    if async_install:
        success(f"Kubernetes cluster {cluster} deployed!!!")
        info2(f"get kubeconfig from {cluster}-ctlplane-0 /root")
        return {'result': 'success'}
    success(f"Kubernetes cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
    if config.type in cloudplatforms and cloud_lb:
        if cloud_dns:
            wait_cloud_dns(cluster, domain)
        # elif api_ip is not None and api_ip == f'api.{cluster}.{domain}':
        else:
            for lbentry in config.list_loadbalancers():
                if lbentry[0] == f'api-{cluster}':
                    lb_ip = lbentry[1]
                    update_etc_hosts(cluster, domain, lb_ip)
                    break
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    apps = data.get('apps', [])
    if data.get('metallb', False) and 'metallb' not in apps:
        apps.append('metallb')
    if data.get('ingress', False) and 'ingress' not in apps:
        apps.append('ingress')
    if data.get('policy_as_code', False) and 'policy_as_code' not in apps:
        apps.append('policy_as_code')
    if data.get('autolabeller', False) and 'autolabeller' not in apps:
        apps.append('autolabeller')
    if apps:
        appdir = f"{plandir}/apps"
        os.environ["PATH"] = f'{os.getcwd()}:{os.environ["PATH"]}'
        for app in apps:
            app_data = data.copy()
            if not os.path.exists(appdir):
                warning(f"Skipping unsupported app {app}")
            else:
                pprint(f"Adding app {app}")
                if f'{app}_version' not in overrides:
                    app_data[f'{app}_version'] = 'latest'
                kube_create_app(config, app, appdir, overrides=app_data)
    if data['wait_ready']:
        pprint("Waiting for all nodes to join cluster")
        while True:
            if len(os.popen("kubectl get node -o name").readlines()) == ctlplanes + workers:
                break
            else:
                sleep(10)
    if autoscale:
        config.import_in_kube(network=network, secure=True)
        with NamedTemporaryFile(mode='w+t') as temp:
            commondir = os.path.dirname(pprint.__code__.co_filename)
            autoscale_overrides = {'cluster': cluster, 'kubetype': 'generic', 'workers': workers, 'replicas': 1}
            autoscale_data = config.process_inputfile(cluster, f"{commondir}/autoscale.yaml.j2",
                                                      overrides=autoscale_overrides)
            temp.write(autoscale_data)
            autoscalecmd = f"kubectl create -f {temp.name}"
            call(autoscalecmd, shell=True)
    if config.type in cloudplatforms and cloud_storage:
        if config.type == 'aws':
            pprint("Deploying cloud storage class")
            deploy_cloud_storage(config, cluster)
    return {'result': 'success'}
