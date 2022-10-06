#!/usr/bin/env python

from glob import glob
from kvirt.common import success, error, pprint, info2, container_mode, warning
from kvirt.common import get_oc, pwd_path, get_installer_rhcos, generate_rhcos_iso
from kvirt.defaults import OPENSHIFT_TAG
from kvirt.openshift import process_apps, update_etc_hosts
from kvirt.openshift import get_ci_installer, get_downstream_installer, get_installer_version
from ipaddress import ip_network
import json
import os
import re
import sys
from shutil import which
from subprocess import call
import time
import yaml

virtplatforms = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'kube': cluster, 'kubetype': 'hypershift'}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
        yaml.safe_dump(data, paramfile)
    pprint(f"Scaling on client {config.client}")
    os.chdir(os.path.expanduser("~/.kcli"))
    worker_overrides = data.copy()
    if worker_overrides.get('workers', 2) == 0:
        return
    threaded = data.get('threaded', False) or data.get('workers_threaded', False)
    config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=worker_overrides, threaded=threaded)


def create(config, plandir, cluster, overrides):
    log_level = 'debug' if config.debug else 'info'
    os.environ["PATH"] += f":{os.getcwd()}"
    k = config.k
    platform = config.type
    arch = k.get_capabilities()['arch'] if config.type == 'kvm' else 'x86_64'
    arch_tag = 'arm64' if arch in ['aarch64', 'arm64'] else 'latest'
    overrides['arch_tag'] = arch_tag
    if 'KUBECONFIG' not in os.environ:
        error("Missing KUBECONFIG...")
        sys.exit(1)
    elif not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = f"{os.getcwd()}/{os.environ['KUBECONFIG']}"
    data = {'kubetype': 'hypershift',
            'domain': 'karmalabs.local',
            'baremetal_iso': False,
            'network': 'default',
            'etcd_size': 4,
            'workers': 2,
            'async': False,
            'tag': OPENSHIFT_TAG,
            'version': 'stable',
            'network_type': 'OVNKubernetes',
            'fips': False,
            'namespace': 'clusters',
            'pub_key': os.path.expanduser('~/.ssh/id_rsa.pub'),
            'pull_secret': 'openshift_pull.json'}
    data.update(overrides)
    if 'cluster' in overrides:
        clustervalue = overrides.get('cluster')
    elif cluster is not None:
        clustervalue = cluster
    else:
        clustervalue = 'testk'
    data['cluster'] = clustervalue
    data['kube'] = data['cluster']
    pprint(f"Deploying cluster {clustervalue}")
    plan = cluster if cluster is not None else clustervalue
    domain = data.get('domain')
    version = data.get('version')
    tag = data.get('tag')
    if str(tag) == '4.1':
        tag = '4.10'
        data['tag'] = tag
    default_sc = False
    for sc in yaml.safe_load(os.popen('oc get sc -o yaml').read())['items']:
        if 'annotations' in sc['metadata']\
           and 'storageclass.kubernetes.io/is-default-class' in sc['metadata']['annotations']\
           and sc['metadata']['annotations']['storageclass.kubernetes.io/is-default-class'] == 'true':
            pprint(f"Using default class {sc['metadata']['name']}")
            default_sc = True
    if not default_sc:
        error("Default Storage class not found. Leaving...")
        sys.exit(1)
    data['basedir'] = '/workdir' if container_mode() else '.'
    api_ip = os.popen("oc get node -o wide | grep master | head -1 | awk '{print $6}'").read().strip()
    data['api_ip'] = api_ip
    cluster = data.get('cluster')
    namespace = data.get('namespace')
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        error(f"Please remove existing directory {clusterdir} first...")
        sys.exit(1)
    if which('oc') is None:
        get_oc()
    pub_key = data.get('pub_key')
    pull_secret = pwd_path(data.get('pull_secret'))
    pull_secret = os.path.expanduser(pull_secret)
    if not os.path.exists(pull_secret):
        error(f"Missing pull secret file {pull_secret}")
        sys.exit(1)
    data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
    if not os.path.exists(pub_key):
        if os.path.exists(os.path.expanduser('~/.kcli/id_rsa.pub')):
            pub_key = os.path.expanduser('~/.kcli/id_rsa.pub')
        else:
            error(f"Missing public key file {pub_key}")
            sys.exit(1)
    data['pub_key'] = open(pub_key).read().strip()
    ingress_ip = data.get('ingress_ip')
    cidr = '192.168.122.0/24'
    if config.type in virtplatforms:
        if ingress_ip is None:
            network = data.get('network')
            networkinfo = k.info_network(network)
            if config.type == 'kvm' and networkinfo['type'] == 'routed':
                cidr = networkinfo['cidr']
                ingress_index = 3 if ':' in cidr else -4
                ingress_ip = str(ip_network(cidr)[ingress_index])
                warning(f"Using {ingress_ip} as ingress_ip")
                data['ingress_ip'] = ingress_ip
            else:
                error("You need to define ingress_ip in your parameters file")
                sys.exit(1)
        virtual_router_id = None
        if data.get('virtual_router_id') is None:
            virtual_router_id = hash(cluster) % 254 + 1
            data['virtual_router_id'] = virtual_router_id
            pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
        pprint(f"Using {ingress_ip} for ingress vip....")
        ipv6 = True if ':' in cidr else False
        data['ipv6'] = ipv6
    assetsdata = data.copy()
    if version == 'cluster':
        release_image = os.popen("oc get clusterversion version -o jsonpath={'.status.history[-1].image'}").read()
        version = os.popen("oc get clusterversion version -o jsonpath={'.status.history[-1].version'}").read()
        minor = version[:3].replace('.', '')
        image = f'rhcos{minor}'
        data['image'] = image
    else:
        if os.path.exists('openshift-install'):
            pprint("Removing old openshift-install")
            os.remove('openshift-install')
        if which('openshift-install') is None:
            if version == 'ci':
                run = get_ci_installer(pull_secret, tag=tag)
            elif version == 'nightly':
                run = get_downstream_installer(nightly=True, tag=tag, pull_secret=pull_secret)
            else:
                run = get_downstream_installer(tag=tag, pull_secret=pull_secret)
            if run != 0:
                error("Couldn't download openshift-install")
                sys.exit(run)
            pprint("Move downloaded openshift-install somewhere in your PATH if you want to reuse it")
        else:
            warning("Using existing openshift-install found in your PATH")
        INSTALLER_VERSION = get_installer_version()
        pprint(f"Using installer version {INSTALLER_VERSION}")
        release_image = os.popen("openshift-install version | grep 'release image' | cut -f3 -d' '").read().strip()
        image = data.get('image')
        if image is None:
            image_type = 'openstack' if data.get('kvm_openstack', True) and config.type == 'kvm' else config.type
            region = config.k.region if config.type == 'aws' else None
            image_url = get_installer_rhcos(_type=image_type, region=region, arch=arch)
            if platform in ['aws', 'gcp']:
                image = image_url
            else:
                image = os.path.basename(os.path.splitext(image_url)[0])
                if platform == 'ibm':
                    image = image.replace('.', '-').replace('_', '-').lower()
                images = [v for v in k.volumes() if image in v]
                if not images:
                    result = config.handle_host(pool=config.pool, image=image, download=True, update_profile=False,
                                                url=image_url, size=data.get('kubevirt_disk_size'))
                    if result['result'] != 'success':
                        sys.exit(1)
            pprint(f"Using image {image}")
            data['image'] = image
        else:
            pprint(f"Checking if image {image} is available")
            images = [v for v in k.volumes() if image in v]
            if not images:
                error(f"Missing {image}. Indicate correct image in your parameters file...")
                sys.exit(1)
    assetsdata['release_image'] = release_image
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['kubetype'] = 'hypershift'
            installparam['api_ip'] = api_ip
            installparam['ingress_ip'] = ingress_ip
            if virtual_router_id is not None:
                installparam['virtual_router_id'] = virtual_router_id
            installparam['image'] = image
            installparam['ipv6'] = ipv6
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    assetsdata['cidr'] = cidr
    pprint("Creating control plane assets")
    cmcmd = f"oc create ns {namespace} -o yaml --dry-run=client | oc apply -f -"
    call(cmcmd, shell=True)
    icsps = yaml.safe_load(os.popen('oc get imagecontentsourcepolicies -o yaml').read())['items']
    if icsps:
        imagecontentsources = []
        for icsp in icsps:
            for mirror_spec in icsp['spec']['repositoryDigestMirrors']:
                source, mirror = mirror_spec['source'], mirror_spec['mirrors'][0]
                imagecontentsources.append({'source': source, 'mirror': mirror})
        assetsdata['imagecontentsources'] = imagecontentsources
    manifestsdir = pwd_path("manifests")
    if os.path.exists(manifestsdir) and os.path.isdir(manifestsdir):
        manifests = []
        for f in glob(f"{manifestsdir}/*.y*ml"):
            mc_name = os.path.basename(f).replace('.yaml', '').replace('.yml', '')
            mc_data = yaml.safe_load(open(f))
            if mc_data.get('kind', 'xx') == 'MachineConfig':
                pprint(f"Injecting manifest {f}")
                mc_data = json.dumps(mc_data)
                manifests.append({'name': mc_name, 'data': mc_data})
        assetsdata['manifests'] = manifests
    assetsfile = config.process_inputfile(cluster, f"{plandir}/assets.yaml", overrides=assetsdata)
    with open(f"{clusterdir}/assets.yaml", 'w') as f:
        f.write(assetsfile)
    cmcmd = f"oc create -f {clusterdir}/assets.yaml"
    call(cmcmd, shell=True)
    assetsdata['clusterdir'] = clusterdir
    console_url = os.popen("oc get route -n openshift-console console -o jsonpath='{.status.ingress[0].host}'").read()
    assetsdata['base_domain'] = console_url.replace('console-openshift-console.apps.', '')
    ignitionscript = config.process_inputfile(cluster, f"{plandir}/ignition.sh", overrides=assetsdata)
    with open(f"{clusterdir}/ignition.sh", 'w') as f:
        f.write(ignitionscript)
    pprint("Waiting before ignition server is usable")
    call(f"until oc -n {namespace}-{cluster} get secret | grep user-data-{cluster} >/dev/null 2>&1 ; do sleep 1 ; done",
         shell=True)
    time.sleep(60)
    call(f'bash {clusterdir}/ignition.sh', shell=True)
    pprint("Deploying workers")
    if 'name' in data:
        del data['name']
    if data.get('baremetal_iso', False):
        result = config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=data, onlyassets=True)
        iso_data = result['assets'][0]
        with open('iso.ign', 'w') as f:
            f.write(iso_data)
        ignitionfile = f'{cluster}-worker.ign'
        with open(ignitionfile, 'w') as f:
            f.write(iso_data)
        iso_pool = data['pool'] or config.pool
        generate_rhcos_iso(k, f"{cluster}-worker", iso_pool, installer=True)
    worker_threaded = data.get('threaded', False) or data.get('workers_threaded', False)
    config.plan(plan, inputfile=f'{plandir}/kcli_plan.yml', overrides=data, threaded=worker_threaded)
    if data.get('ignore_hosts', False):
        warning("Not updating /etc/hosts as per your request")
    else:
        update_etc_hosts(cluster, domain, api_ip, ingress_ip)
    kubeconfigpath = f'{clusterdir}/auth/kubeconfig'
    kubeconfig = os.popen(f"oc extract -n {namespace} secret/{cluster}-admin-kubeconfig --to=-").read()
    with open(kubeconfigpath, 'w') as f:
        f.write(kubeconfig)
    kubeadminpath = f'{clusterdir}/auth/kubeadmin-password'
    kubeadmin = os.popen(f"oc extract -n {namespace} secret/{cluster}-kubeadmin-password --to=-").read()
    with open(kubeadminpath, 'w') as f:
        f.write(kubeadmin)
    autoapproverpath = f'{clusterdir}/autoapprovercron.yml'
    autoapprover = config.process_inputfile(cluster, f"{plandir}/autoapprovercron.yml", overrides=data)
    with open(autoapproverpath, 'w') as f:
        f.write(autoapprover)
    call(f"oc apply -f {autoapproverpath}", shell=True)
    async_install = data.get('async')
    if async_install or which('openshift-install') is None:
        success(f"Kubernetes cluster {cluster} deployed!!!")
        info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
        info2("export PATH=$PWD:$PATH")
    else:
        installcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for install-complete'
        installcommand += f" || {installcommand}"
        pprint("Launching install-complete step. It will be retried one extra time in case of timeouts")
        call(installcommand, shell=True)
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    apps = overrides.get('apps', [])
    process_apps(config, clusterdir, apps, overrides)
