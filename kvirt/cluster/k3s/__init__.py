from ipaddress import ip_network
from kvirt.common import error, success, pprint, warning, get_kubectl, info2, container_mode, create_app_generic
from kvirt.common import deploy_cloud_storage, wait_cloud_dns, update_etc_hosts, fix_typos, get_cluster_api_vips
from kvirt.common import wait_for_nodes
import os
import re
from random import choice
from shutil import which
from string import ascii_letters, digits
from subprocess import call, run
from tempfile import NamedTemporaryFile
from time import sleep
from yaml import safe_dump, safe_load

cloud_providers = ['aws', 'azure', 'gcp', 'ibm', 'hcloud']


def update_ip_alias(config, nodes):
    timeout = 0
    cmd_one = ['kubectl', 'get', 'nodes', '-o=jsonpath={range .items[?(@.spec.podCIDR)]}{.metadata.name}{\'\\n\'}{end}']
    while True:
        if timeout > 240:
            error(f"Timeout waiting for {nodes} nodes to have a Pod CIDR assigned")
            return
        pprint(f"Waiting 5s for {nodes} nodes to have a Pod CIDR assigned")
        result = run(cmd_one, capture_output=True, text=True)
        current_nodes = len(result.stdout.splitlines())
        if current_nodes == nodes:
            break
        else:
            sleep(5)
            timeout += 5
    for node in safe_load(os.popen("kubectl get node -o yaml").read())['items']:
        try:
            name, pod_cidr = node['metadata']['name'], node['spec']['podCIDR']
            config.k.update_aliases(name, pod_cidr)
        except KeyError as e:
            error(f"Hit Error: {e}")


