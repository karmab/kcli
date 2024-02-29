#!/usr/bin/env python

from base64 import b64encode
from glob import glob
from ipaddress import ip_network
from kvirt.common import success, error, pprint, info2, container_mode, warning, fix_typos
from kvirt.common import get_oc, pwd_path, get_installer_rhcos, get_ssh_pub_key, start_baremetal_hosts, olm_app
from kvirt.common import deploy_cloud_storage
from kvirt.defaults import OPENSHIFT_TAG
from kvirt.cluster.openshift import get_ci_installer, get_downstream_installer, get_installer_version
from kvirt.cluster.openshift import same_release_images, process_apps, update_openshift_etc_hosts, offline_image
import json
import os
import re
import socket
import sys
from shutil import which, copy2
from subprocess import call
from tempfile import TemporaryDirectory, NamedTemporaryFile
from time import sleep
from uuid import UUID
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import yaml

virt_providers = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere', 'proxmox']
cloud_providers = ['aws', 'azure', 'gcp', 'ibm']


def valid_uuid(uuid):
    try:
        UUID(uuid)
        return True
    except:
        return False


def get_info(url, user, password):
    match = re.match('.*/redfish/v1/Systems/(.*)', url)
    if '/redfish/v1/Systems' in url and\
       (valid_uuid(os.path.basename(url)) or (match is not None and len(match.group(1).split('/')) == 2)):
        model = 'virtual'
        user = user or 'fake'
        password = password or 'fake'
        url = url.replace('http', 'redfish-virtualmedia+http')
        return url, user, password
    oem_url = f"https://{url}" if '://' not in url else url
    p = urlparse(oem_url)
    headers = {'Accept': 'application/json'}
    request = Request(f"https://{p.netloc}/redfish/v1", headers=headers)
    oem = json.loads(urlopen(request).read())['Oem']
    model = "dell" if 'Dell' in oem else "hp" if 'Hpe' in oem else 'supermicro' if 'Supermicro' in oem else 'N/A'
    if '://' not in url:
        if model in ['hp', 'supermicro']:
            url = f"https://{url}/redfish/v1/Systems/1"
        elif model == 'dell':
            url = f"https://{url}/redfish/v1/Systems/System.Embedded.1"
            user = user or 'root'
            password = password or 'calvin'
        else:
            print(f"Invalid url {url}")
            sys.exit(0)
    if model in ['hp', 'hpe', 'supermicro']:
        url = url.replace('https://', 'redfish-virtualmedia')
    elif model == 'dell':
        url = url.replace('https://', 'idrac-virtualmedia')
    return url, user, password


def create_bmh_objects(config, plandir, cluster, namespace, baremetal_hosts, overrides={}):
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    uefi = overrides.get('uefi', False)
    nmstatedata = ''
    with open(f"{clusterdir}/bmcs.yml", 'w') as f:
        for index, host in enumerate(baremetal_hosts):
            bmc_url = host.get('url') or host.get('bmc_url')
            if bmc_url is None:
                warning("Skipping entry {index} in baremetal_hosts array as it misses url")
                continue
            bmc_user = host.get('username') or host.get('user') or host.get('bmc_username') or host.get('bmc_user')\
                or overrides.get('bmc_user') or overrides.get('bmc_username')\
                or overrides.get('user') or overrides.get('username')
            bmc_password = host.get('password') or host.get('bmc_password') or overrides.get('bmc_password')
            bmc_mac = host.get('mac') or host.get('bmc_mac')
            if bmc_mac is None:
                warning("Skipping entry {index} in baremetal_hosts array as it misses mac")
                continue
            bmc_uefi = host.get('uefi') or host.get('bmc_uefi') or uefi
            bmc_name = host.get('name') or host.get('bmc_name') or f'{cluster}-node-{index}'
            bmc_url, bmc_user, bmc_password = get_info(bmc_url, bmc_user, bmc_password)
            bmc_overrides = {'url': bmc_url, 'user': bmc_user, 'password': bmc_password, 'name': bmc_name,
                             'uefi': bmc_uefi, 'namespace': namespace, 'cluster': cluster,
                             'mac': bmc_mac}
            bmc_data = config.process_inputfile(cluster, f"{plandir}/bmc.yml.j2", overrides=bmc_overrides)
            f.write(bmc_data)
            if 'addresses' in host:
                host_data = host.copy()
                host_data['name'] = bmc_name
                host_data['cluster'] = cluster
                host_data['namespace'] = namespace
                if 'dns_resolver' not in host_data:
                    warning("Skipping nmstate for entry {index} as dns_resolver isnt defined")
                    continue
                nmstatedata += config.process_inputfile(cluster, f'{plandir}/nmstateconfig.yml.j2', overrides=host_data)
                nmstatedata += '---\n'
    bmccmd = f"oc create -f {clusterdir}/bmcs.yml"
    call(bmccmd, shell=True)
    if nmstatedata != '':
        with open(f"{clusterdir}/nmstateconfig.yml", 'w') as f:
            f.write(nmstatedata)
        nmcmd = f"oc create -f {clusterdir}/nmstateconfig.yml"
        call(nmcmd, shell=True)


def handle_baremetal_iso(config, plandir, cluster, data, baremetal_hosts=[]):
    baremetal_iso_overrides = data.copy()
    baremetal_iso_overrides['noname'] = True
    baremetal_iso_overrides['workers'] = 1
    result = config.plan(cluster, inputfile=f'{plandir}/kcli_plan.yml', overrides=baremetal_iso_overrides,
                         onlyassets=True)
    iso_data = result['assets'][0]
    with open('iso.ign', 'w') as f:
        f.write(iso_data)
    iso_pool = data.get('pool') or config.pool
    config.create_openshift_iso(cluster, ignitionfile='iso.ign', installer=True)
    if baremetal_hosts:
        iso_pool_path = config.k.get_pool_path(iso_pool)
        chmodcmd = f"chmod 666 {iso_pool_path}/{cluster}-worker.iso"
        call(chmodcmd, shell=True)
        pprint("Creating httpd deployment to host iso for baremetal workers")
        httpdcmd = f"oc create -f {plandir}/httpd.yaml"
        call(httpdcmd, shell=True)
        svcip_cmd = 'oc get node -o yaml'
        svcip = yaml.safe_load(os.popen(svcip_cmd).read())['items'][0]['status']['addresses'][0]['address']
        svcport_cmd = 'oc get svc -n default httpd-kcli-svc -o yaml'
        svcport = yaml.safe_load(os.popen(svcport_cmd).read())['spec']['ports'][0]['nodePort']
        podname = os.popen('oc -n default get pod -l app=httpd-kcli -o name').read().split('/')[1].strip()
        try:
            call(f"oc wait -n default --for=condition=Ready pod/{podname}", shell=True)
        except Exception as e:
            error(f"Hit {e}")
            sys.exit(1)
        copycmd = f"oc -n default cp {iso_pool_path}/{cluster}-worker.iso {podname}:/var/www/html"
        call(copycmd, shell=True)
        return f'http://{svcip}:{svcport}/{cluster}-worker.iso'


def scale(config, plandir, cluster, overrides):
    provider = config.type
    plan = cluster
    data = {'cluster': cluster, 'kube': cluster, 'kubetype': 'hypershift', 'namespace': 'clusters', 'assisted': False,
            'kubevirt': False}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data['cluster']
    namespace = data['namespace']
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if not os.path.exists(clusterdir):
        warning(f"Creating {clusterdir} from your input (auth creds will be missing)")
        data['client'] = config.client
        overrides['cluster'] = cluster
        overrides['clusterdir'] = clusterdir
        plan = overrides.get('plan') or plan
        if 'ingress_ip' not in overrides and provider != 'kubevirt':
            msg = "Missing ingress_ip..."
            return {'result': 'failure', 'reason': msg}
        domain = overrides.get('domain')
        if domain is None:
            msg = "Missing domain..."
            return {'result': 'failure', 'reason': msg}
        if 'management_ingress_domain' not in overrides:
            overrides['management_ingress_domain'] = f'apps.{cluster}.{domain}'
        os.mkdir(clusterdir)
        ignitionscript = config.process_inputfile(cluster, f"{plandir}/ignition.sh", overrides=overrides)
        with open(f"{clusterdir}/ignition.sh", 'w') as f:
            f.write(ignitionscript)
        call(f'bash {clusterdir}/ignition.sh', shell=True)
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    assisted = data['assisted']
    kubevirt = data['kubevirt']
    with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
        yaml.safe_dump(data, paramfile)
    pprint(f"Scaling on client {config.client}")
    worker_overrides = data.copy()
    workers = worker_overrides.get('workers', 2)
    if kubevirt:
        # kubeconfig = data['kubeconfig']
        # os.environ['KUBECONFIG'] = kubeconfig
        cmcmd = f"oc -n {namespace}-{cluster} scale nodepool {cluster} --replicas {workers}"
        call(cmcmd, shell=True)
        return {'result': 'success'}
    os.chdir(os.path.expanduser("~/.kcli"))
    old_baremetal_hosts = installparam.get('baremetal_hosts', [])
    new_baremetal_hosts = overrides.get('baremetal_hosts', [])
    baremetal_hosts = [entry for entry in new_baremetal_hosts if entry not in old_baremetal_hosts]
    if baremetal_hosts:
        if assisted:
            create_bmh_objects(config, plandir, cluster, namespace, baremetal_hosts, overrides)
            cmcmd = f"oc -n {namespace}-{cluster} scale nodepool {cluster} --replicas {workers}"
            call(cmcmd, shell=True)
            return {'result': 'success'}
        else:
            if not old_baremetal_hosts:
                iso_url = handle_baremetal_iso(config, plandir, cluster, data, baremetal_hosts)
            else:
                svcip_cmd = 'oc get node -o yaml'
                svcip = yaml.safe_load(os.popen(svcip_cmd).read())['items'][0]['status']['addresses'][0]['address']
                svcport_cmd = 'oc get svc -n default httpd-kcli-svc -o yaml'
                svcport = yaml.safe_load(os.popen(svcport_cmd).read())['spec']['ports'][0]['nodePort']
                iso_url = f'http://{svcip}:{svcport}/{cluster}-worker.iso'
            start_baremetal_hosts(baremetal_hosts, iso_url, overrides=overrides, debug=config.debug)
            worker_overrides['workers'] = workers - len(new_baremetal_hosts)
    if worker_overrides.get('workers', 2) <= 0:
        return {'result': 'success'}
    threaded = data.get('threaded', False) or data.get('workers_threaded', False)
    return config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=worker_overrides, threaded=threaded)