def scale(config, plandir, cluster, overrides):
    storedparameters = overrides.get('storedparameters', True)
    provider = config.type
    plan = cluster
    data = {'cluster': cluster, 'domain': 'karmalabs.corp', 'image': 'ubuntu2004', 'kube': cluster, 'kubetype': 'k3s',
            'sdn': 'flannel', 'extra_scripts': [], 'cloud_native': False, 'ctlplanes': 1, 'workers': 0}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data['cluster']
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if storedparameters and os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    else:
        data['client'] = config.client
    data.update(overrides)
    data['scale'] = True
    cloud_native = data.get('cloud_native')
    cloud_lb = data.get('cloud_lb', provider in cloud_providers and data['ctlplanes'] > 1)
    data['cloud_lb'] = cloud_lb
    ctlplanes = data['ctlplanes']
    workers = data['workers']
    sdn = None if 'sdn' in overrides and overrides['sdn'] is None else data.get('sdn')
    client = config.client
    if 'api_ip' not in data:
        data['api_ip'] = None
    if 'first_ip' not in data or data['first_ip'] is None:
        first_info = config.k.info(f'{cluster}-ctlplane-0') or config.k.info(f'{cluster}-master-0')
        data['first_ip'] = first_info.get('private_ip') or first_info.get('ip')
    pprint(f"Scaling on client {client}")
    if os.path.exists(clusterdir):
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
            safe_dump(data, paramfile)
    vmrules_all_names = []
    if data.get('vmrules', config.vmrules) and data.get('vmrules_strict', config.vmrules_strict):
        vmrules_all_names = [list(entry.keys())[0] for entry in data.get('vmrules', config.vmrules)]
    for role in ['ctlplanes', 'workers']:
        install_k3s_args = []
        for arg in data:
            if arg.startswith('install_k3s'):
                install_k3s_args.append(f"{arg.upper()}={data[arg]}")
        overrides = data.copy()
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        if role == 'ctlplanes':
            if ctlplanes == 1:
                continue
            if provider not in cloud_providers and not cloud_lb\
               and ('virtual_router_id' not in overrides or 'auth_pass' not in overrides):
                warning("Scaling up of ctlplanes won't work without virtual_router_id and auth_pass")
            if sdn is None or sdn != 'flannel':
                install_k3s_args.append("INSTALL_K3S_EXEC='--flannel-backend=none'")
            install_k3s_args = ' '.join(install_k3s_args)
        if role == 'workers' and workers == 0:
            continue
        if vmrules_all_names:
            reg = re.compile(f'{cluster}-{role[:-1]}-[0-9]+')
            vmrules_names = [name for name in vmrules_all_names if reg.match(name)]
            if len(vmrules_names) != overrides.get(role, 1):
                warning(f"Adjusting {role} number to vmrule entries")
                overrides[role] = len(vmrules_names)
            overrides['vmrules_names'] = sorted(vmrules_names)
        overrides['install_k3s_args'] = install_k3s_args
        result = config.plan(plan, inputfile=f'{plandir}/{role}.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            return result
        else:
            pprint(f"{role.capitalize()} Nodes will join the cluster in the following minutes")
    if cloud_native and provider == 'gcp':
        pprint("Updating ip alias ranges")
        update_ip_alias(config, ctlplanes + workers)
    return {'result': 'success'}


def create(config, plandir, cluster, overrides):
    provider = config.type
    k = config.k
    data = safe_load(open(f'{plandir}/kcli_default.yml'))
    data.update(overrides)
    fix_typos(data)
    storedparameters = data.get('storedparameters', True)
    cloud_dns = data['cloud_dns']
    data['cloud_lb'] = overrides.get('cloud_lb', provider in cloud_providers and data['ctlplanes'] > 1)
    cloud_lb = data['cloud_lb']
    cloud_storage = data['cloud_storage']
    cloud_native = data['cloud_native']
    data['cluster'] = cluster
    plan = cluster
    data['kube'] = data['cluster']
    data['kubetype'] = 'k3s'
    autoscale = data['autoscale']
    ctlplanes = data['ctlplanes']
    workers = data['workers']
    network = data['network']
    sdn = None if 'sdn' in overrides and overrides['sdn'] is None else data.get('sdn')
    domain = data['domain']
    image = data['image']
    api_ip = data.get('api_ip')
    if ctlplanes > 1:
        if provider in cloud_providers:
            if not cloud_lb:
                msg = "Multiple ctlplanes require cloud_lb to be set to True"
                return {'result': 'failure', 'reason': msg}
            elif api_ip is None:
                api_ip = f"api.{cluster}.{domain}"
                data['api_ip'] = api_ip
        elif api_ip is None:
            networkinfo = k.info_network(network)
            if provider == 'kvm' and networkinfo['type'] == 'routed':
                vip_mappings = get_cluster_api_vips()
                cidr = networkinfo['cidr']
                if cidr == 'N/A':
                    msg = "Couldnt gather an api_ip from your specified network"
                    return {'result': 'failure', 'reason': msg}
                api_index = 2 if ':' in cidr else -3
                if network in vip_mappings:
                    api_index -= api_index + vip_mappings[network] if ':' in cidr else api_index - vip_mappings[network]
                api_ip = str(ip_network(cidr)[api_index])
                warning(f"Using {api_ip} as api_ip")
                data['api_ip'] = api_ip
                data['automatic_api_ip'] = True
            elif provider == 'kubevirt':
                selector = {'kcli/plan': plan, 'kcli/role': 'ctlplane'}
                api_ip = config.k.create_service(f"{cluster}-api", config.k.namespace, selector,
                                                 _type="LoadBalancer", ports=[6443])
                if api_ip is None:
                    msg = "Couldnt get an kubevirt api_ip from service"
                    return {'result': 'failure', 'reason': msg}
                else:
                    pprint(f"Using api_ip {api_ip}")
                    data['api_ip'] = api_ip
            else:
                msg = "You need to define api_ip in your parameters file"
                return {'result': 'failure', 'reason': msg}
        if not cloud_lb and ctlplanes > 1:
            if data.get('virtual_router_id') is None:
                data['virtual_router_id'] = hash(data['cluster']) % 254 + 1
                pprint(f"Using keepalived virtual_router_id {data['virtual_router_id']}")
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
        msg = f"Remove existing directory {clusterdir} or use --force"
        return {'result': 'failure', 'reason': msg}
    if which('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
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
        return result
    first_info = config.k.info(f'{cluster}-ctlplane-0')
    first_ip = first_info.get('private_ip') or first_info.get('ip')
    data['first_ip'] = first_ip
    if storedparameters:
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['client'] = config.client
            installparam['cluster'] = cluster
            installparam['api_ip'] = api_ip
            installparam['first_ip'] = first_ip
            installparam['plan'] = plan
            installparam['kubetype'] = 'k3s'
            installparam['image'] = image
            if not cloud_lb and ctlplanes > 1:
                installparam['virtual_router_id'] = data['virtual_router_id']
                installparam['auth_pass'] = data['auth_pass']
            if 'automatic_api_ip' in data:
                installparam['automatic_api_ip'] = True
            safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
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
    if cloud_lb and provider in cloud_providers:
        if cloud_dns:
            config.k.delete_dns(f'api.{cluster}', domain=domain)
        if provider == 'aws':
            data['vpcid'] = config.k.get_vpcid_of_vm(f"{cluster}-ctlplane-0")
        result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_api.yml', overrides=data)
        if result['result'] != 'success':
            return result
    success(f"K3s cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
    if provider in cloud_providers and cloud_lb:
        if cloud_dns:
            wait_cloud_dns(cluster, domain)
        elif api_ip is not None and api_ip == f'api.{cluster}.{domain}':
            for lbentry in config.list_loadbalancers():
                if lbentry[0] == f'api-{cluster}':
                    lb_ip = lbentry[1]
                    update_etc_hosts(cluster, domain, lb_ip)
                    break
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    apps = data.get('apps', [])
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
                create_app_generic(config, app, appdir, overrides=app_data)
    if ctlplanes + workers > 1:
        ready = wait_for_nodes(ctlplanes + workers)
        if not ready:
            msg = "Timeout waiting for all nodes to join"
            return {'result': 'failure', 'reason': msg}
    if autoscale:
        config.import_in_kube(network=network, secure=True)
        with NamedTemporaryFile(mode='w+t') as temp:
            commondir = os.path.dirname(pprint.__code__.co_filename)
            autoscale_overrides = {'cluster': cluster, 'kubetype': 'k3s', 'workers': workers, 'replicas': 1}
            autoscale_data = config.process_inputfile(cluster, f"{commondir}/autoscale.yaml.j2",
                                                      overrides=autoscale_overrides)
            temp.write(autoscale_data)
            autoscalecmd = f"kubectl create -f {temp.name}"
            call(autoscalecmd, shell=True)
    if provider in cloud_providers:
        if cloud_storage and provider == 'aws':
            pprint("Deploying cloud storage class")
            deploy_cloud_storage(config, cluster)
        if cloud_native and provider == 'gcp':
            pprint("Updating ip alias ranges")
            update_ip_alias(config, ctlplanes + workers)
    return {'result': 'success'}