def create(config, plandir, cluster, overrides):
    log_level = 'debug' if config.debug else 'info'
    k = config.k
    provider = config.type
    arch = k.get_capabilities()['arch'] if provider == 'kvm' else 'x86_64'
    arch_tag = 'arm64' if arch in ['aarch64', 'arm64'] else 'latest'
    overrides['arch_tag'] = arch_tag
    if 'KUBECONFIG' not in os.environ:
        warning("KUBECONFIG not set...Using .kube/config instead")
    elif not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
        if not os.path.exists(os.environ['KUBECONFIG']):
            msg = "Kubeconfig not found. Leaving..."
            return {'result': 'failure', 'reason': msg}
    data = {'kubetype': 'hypershift',
            'domain': 'karmalabs.corp',
            'platform': None,
            'baremetal_iso': False,
            'baremetal_hosts': [],
            'coredns': True,
            'mdns': False,
            'network': 'default',
            'etcd_size': 4,
            'workers': 2,
            'apps': [],
            'async': False,
            'notify': False,
            'tag': OPENSHIFT_TAG,
            'version': 'stable',
            'network_type': 'OVNKubernetes',
            'fips': False,
            'operator_image': 'quay.io/hypershift/hypershift-operator:latest',
            'mce': True,
            'namespace': 'clusters',
            'pull_secret': 'openshift_pull.json',
            'sslip': False,
            'kubevirt_ingress_service': False,
            'dualstack': False,
            'ipv6': False,
            'cluster_networks': [],
            'service_networks': [],
            'cluster_network_ipv4': '10.129.0.0/14',
            'service_network_ipv4': '172.31.0.0/16',
            'cluster_network_ipv6': "fd03::/48",
            'service_network_ipv6': "fd04::/112",
            'autoscale': False,
            'mce': True,
            'mce_assisted': False,
            'calico_version': None,
            'cilium_version': None,
            'hosted_tag': None,
            'hosted_ha': False,
            'hosted_version': None,
            'image_overrides': None,
            'retries': 3}
    data.update(overrides)
    fix_typos(data)
    retries = data.get('retries')
    if 'cluster' in overrides:
        clustervalue = overrides.get('cluster')
    elif cluster is not None:
        clustervalue = cluster
    else:
        clustervalue = 'myhypershift'
    data['cluster'] = clustervalue
    data['kube'] = data['cluster']
    ignore_hosts = data.get('ignore_hosts', False)
    pprint(f"Deploying cluster {clustervalue}")
    plan = cluster if cluster is not None else clustervalue
    platform = data.get('platform')
    assisted = platform == 'assisted'
    data['assisted'] = assisted
    kubevirt = platform == 'kubevirt'
    data['kubevirt'] = kubevirt
    if platform not in [None, 'kubevirt', 'assisted']:
        msg = "Incorrect platform. Choose between None, kubevirt and assisted"
        return {'result': 'failure', 'reason': msg}
    baremetal_iso = data.get('baremetal_iso', False)
    baremetal_hosts = data.get('baremetal_hosts')
    async_install = data.get('async')
    notify = data.get('notify')
    autoscale = data.get('autoscale')
    sslip = data.get('sslip')
    domain = data.get('domain')
    original_domain = domain
    data['original_domain'] = domain
    apps = overrides.get('apps', [])
    workers = data.get('workers')
    version = data.get('version')
    coredns = data.get('coredns')
    tag = data.get('tag')
    if str(tag) == '4.1':
        tag = '4.10'
        data['tag'] = tag
    pull_secret = os.path.expanduser(pwd_path(data.get('pull_secret')))
    if not os.path.exists(pull_secret):
        msg = f"Missing pull secret file {pull_secret}"
        return {'result': 'failure', 'reason': msg}
    network_type = data['network_type']
    if network_type not in ['Calico', 'OVNKubernetes']:
        data['network_type'] = 'Other'
    cluster = data.get('cluster')
    namespace = data.get('namespace')
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        msg = f"Remove existing directory {clusterdir} or use --force"
        return {'result': 'failure', 'reason': msg}
    else:
        os.makedirs(f"{clusterdir}/auth")
    if which('oc') is None:
        get_oc()
    default_sc = False
    for sc in yaml.safe_load(os.popen('oc get sc -o yaml').read())['items']:
        if 'annotations' in sc['metadata']\
           and 'storageclass.kubernetes.io/is-default-class' in sc['metadata']['annotations']\
           and sc['metadata']['annotations']['storageclass.kubernetes.io/is-default-class'] == 'true':
            pprint(f"Using default class {sc['metadata']['name']}")
            default_sc = True
    if not default_sc:
        msg = "Default Storage class not found. Leaving..."
        return {'result': 'failure', 'reason': msg}
    kubeconfig = os.environ.get('KUBECONFIG')
    kubeconfigdir = os.path.dirname(kubeconfig) if kubeconfig is not None else os.path.expanduser("~/.kube")
    kubeconfig = os.path.basename(kubeconfig) if kubeconfig is not None else 'config'
    hosted_crd_cmd = 'oc get crd hostedclusters.hypershift.openshift.io -o yaml 2>/dev/null'
    assisted_crd_cmd = 'oc -n multicluster-engine get pod -l app=assisted-service -o name 2>/dev/null'
    if yaml.safe_load(os.popen(hosted_crd_cmd).read()) is None\
       or (assisted and yaml.safe_load(os.popen(assisted_crd_cmd).read()) is None):
        warning("Hypershift not fully installed. Installing it for you")
        if data['mce'] or assisted:
            mce_assisted = assisted or data['mce_assisted']
            app_name, source, channel, csv, description, x_namespace, channels, crds = olm_app('multicluster-engine')
            app_data = {'name': app_name, 'source': source, 'channel': channel, 'namespace': x_namespace, 'csv': csv,
                        'mce_hypershift': True, 'assisted': mce_assisted, 'version': version, 'tag': tag}
            config.create_app_openshift(app_name, app_data)
            sleep(240)
        elif which('podman') is None:
            msg = "Please install podman first in order to install hypershift"
            return {'result': 'failure', 'reason': msg}
        else:
            hypercmd = f"podman pull {data['operator_image']}"
            call(hypercmd, shell=True)
            hypercmd = "podman run -it --rm --security-opt label=disable --entrypoint=/usr/bin/hypershift "
            hypercmd += f"-e KUBECONFIG=/k/{kubeconfig} -v {kubeconfigdir}:/k {data['operator_image']} install"
            hypercmd += f" --hypershift-image {data['operator_image']}"
            call(hypercmd, shell=True)
            sleep(120)
    if yaml.safe_load(os.popen(hosted_crd_cmd).read()) is None:
        msg = "Couldnt install hypershift properly"
        return {'result': 'failure', 'reason': msg}
    elif assisted and yaml.safe_load(os.popen(assisted_crd_cmd).read()) is None:
        msg = "Couldnt install assisted properly"
        return {'result': 'failure', 'reason': msg}
    registry = 'quay.io'
    management_image = os.popen("oc get clusterversion version -o jsonpath='{.status.desired.image}'").read()
    prefixes = ['quay.io', 'registry.ci']
    fake_disconnected = overrides.get('fake_disconnected', False)
    if not fake_disconnected and not any(management_image.startswith(p) for p in prefixes):
        disconnected_url = management_image.split('/')[0]
        data['registry'] = disconnected_url
        if disconnected_url not in open(pull_secret).read():
            msg = f"entry for {disconnected_url} missing in pull secret"
            error(msg)
            return {'result': 'failure', 'reason': msg}
        hypershift_info = f"oc adm release info --insecure --pullspecs -a {pull_secret} | "
        hypershift_info += "grep hypershift | awk '{print $2}' | cut -d@ -f2"
        hypershift_tag = os.popen(hypershift_info).read().strip()
        mco_info = f"oc adm release info --insecure --pullspecs -a {pull_secret} | "
        mco_info += "grep machine-config-operator | awk '{print $2'} | cut -d@ -f2"
        mco_tag = os.popen(mco_info).read().strip()
        disconnected_data = {'disconnected_url': disconnected_url, 'hypershift_tag': hypershift_tag, 'mco_tag': mco_tag}
        disconnectedfile = config.process_inputfile(cluster, f"{plandir}/disconnected.sh", overrides=disconnected_data)
        with open(f"{clusterdir}/disconnected.sh", 'w') as f:
            f.write(disconnectedfile)
        call(f'bash {clusterdir}/disconnected.sh', shell=True)
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = management_image
        cacmd = "oc -n openshift-config get cm user-ca-bundle -o jsonpath='{.data.ca-bundle\\.crt}'"
        data['ca'] = os.popen(cacmd).read().strip()
        data['operator_disconnected_image'] = f'{disconnected_url}/openshift/release@{hypershift_tag}'
    data['registry'] = registry
    data['basedir'] = '/workdir' if container_mode() else '.'
    supported_data = yaml.safe_load(os.popen("oc get cm/supported-versions -o yaml -n hypershift").read())
    if supported_data is not None:
        supported_data = supported_data['data']
        supported_versions = supported_versions = supported_data['supported-versions']
        versions = yaml.safe_load(supported_versions)['versions']
        if version == 'latest':
            tag = versions[0]
        elif str(tag) not in versions:
            msg = f"Invalid tag {tag}. Choose between {','.join(versions)}"
            return {'result': 'failure', 'reason': msg}
    else:
        warning(f"Couldnt verify whether {tag} is a valid tag")
    management_cmd = "oc get ingresscontroller -n openshift-ingress-operator default -o jsonpath='{.status.domain}'"
    management_ingress_domain = os.popen(management_cmd).read()
    data['management_ingress_domain'] = management_ingress_domain
    management_ingress_ip = data.get('management_ingress_ip')
    if management_ingress_ip is None:
        try:
            management_ingress_ip = socket.getaddrinfo('xxx.' + management_ingress_domain, 80,
                                                       proto=socket.IPPROTO_TCP)[0][4][0]
            data['management_ingress_ip'] = management_ingress_ip
        except:
            warning("Couldn't figure out management ingress ip. Using node port instead")
            data['nodeport'] = True
    management_api_ip = data.get('management_api_ip')
    if management_api_ip is None:
        management_ips_cmd = "oc get nodes --no-headers -o jsonpath=\"{.items[*]['status.addresses'][0]['address']}\""
        management_ips = os.popen(management_ips_cmd).read().split(' ')
        if len(management_ips) == 1:
            management_api_ip = management_ips[0]
        else:
            management_api_url = os.popen("oc whoami --show-server").read()
            management_api_domain = urlparse(management_api_url).hostname
            management_api_ip = socket.getaddrinfo(management_api_domain, 6443, proto=socket.IPPROTO_TCP)[0][4][0]
        data['management_api_ip'] = management_api_ip
    pprint(f"Using {management_api_ip} as management api ip")
    pub_key = data.get('pub_key')
    data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
    pub_key = data.get('pub_key') or get_ssh_pub_key()
    keys = data.get('keys', [])
    if pub_key is None:
        if keys:
            warning("Using first key from your keys array")
            pub_key = keys[0]
        else:
            msg = "No usable public key found, which is required for the deployment. Create one using ssh-keygen"
            return {'result': 'failure', 'reason': msg}
    pub_key = os.path.expanduser(pub_key)
    if pub_key.startswith('ssh-'):
        data['pub_key'] = pub_key
    elif os.path.exists(pub_key):
        data['pub_key'] = open(pub_key).read().strip()
    else:
        msg = f"Publickey file {pub_key} not found"
        return {'result': 'failure', 'reason': msg}
    network = data.get('network')
    ingress_ip = data.get('ingress_ip')
    virtual_router_id = None
    if ingress_ip is None:
        networkinfo = k.info_network(network)
        if provider == 'kubevirt' or kubevirt:
            domain = management_ingress_domain
            data['domain'] = domain
            pprint(f"Setting domain to {domain}")
            try:
                cmcmd = "oc patch ingresscontroller -n openshift-ingress-operator default --type=json -p "
                cmcmd += "'[{ \"op\": \"add\", \"path\": \"/spec/routeAdmission\", "
                cmcmd += "\"value\": {wildcardPolicy: \"WildcardsAllowed\"}}]'"
                call(cmcmd, shell=True)
            except:
                warning("Couldnt patch ingresscontroller to support wildcards. Assuming it's configured properly")
            if not kubevirt:
                selector = {'kcli/plan': plan, 'kcli/role': 'worker'}
                service_type = "LoadBalancer" if k.access_mode == 'LoadBalancer' else 'NodePort'
                ingress_ip = k.create_service(f"{cluster}-ingress", k.namespace, selector, _type=service_type,
                                              ports=[80, 443])
                if service_type == 'NodePort':
                    hostname = f"http.apps.{cluster}.{management_ingress_domain}"
                    route_cmd = f"oc -n {k.namespace} create route passthrough --service={cluster}-ingress "
                    route_cmd += f"--hostname={hostname} --wildcard-policy=Subdomain --port=443"
                    call(route_cmd, shell=True)
                elif ingress_ip is None:
                    msg = f"Couldnt gather an ingress_ip from network {network}"
                    return {'result': 'failure', 'reason': msg}
        elif provider == 'kvm' and networkinfo['type'] == 'routed':
            cidr = networkinfo['cidr']
            ingress_index = 3 if ':' in cidr else -4
            ingress_ip = str(ip_network(cidr)[ingress_index])
            warning(f"Using {ingress_ip} as ingress_ip")
            data['ingress_ip'] = ingress_ip
        else:
            msg = "You need to define ingress_ip in your parameters file"
            return {'result': 'failure', 'reason': msg}
    elif kubevirt:
        warning(f"Note that ingress_ip {ingress_ip} won't be configured as you're using kubevirt provider")
    if ingress_ip is not None and data.get('virtual_router_id') is None:
        virtual_router_id = hash(cluster) % 254 + 1
        data['virtual_router_id'] = virtual_router_id
        pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
    if ingress_ip is not None and sslip and provider in virt_providers:
        domain = f"{ingress_ip.replace('.', '-').replace(':', '-')}.sslip.io"
        data['domain'] = domain
        pprint(f"Setting domain to {domain}")
        ignore_hosts = False
    assetsdata = data.copy()
    copy2(f'{kubeconfigdir}/{kubeconfig}', f"{clusterdir}/kubeconfig.mgmt")
    cidr = data.get('cidr', '192.168.122.0/24')
    assetsdata['cidr'] = cidr
    ipv6 = ':' in cidr
    data['ipv6'] = ipv6
    pprint("Creating control plane assets")
    cmcmd = f"oc create ns {namespace} -o yaml --dry-run=client | oc apply -f -"
    call(cmcmd, shell=True)
    icsps = yaml.safe_load(os.popen('oc get imagecontentsourcepolicies -o yaml').read())['items']
    if not fake_disconnected and icsps:
        imagecontentsources = []
        for icsp in icsps:
            for mirror_spec in icsp['spec']['repositoryDigestMirrors']:
                source, mirror = mirror_spec['source'], mirror_spec['mirrors'][0]
                imagecontentsources.append({'source': source, 'mirror': mirror})
        assetsdata['imagecontentsources'] = imagecontentsources
    manifests = []
    manifestsdir = pwd_path("manifests")
    if os.path.exists(manifestsdir) and os.path.isdir(manifestsdir):
        for f in glob(f"{manifestsdir}/*.y*ml"):
            mc_name = os.path.basename(f).replace('.yaml', '').replace('.yml', '')
            mc_data = yaml.safe_load(open(f))
            if mc_data.get('kind', 'xx') == 'MachineConfig':
                pprint(f"Injecting manifest {f}")
                mc_data = json.dumps(mc_data)
                manifests.append({'name': mc_name, 'data': mc_data})
    if assisted:
        keepalived_yml_data = config.process_inputfile(cluster, f"{plandir}/staticpods/keepalived.yml", overrides=data)
        keepalived_yml_data = b64encode(keepalived_yml_data.encode()).decode("UTF-8")
        keepalived_conf_data = config.process_inputfile(cluster, f"{plandir}/keepalived.conf", overrides=data)
        keepalived_conf_data = b64encode(keepalived_conf_data.encode()).decode("UTF-8")
        assisted_data = {'keepalived_yml_data': keepalived_yml_data, 'keepalived_conf_data': keepalived_conf_data}
        if not sslip and coredns:
            coredns_yml_data = config.process_inputfile(cluster, f"{plandir}/staticpods/coredns.yml", overrides=data)
            coredns_yml_data = b64encode(coredns_yml_data.encode()).decode("UTF-8")
            assisted_data['coredns_yml_data'] = coredns_yml_data
            coredns_conf_data = config.process_inputfile(cluster, f"{plandir}/Corefile", overrides=data)
            coredns_conf_data = b64encode(coredns_conf_data.encode()).decode("UTF-8")
            assisted_data['coredns_conf_data'] = coredns_conf_data
            force_dns_data = config.process_inputfile(cluster, f"{plandir}/99-forcedns", overrides=data)
            force_dns_data = b64encode(force_dns_data.encode()).decode("UTF-8")
            assisted_data['force_dns_data'] = force_dns_data
        assisted_data['cluster'] = cluster
        assisted_data['sslip'] = sslip
        assisted_data['coredns'] = coredns
        assisted_data = config.process_inputfile(cluster, f'{plandir}/assisted_ingress.yml', overrides=assisted_data)
        assisted_data = json.dumps(assisted_data)
        manifests.append({'name': f'assisted-ingress-{cluster}', 'data': assisted_data})
    if manifests:
        assetsdata['manifests'] = manifests
    async_files = []
    async_tempdir = TemporaryDirectory()
    asyncdir = async_tempdir.name
    if notify:
        notifycmd = "cat /shared/results.txt"
        notifycmds, mailcontent = config.handle_notifications(cluster, notifymethods=config.notifymethods,
                                                              pushbullettoken=config.pushbullettoken,
                                                              notifycmd=notifycmd, slackchannel=config.slackchannel,
                                                              slacktoken=config.slacktoken,
                                                              mailserver=config.mailserver,
                                                              mailfrom=config.mailfrom, mailto=config.mailto,
                                                              cluster=True)
        notifyfile = f"{plandir}/99-notifications.yaml"
        notifyfile = config.process_inputfile(cluster, notifyfile, overrides={'registry': registry,
                                                                              'cluster': cluster,
                                                                              'domain': original_domain,
                                                                              'cmds': notifycmds,
                                                                              'mailcontent': mailcontent})
        with open(f"{asyncdir}/99-notifications.yaml", 'w') as f:
            f.write(notifyfile)
        async_files.append({'path': '/etc/kubernetes/99-notifications.yaml',
                            'origin': f"{asyncdir}/99-notifications.yaml"})
    if async_install:
        if apps:
            autolabeller = False
            final_apps = []
            for a in apps:
                if isinstance(a, str) and a == 'users' or (isinstance(a, dict) and a.get('name', '') == 'users'):
                    continue
                elif isinstance(a, str) and a == 'autolabeller'\
                        or (isinstance(a, dict) and a.get('name', '') == 'autolabeller'):
                    autolabeller = True
                elif isinstance(a, str) and a != 'nfs':
                    final_apps.append(a)
                elif isinstance(a, dict) and 'name' in a:
                    final_apps.append(a['name'])
                else:
                    error(f"Invalid app {a}. Skipping")
            appsfile = f"{plandir}/99-apps.yaml"
            apps_data = {'registry': registry, 'apps': final_apps, overrides: yaml.dump(overrides)}
            appsfile = config.process_inputfile(cluster, appsfile, overrides=apps_data)
            with open(f"{asyncdir}/99-apps.yaml", 'w') as f:
                f.write(appsfile)
            async_files.append({'path': '/etc/kubernetes/99-apps.yaml',
                                'origin': f"{asyncdir}/99-apps.yaml"})
            appdir = f"{plandir}/apps"
            apps_namespace = {'advanced-cluster-management': 'open-cluster-management',
                              'multicluster-engine': 'multicluster-engine', 'kubevirt-hyperconverged': 'openshift-cnv',
                              'local-storage-operator': 'openshift-local-storage',
                              'ocs-operator': 'openshift-storage', 'odf-lvm-operator': 'openshift-storage',
                              'odf-operator': 'openshift-storage', 'metallb-operator': 'openshift-operators',
                              'autolabeller': 'autorules'}
            if autolabeller:
                final_apps.append('autolabeller')
            for appname in final_apps:
                app_data = data.copy()
                if data.get('apps_install_cr') and os.path.exists(f"{appdir}/{appname}/cr.yml"):
                    app_data['namespace'] = apps_namespace[appname]
                    if original_domain is not None:
                        app_data['domain'] = original_domain
                    cr_content = config.process_inputfile(cluster, f"{appdir}/{appname}/cr.yml", overrides=app_data)
                    rendered = config.process_inputfile(cluster, f"{plandir}/99-apps-cr.yaml",
                                                        overrides={'registry': registry,
                                                                   'app': appname,
                                                                   'cr_content': cr_content})
                    with open(f"{asyncdir}/99-apps-cr.yaml", 'w') as f:
                        f.write(rendered)
                    async_files.append({'path': '/etc/kubernetes/99-app-cr.yaml',
                                        'origin': f"{asyncdir}/99-apps-cr.yaml"})
        if autoscale:
            config.import_in_kube(network=network, dest=f"{clusterdir}", secure=True)
            for entry in ["99-kcli-conf-cm.yaml", "99-kcli-ssh-cm.yaml"]:
                async_files.append({'path': f'/etc/kubernetes/{entry}', 'origin': f"{clusterdir}/{entry}"})
            commondir = os.path.dirname(pprint.__code__.co_filename)
            autoscale_overrides = {'cluster': cluster, 'kubetype': 'hypershift', 'workers': workers, 'replicas': 1,
                                   'sa': 'default'}
            autoscale_data = config.process_inputfile(cluster, f"{commondir}/autoscale.yaml.j2",
                                                      overrides=autoscale_overrides)
            with open(f"{asyncdir}/autoscale.yaml", 'w') as f:
                f.write(autoscale_data)
            async_files.append({'path': '/etc/kubernetes/autoscale.yaml', 'origin': f"{asyncdir}/autoscale.yaml"})
    data['async_files'] = async_files
    if assisted:
        assistedfile = config.process_inputfile(cluster, f"{plandir}/assisted_infra.yml", overrides=assetsdata)
        with open(f"{clusterdir}/assisted_infra.yml", 'w') as f:
            f.write(assistedfile)
        cmcmd = f"oc create -f {clusterdir}/assisted_infra.yml"
        call(cmcmd, shell=True)
    if 'OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE' in os.environ:
        assetsdata['hosted_image'] = os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE']
    else:
        hosted_version = data['hosted_version'] or version
        hosted_tag = data['hosted_tag'] or tag
        assetsdata['hosted_image'] = offline_image(version=hosted_version, tag=hosted_tag, pull_secret=pull_secret)
    hostedclusterfile = config.process_inputfile(cluster, f"{plandir}/hostedcluster.yaml", overrides=assetsdata)
    with open(f"{clusterdir}/hostedcluster.yaml", 'w') as f:
        f.write(hostedclusterfile)
    cmcmd = f"oc create -f {clusterdir}/hostedcluster.yaml"
    call(cmcmd, shell=True)
    which_openshift = which('openshift-install')
    openshift_dir = os.path.dirname(which_openshift) if which_openshift is not None else '.'
    if not same_release_images(version=version, tag=tag, pull_secret=pull_secret, path=openshift_dir):
        if version in ['ci', 'nightly']:
            nightly = version == 'nigthly'
            run = get_ci_installer(pull_secret, tag=tag, nightly=nightly)
        elif version in ['dev-preview', 'stable', 'latest']:
            run = get_downstream_installer(version=version, tag=tag, pull_secret=pull_secret)
        else:
            msg = f"Invalid version {version}"
            return {'result': 'failure', 'reason': msg}
        if run != 0:
            msg = "Couldn't download openshift-install"
            return {'result': 'failure', 'reason': msg}
        pprint("Move downloaded openshift-install somewhere in your PATH if you want to reuse it")
    elif which_openshift is not None:
        pprint("Using existing openshift-install found in your PATH")
    else:
        pprint("Reusing matching openshift-install")
    os.environ["PATH"] = f'{os.getcwd()}:{os.environ["PATH"]}'
    INSTALLER_VERSION = get_installer_version()
    pprint(f"Using installer version {INSTALLER_VERSION}")
    if 'OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE' in os.environ:
        assetsdata['nodepool_image'] = os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE']
    else:
        nodepool_image = os.popen("openshift-install version | grep 'release image' | cut -f3 -d' '").read().strip()
        assetsdata['nodepool_image'] = nodepool_image
    if assisted:
        create_bmh_objects(config, plandir, cluster, namespace, baremetal_hosts, overrides)
        agents = len(baremetal_hosts)
        if not agents:
            warning("No baremetal hosts were defined. Setting agent count to 2")
            agents = 2
        pprint(f"Waiting for {agents} agents to appear")
        agent_ns = f"{namespace}-{cluster}"
        call(f'until [ "$(oc -n {agent_ns} get agent -o name | wc -l | xargs)" -eq "{agents}" ] ; do sleep 1 ; done',
             shell=True)
        pprint("Waiting 2mn to avoid race conditions when creating nodepool")
        sleep(120)
    elif not kubevirt:
        image = data.get('image')
        if image is None:
            image_type = 'openstack' if data.get('kvm_openstack', True) and provider == 'kvm' else provider
            region = config.k.region if provider == 'aws' else None
            image_url = get_installer_rhcos(_type=image_type, region=region, arch=arch)
            if provider in ['aws', 'gcp']:
                image = image_url
            else:
                image = os.path.basename(os.path.splitext(image_url)[0])
                if provider == 'ibm':
                    image = image.replace('.', '-').replace('_', '-').lower()
                images = [v for v in k.volumes() if image in v]
                if not images:
                    result = config.download_image(pool=config.pool, image=image, url=image_url,
                                                   size=data.get('kubevirt_disk_size'))
                    if result['result'] != 'success':
                        return result
            pprint(f"Using image {image}")
            data['image'] = image
        elif provider == 'kubevirt' and '/' in image:
            warning(f"Assuming image {image} is available")
        else:
            pprint(f"Checking if image {image} is available")
            images = [v for v in k.volumes() if image in v]
            if not images:
                msg = f"Missing {image}. Indicate correct image in your parameters file..."
                return {'result': 'failure', 'reason': msg}
    with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
        installparam = overrides.copy()
        installparam['client'] = config.client
        installparam['plan'] = plan
        installparam['cluster'] = cluster
        installparam['kubetype'] = 'hypershift'
        installparam['management_api_ip'] = management_api_ip
        if management_ingress_ip is not None:
            installparam['management_ingress_ip'] = management_ingress_ip
        if ingress_ip is not None:
            installparam['ingress_ip'] = ingress_ip
        if virtual_router_id is not None:
            installparam['virtual_router_id'] = virtual_router_id
        installparam['platform'] = platform
        if platform is None:
            installparam['image'] = image
        installparam['ipv6'] = ipv6
        installparam['original_domain'] = data['original_domain']
        yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    nodepoolfile = config.process_inputfile(cluster, f"{plandir}/nodepool.yaml", overrides=assetsdata)
    with open(f"{clusterdir}/nodepool.yaml", 'w') as f:
        f.write(nodepoolfile)
    cmcmd = f"oc create -f {clusterdir}/nodepool.yaml"
    call(cmcmd, shell=True)
    assetsdata['clusterdir'] = clusterdir
    if platform is None:
        ignitionscript = config.process_inputfile(cluster, f"{plandir}/ignition.sh", overrides=assetsdata)
        with open(f"{clusterdir}/ignition.sh", 'w') as f:
            f.write(ignitionscript)
        pprint("Waiting before ignition data is available")
        user_data = f"user-data-{cluster}"
        call(f"until oc -n {namespace}-{cluster} get secret | grep {user_data} >/dev/null 2>&1 ; do sleep 1 ; done",
             shell=True)
        ignition_worker = f"{clusterdir}/nodepool.ign"
        timeout = 0
        while True:
            if os.path.exists(ignition_worker):
                break
            else:
                sleep(30)
                timeout += 30
                if timeout > 300:
                    msg = "Timeout trying to retrieve worker ignition"
                    return {'result': 'failure', 'reason': msg}
            call(f'bash {clusterdir}/ignition.sh', shell=True)
    if 'name' in data:
        del data['name']
    autoapproverpath = f'{clusterdir}/autoapprovercron.yml'
    autoapprover = config.process_inputfile(cluster, f"{plandir}/autoapprovercron.yml", overrides=data)
    with open(autoapproverpath, 'w') as f:
        f.write(autoapprover)
    call(f"oc apply -f {autoapproverpath}", shell=True)
    if platform is None:
        if provider in cloud_providers + ['openstack']:
            copy2(f"{clusterdir}/nodepool.ign", f"{clusterdir}/nodepool.ign.ori")
            bucket = f"{cluster}-{domain.replace('.', '-')}"
            if bucket not in config.k.list_buckets():
                config.k.create_bucket(bucket)
            config.k.upload_to_bucket(bucket, f"{clusterdir}/nodepool.ign", public=True)
            bucket_url = config.k.public_bucketfile_url(bucket, "nodepool.ign")
            new_ignition = {'ignition': {'config': {'merge': [{'source': bucket_url}]}, 'version': '3.2.0'}}
            with open(f"{clusterdir}/nodepool.ign", 'w') as f:
                f.write(json.dumps(new_ignition))
        elif baremetal_iso or baremetal_hosts:
            iso_url = handle_baremetal_iso(config, plandir, cluster, data, baremetal_hosts)
            start_baremetal_hosts(baremetal_hosts, iso_url, overrides=overrides, debug=config.debug)
            data['workers'] = data.get('workers', 2) - len(baremetal_hosts)
    pprint("Waiting for kubeconfig to be available")
    call(f"until oc -n {namespace} get secret {cluster}-admin-kubeconfig >/dev/null 2>&1 ; do sleep 1 ; done",
         shell=True)
    kubeconfigpath = f'{clusterdir}/auth/kubeconfig'
    kubeconfig = os.popen(f"oc extract -n {namespace} secret/{cluster}-admin-kubeconfig --to=-").read()
    with open(kubeconfigpath, 'w') as f:
        f.write(kubeconfig)
    pprint("Waiting for kubeadmin-password to be available")
    call(f"until oc -n {namespace} get secret {cluster}-kubeadmin-password >/dev/null 2>&1 ; do sleep 1 ; done",
         shell=True)
    kubeadminpath = f'{clusterdir}/auth/kubeadmin-password'
    kubeadmin = os.popen(f"oc extract -n {namespace} secret/{cluster}-kubeadmin-password --to=-").read()
    with open(kubeadminpath, 'w') as f:
        f.write(kubeadmin)
    if network_type == 'Calico':
        calico_version = data['calico_version']
        with TemporaryDirectory() as tmpdir:
            calico_data = {'tmpdir': tmpdir, 'namespace': namespace, 'cluster': cluster, 'clusterdir': clusterdir,
                           'calico_version': calico_version}
            calico_script = config.process_inputfile('xxx', f'{plandir}/calico.sh.j2', overrides=calico_data)
            with open(f"{tmpdir}/calico.sh", 'w') as f:
                f.write(calico_script)
            call(f'bash {tmpdir}/calico.sh', shell=True)
    elif network_type == 'Cilium':
        cilium_version = data['cilium_version']
        cluster_network_ipv4 = data['cluster_network_ipv4']
        cilium_data = {'clusterdir': clusterdir, 'cilium_version': cilium_version, 'cidr': cluster_network_ipv4}
        cilium_script = config.process_inputfile('xxx', f'{plandir}/cilium.sh.j2', overrides=cilium_data)
        with open(f"{clusterdir}/cilium.sh", 'w') as f:
            f.write(cilium_script)
        call(f'bash {clusterdir}/cilium.sh', shell=True)
    if platform is None and data['workers'] > 0:
        pprint("Deploying workers")
        worker_threaded = data.get('threaded', False) or data.get('workers_threaded', False)
        config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=data, threaded=worker_threaded)
    async_tempdir.cleanup()
    if ignore_hosts:
        warning("Not updating /etc/hosts as per your request")
    else:
        update_openshift_etc_hosts(cluster, domain, management_api_ip, ingress_ip)
    if provider in cloud_providers:
        result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_apps.yml', overrides=data)
        if result['result'] != 'success':
            return result
    if async_install or which('openshift-install') is None:
        success(f"Kubernetes cluster {cluster} deployed!!!")
        info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
        info2("export PATH=$PWD:$PATH")
    else:
        installcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for install-complete'
        installcommand = ' || '.join([installcommand for x in range(retries)])
        pprint("Launching install-complete step. It will be retried extra times to handle timeouts")
        run = call(installcommand, shell=True)
        if run != 0:
            msg = "Leaving environment for debugging purposes. "
            msg += f"Delete it with kcli delete kube --yes {cluster}"
            return {'result': 'failure', 'reason': msg}
    if provider in cloud_providers:
        bucket = f"{cluster}-{domain.replace('.', '-')}"
        config.k.delete_bucket(bucket)
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    apps = overrides.get('apps', [])
    overrides['hypershift'] = True
    overrides['cluster'] = cluster
    process_apps(config, clusterdir, apps, overrides)
    if autoscale:
        config.import_in_kube(network=network, secure=True)
        with NamedTemporaryFile(mode='w+t') as temp:
            commondir = os.path.dirname(pprint.__code__.co_filename)
            autoscale_overrides = {'cluster': cluster, 'kubetype': 'k3s', 'workers': workers, 'replicas': 1,
                                   'sa': 'default'}
            autoscale_data = config.process_inputfile(cluster, f"{commondir}/autoscale.yaml.j2",
                                                      overrides=autoscale_overrides)
            temp.write(autoscale_data)
            temp.seek(0)
            scc_cmd = "oc adm policy add-scc-to-user anyuid -z default -n kcli-infra"
            call(scc_cmd, shell=True)
            autoscale_cmd = f"oc create -f {temp.name}"
            call(autoscale_cmd, shell=True)
    if provider in cloud_providers and data.get('cloud_storage', True):
        pprint("Deploying cloud storage class")
        deploy_cloud_storage(config, cluster, apply=False)
    return {'result': 'success'}
