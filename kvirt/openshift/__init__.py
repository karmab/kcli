#!/usr/bin/env python

from base64 import b64encode
from distutils.spawn import find_executable
from glob import glob
import json
import os
import sys
from kvirt.common import error, pprint, success, warning, info2
from kvirt.common import gen_mac, get_oc, get_values, pwd_path, fetch
from kvirt.common import get_commit_rhcos, get_latest_fcos, kube_create_app, patch_bootstrap
from kvirt.common import ssh, scp, _ssh_credentials, word2number
from kvirt.openshift.calico import calicoassets
import re
from shutil import copy2, rmtree
from subprocess import call
from time import sleep
from urllib.request import urlopen
import yaml


virtplatforms = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere', 'packet']
cloudplatforms = ['aws', 'gcp']
DEFAULT_TAG = '4.6'


def get_installer_version():
    INSTALLER_VERSION = os.popen('openshift-install version').readlines()[0].split(" ")[1].strip()
    if INSTALLER_VERSION.startswith('v'):
        INSTALLER_VERSION = INSTALLER_VERSION[1:]
    return INSTALLER_VERSION


def get_rhcos_openstack_url():
    for line in os.popen('openshift-install version').readlines():
        if 'built from commit' in line:
            commit_id = line.replace('built from commit ', '').strip()
            break
    r = urlopen("https://raw.githubusercontent.com/openshift/installer/%s/data/data/rhcos.json" % commit_id)
    r = str(r.read(), 'utf-8').strip()
    data = json.loads(r)
    return "%s%s" % (data['baseURI'], data['images']['openstack']['path'])


def get_minimal_rhcos():
    for line in os.popen('openshift-install version').readlines():
        if 'built from commit' in line:
            commit_id = line.replace('built from commit ', '').strip()
            break
    r = urlopen("https://raw.githubusercontent.com/openshift/installer/%s/data/data/rhcos.json" % commit_id)
    r = str(r.read(), 'utf-8').strip()
    data = json.loads(r)
    ver = os.path.basename(data['images']['qemu']['path']).replace('-0-qemu.x86_64.qcow2.gz', '').replace('rhcos-', '')
    return int(ver.replace('.', ''))


def get_downstream_installer(nightly=False, macosx=False, tag=None):
    repo = 'ocp-dev-preview' if nightly else 'ocp'
    if tag is None:
        repo += '/latest'
    elif str(tag).count('.') == 1:
        repo += '/latest-%s' % tag
    else:
        repo += '/%s' % tag.replace('-x86_64', '')
    INSTALLSYSTEM = 'mac' if os.path.exists('/Users') or macosx else 'linux'
    msg = 'Downloading openshift-install from https://mirror.openshift.com/pub/openshift-v4/clients/%s' % repo
    pprint(msg)
    r = urlopen("https://mirror.openshift.com/pub/openshift-v4/clients/%s/release.txt" % repo).readlines()
    version = None
    for line in r:
        if 'Name' in str(line):
            version = str(line).split(':')[1].strip().replace('\\n', '').replace("'", "")
            break
    if version is None:
        error("Coudldn't find version")
        return 1
    cmd = "curl -s https://mirror.openshift.com/pub/openshift-v4/clients/%s/" % repo
    cmd += "openshift-install-%s-%s.tar.gz " % (INSTALLSYSTEM, version)
    cmd += "| tar zxf - openshift-install"
    cmd += "; chmod 700 openshift-install"
    return call(cmd, shell=True)


def get_ci_installer(pull_secret, tag=None, macosx=False, upstream=False):
    base = 'openshift' if not upstream else 'origin'
    if tag is None:
        tags = []
        r = urlopen("https://%s-release.ci.openshift.org/graph?format=dot" % base).readlines()
        for line in r:
            tag_match = re.match('.*label="(.*.)", shape=.*', str(line))
            if tag_match is not None:
                tags.append(tag_match.group(1))
        tag = sorted(tags)[-1]
    elif '/' not in str(tag):
        basetag = 'ocp' if not upstream else 'origin'
        tag = 'registry.ci.openshift.org/%s/release:%s' % (basetag, tag)
    os.environ['OPENSHIFT_RELEASE_IMAGE'] = tag
    msg = 'Downloading openshift-install %s in current directory' % tag
    pprint(msg)
    if upstream:
        cmd = "oc adm release extract --command=openshift-install --to . %s" % tag
    else:
        cmd = "oc adm release extract --registry-config %s --command=openshift-install --to . %s" % (pull_secret, tag)
    cmd += "; chmod 700 openshift-install"
    return call(cmd, shell=True)


def get_upstream_installer(macosx=False, tag=None):
    INSTALLSYSTEM = 'mac' if os.path.exists('/Users') or macosx else 'linux'
    msg = 'Downloading okd openshift-install from github in current directory'
    pprint(msg)
    r = urlopen("https://api.github.com/repos/openshift/okd/releases")
    data = json.loads(r.read())
    version = sorted([x['tag_name'] for x in data])[-1]
    cmd = "curl -Ls https://github.com/openshift/okd/releases/download/"
    cmd += "%s/openshift-install-%s-%s.tar.gz" % (version, INSTALLSYSTEM, version)
    cmd += "| tar zxf - openshift-install"
    cmd += "; chmod 700 openshift-install"
    return call(cmd, shell=True)


def gather_dhcp(data, platform):
    cluster = data.get('cluster', 'testk')
    masters = data.get('masters', 1)
    workers = data.get('workers', 0)
    bootstrap_name = "%s-bootstrap" % cluster
    bootstrap_mac = data.get('bootstrap_mac', gen_mac())
    bootstrap_ip = data.get('bootstrap_ip')
    dhcp_ip = data.get('dhcp_ip')
    dhcp_netmask = data.get('dhcp_netmask')
    dhcp_gateway = data.get('dhcp_gateway')
    dhcp_dns = data.get('dhcp_dns')
    if bootstrap_ip is None or dhcp_ip is None or dhcp_netmask is None or dhcp_gateway is None or dhcp_dns is None:
        return {}
    if platform in ['openstack', 'vsphere']:
        bootstrap_helper_name = "%s-bootstrap-helper" % cluster
        bootstrap_helper_mac = data.get('bootstrap_helper_mac', gen_mac())
        bootstrap_helper_ip = data.get('bootstrap_helper_ip')
        if bootstrap_helper_ip is None:
            return {}
    master_names = ['%s-master-%s' % (cluster, num) for num in range(masters)]
    worker_names = ['%s-worker-%s' % (cluster, num) for num in range(workers)]
    node_names = master_names + worker_names
    master_macs = get_values(data, 'master', 'macs')
    worker_macs = get_values(data, 'worker', 'macs')
    node_macs = master_macs + worker_macs
    master_ips = get_values(data, 'master', 'ips')
    worker_ips = get_values(data, 'worker', 'ips')
    node_ips = master_ips + worker_ips
    if not node_macs:
        node_macs = [gen_mac() for x in node_names]
    if node_ips and len(node_macs) == len(node_ips) and len(node_names) == len(node_macs):
        nodes = len(node_macs) + 1
        node_names.insert(0, bootstrap_name)
        node_macs.insert(0, bootstrap_mac)
        node_ips.insert(0, bootstrap_ip)
        if platform in ['openstack', 'vsphere']:
            nodes += 1
            node_names.insert(0, bootstrap_helper_name)
            node_macs.insert(0, bootstrap_helper_mac)
            node_ips.insert(0, bootstrap_helper_ip)
        node_names = ','.join(node_names)
        node_macs = ','.join(node_macs)
        node_ips = ','.join(node_ips)
        return {'node_names': node_names, 'node_macs': node_macs, 'node_ips': node_ips, 'nodes': nodes}


def scale(config, plandir, cluster, overrides):
    plan = cluster if cluster is not None else 'testk'
    client = config.client
    platform = config.type
    k = config.k
    data = {}
    pprint("Scaling on client %s" % client)
    cluster = overrides.get('cluster', 'testk')
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if not os.path.exists(clusterdir):
        error("Cluster directory %s not found..." % clusterdir)
        sys.exit(1)
    if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    api_ip = data.get('api_ip')
    if platform in virtplatforms:
        if api_ip is None:
            network = data.get('network')
            if network == 'default' and platform == 'kvm':
                warning("Using 192.168.122.253 as api_ip")
                data['api_ip'] = "192.168.122.253"
            elif platform == 'kubevirt':
                selector = {'kcli/plan': plan, 'kcli/role': 'master'}
                api_ip = config.k.create_service("%s-api" % cluster, config.k.namespace, selector,
                                                 _type="LoadBalancer", ports=[6443, 22623, 22624])
                if api_ip is None:
                    os._exit(1)
                else:
                    pprint("Using api_ip %s" % api_ip)
                    data['api_ip'] = api_ip
            else:
                error("You need to define api_ip in your parameters file")
                os._exit(1)
        if data.get('virtual_router_id') is None:
            data['virtual_router_id'] = word2number(cluster)
        pprint("Using keepalived virtual_router_id %s" % data['virtual_router_id'])
    if platform == 'packet':
        network = data.get('network')
        if network is None:
            error("You need to indicate a specific vlan network")
            os._exit(1)
    image = overrides.get('image')
    if image is None:
        cluster_image = k.info("%s-master-0" % cluster).get('image')
        if cluster_image is None:
            error("Missing image...")
            sys.exit(1)
        else:
            pprint("Using image %s" % cluster_image)
            image = cluster_image
    data['image'] = image
    for role in ['masters', 'workers']:
        overrides = data.copy()
        if overrides.get(role, 0) == 0:
            continue
        if platform in virtplatforms:
            os.chdir(os.path.expanduser("~/.kcli"))
            result = config.plan(plan, inputfile='%s/%s.yml' % (plandir, role), overrides=overrides)
        elif platform in cloudplatforms:
            result = config.plan(plan, inputfile='%s/cloud_%s.yml' % (plandir, role), overrides=overrides)
        if result['result'] != 'success':
            os._exit(1)
        elif platform == 'packet' and 'newvms' in result and result['newvms']:
            for node in result['newvms']:
                k.add_nic(node, network)


def create(config, plandir, cluster, overrides):
    k = config.k
    bootstrap_helper_ip = None
    client = config.client
    platform = config.type
    pprint("Deploying on client %s" % client)
    data = {'helper_image': 'CentOS-7-x86_64-GenericCloud.qcow2',
            'domain': 'karmalabs.com',
            'network': 'default',
            'masters': 1,
            'workers': 0,
            'tag': DEFAULT_TAG,
            'ipv6': False,
            'pub_key': os.path.expanduser('~/.ssh/id_rsa.pub'),
            'pull_secret': 'openshift_pull.json',
            'version': 'nightly',
            'macosx': False,
            'upstream': False,
            'fips': False,
            'apps': [],
            'minimal': False,
            'dualstack': False}
    data.update(overrides)
    if 'cluster' in overrides:
        clustervalue = overrides.get('cluster')
    elif cluster is not None:
        clustervalue = cluster
    else:
        clustervalue = 'testk'
    data['cluster'] = clustervalue
    pprint("Deploying cluster %s" % clustervalue)
    plan = cluster if cluster is not None else clustervalue
    overrides['kubetype'] = 'openshift'
    apps = overrides.get('apps', [])
    if ('localstorage' in apps or 'ocs' in apps) and 'extra_disks' not in overrides\
            and 'extra_master_disks' not in overrides and 'extra_worker_disks' not in overrides:
        warning("Storage apps require extra disks to be set")
    overrides['kube'] = data['cluster']
    installparam = overrides.copy()
    masters = data.get('masters', 1)
    if masters == 0:
        error("Invalid number of masters")
        os._exit(1)
    network = data.get('network')
    ipv6 = data['ipv6']
    dualstack = data.get('dualstack')
    upstream = data.get('upstream')
    version = data.get('version')
    tag = data.get('tag')
    if os.path.exists('openshift-install'):
        pprint("Removing old openshift-install")
        os.remove('openshift-install')
    minimal = data.get('minimal')
    if version not in ['ci', 'nightly']:
        pprint("Using stable version")
    else:
        pprint("Using %s version" % version)
    cluster = data.get('cluster')
    helper_image = data.get('helper_image')
    image = data.get('image')
    api_ip = data.get('api_ip')
    if platform in virtplatforms and api_ip is None:
        if network == 'default' and platform == 'kvm':
            warning("Using 192.168.122.253 as api_ip")
            overrides['api_ip'] = "192.168.122.253"
            api_ip = "192.168.122.253"
        else:
            error("You need to define api_ip in your parameters file")
            os._exit(1)
    if ':' in api_ip:
        ipv6 = True
    ingress_ip = data.get('ingress_ip')
    public_api_ip = data.get('public_api_ip')
    network = data.get('network')
    if platform == 'packet':
        if network == 'default':
            error("You need to indicate a specific vlan network")
            os._exit(1)
        else:
            facilities = [n['domain'] for n in k.list_networks().values() if str(n['cidr']) == network]
            if not facilities:
                error("Vlan network %s not found in any facility" % network)
                os._exit(1)
            elif k.facility not in facilities:
                error("Vlan network %s not found in facility %s" % (network, k.facility))
                os._exit(1)
    masters = data.get('masters')
    workers = data.get('workers')
    disconnected_deploy = data.get('disconnected_deploy', False)
    disconnected_reuse = data.get('disconnected_reuse', False)
    disconnected_url = data.get('disconnected_url')
    disconnected_user = data.get('disconnected_user')
    disconnected_password = data.get('disconnected_password')
    disconnected_prefix = data.get('disconnected_prefix', 'ocp4')
    tag = data.get('tag')
    pub_key = data.get('pub_key')
    pull_secret = pwd_path(data.get('pull_secret')) if not upstream else "%s/fake_pull.json" % plandir
    pull_secret = os.path.expanduser(pull_secret)
    macosx = data.get('macosx')
    if macosx and not os.path.exists('/i_am_a_container'):
        macosx = False
    if platform == 'openstack' and (api_ip is None or public_api_ip is None):
        error("You need to define both api_ip and public_api_ip in your parameters file")
        os._exit(1)
    if not os.path.exists(pull_secret):
        error("Missing pull secret file %s" % pull_secret)
        sys.exit(1)
    if not os.path.exists(pub_key):
        if os.path.exists(os.path.expanduser('~/.kcli/id_rsa.pub')):
            pub_key = os.path.expanduser('~/.kcli/id_rsa.pub')
        else:
            error("Missing public key file %s" % pub_key)
            sys.exit(1)
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists(clusterdir):
        if [v for v in config.k.list() if v.get('plan', 'kvirt') == cluster]:
            error("Please remove existing directory %s first..." % clusterdir)
            sys.exit(1)
        else:
            pprint("Removing directory %s" % clusterdir)
            rmtree(clusterdir)
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    if find_executable('oc') is None:
        get_oc(macosx=macosx)
    if version == 'ci':
        if '/' not in str(tag):
            basetag = 'ocp' if not upstream else 'origin'
            tag = 'registry.ci.openshift.org/%s/release:%s' % (basetag, tag)
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = tag
        pprint("Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to %s" % tag)
    if find_executable('openshift-install') is None:
        if version == 'ci':
            run = get_ci_installer(pull_secret, tag=tag, upstream=upstream)
        elif version == 'nightly':
            run = get_downstream_installer(nightly=True, tag=tag)
        elif upstream:
            run = get_upstream_installer(tag=tag)
        else:
            run = get_downstream_installer(tag=tag)
        if run != 0:
            error("Couldn't download openshift-install")
            os._exit(run)
        pprint("Move downloaded openshift-install somewhere in your path if you want to reuse it")
    os.environ["PATH"] += ":%s" % os.getcwd()
    if disconnected_url is not None:
        if '/' not in str(tag):
            tag = '%s/%s/release:%s' % (disconnected_url, disconnected_prefix, tag)
            os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = tag
        pprint("Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to %s" % tag)
    INSTALLER_VERSION = get_installer_version()
    COMMIT_ID = os.popen('openshift-install version').readlines()[1].replace('built from commit', '').strip()
    if platform == 'packet' and not upstream:
        overrides['commit_id'] = COMMIT_ID
    pprint("Using installer version %s" % INSTALLER_VERSION)
    OPENSHIFT_VERSION = INSTALLER_VERSION[0:3].replace('.', '')
    curl_header = "Accept: application/vnd.coreos.ignition+json; version=3.1.0"
    if upstream:
        curl_header = "User-Agent: Ignition/2.3.0"
    elif OPENSHIFT_VERSION.isdigit() and int(OPENSHIFT_VERSION) < 46:
        curl_header = "User-Agent: Ignition/0.35.0"
    overrides['curl_header'] = curl_header
    if image is None:
        if upstream:
            fcos_base = 'stable' if version == 'stable' else 'testing'
            fcos_url = "https://builds.coreos.fedoraproject.org/streams/%s.json" % fcos_base
            image_url = get_latest_fcos(fcos_url, _type=config.type)
        else:
            image_url = get_commit_rhcos(COMMIT_ID, _type=config.type)
        image = os.path.basename(os.path.splitext(image_url)[0])
        images = [v for v in k.volumes() if image in v]
        if not images:
            result = config.handle_host(pool=config.pool, image=image, download=True, update_profile=False,
                                        url=image_url)
            if result['result'] != 'success':
                os._exit(1)
        else:
            pprint("Using image %s" % image)
    elif platform != 'packet':
        pprint("Checking if image %s is available" % image)
        images = [v for v in k.volumes() if image in v]
        if not images:
            error("Missing %s. Indicate correct image in your parameters file..." % image)
            os._exit(1)
    else:
        error("Missing image in your parameters file. This is required for packet")
        os._exit(1)
    overrides['image'] = image
    overrides['cluster'] = cluster
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        with open("%s/kcli_parameters.yml" % clusterdir, 'w') as p:
            installparam['plan'] = plan
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    data['pub_key'] = open(pub_key).read().strip()
    if platform in virtplatforms and disconnected_deploy:
        if platform == 'kvm' and network in [n for n in k.list_networks() if k.list_networks()[n]['type'] == 'routed']:
            data['disconnected_dns'] = True
        disconnected_vm = "%s-disconnecter" % cluster
        pprint("Deploying disconnected vm %s" % disconnected_vm)
        data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
        disconnected_plan = "%s-reuse" % plan if disconnected_reuse else plan
        result = config.plan(disconnected_plan, inputfile='%s/disconnected.yml' % plandir, overrides=data)
        if result['result'] != 'success':
            os._exit(1)
        disconnected_ip, disconnected_vmport = _ssh_credentials(k, disconnected_vm)[1:]
        cacmd = "cat /opt/registry/certs/domain.crt"
        cacmd = ssh(disconnected_vm, ip=disconnected_ip, user='root', tunnel=config.tunnel,
                    tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                    insecure=True, cmd=cacmd, vmport=disconnected_vmport)
        disconnected_ca = os.popen(cacmd).read().strip()
        if data['ca'] is not None:
            data['ca'] += disconnected_ca
        else:
            data['ca'] = disconnected_ca
        urlcmd = "cat /root/url.txt"
        urlcmd = ssh(disconnected_vm, ip=disconnected_ip, user='root', tunnel=config.tunnel,
                     tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                     insecure=True, cmd=urlcmd, vmport=disconnected_vmport)
        disconnected_url = os.popen(urlcmd).read().strip()
        overrides['disconnected_url'] = disconnected_url
        data['disconnected_url'] = disconnected_url
        if disconnected_user is None:
            disconnected_user = 'dummy'
        if disconnected_password is None:
            disconnected_password = 'dummy'
        versioncmd = "cat /root/version.txt"
        versioncmd = ssh(disconnected_vm, ip=disconnected_ip, user='root', tunnel=config.tunnel,
                         tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                         insecure=True, cmd=versioncmd, vmport=disconnected_vmport)
        disconnected_version = os.popen(versioncmd).read().strip()
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = disconnected_version
        pprint("Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to %s" % disconnected_version)
    if disconnected_url is not None and disconnected_user is not None and disconnected_password is not None:
        key = "%s:%s" % (disconnected_user, disconnected_password)
        key = str(b64encode(key.encode('utf-8')), 'utf-8')
        auths = {'auths': {disconnected_url: {'auth': key, 'email': 'jhendrix@karmalabs.com'}}}
        data['pull_secret'] = json.dumps(auths)
    else:
        data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
    if ipv6:
        data['network_type'] = 'OVNKubernetes'
        data['ipv6'] = True
        overrides['ipv6'] = True
    installconfig = config.process_inputfile(cluster, "%s/install-config.yaml" % plandir, overrides=data)
    with open("%s/install-config.yaml" % clusterdir, 'w') as f:
        f.write(installconfig)
    with open("%s/install-config.yaml.bck" % clusterdir, 'w') as f:
        f.write(installconfig)
    autoapprover = config.process_inputfile(cluster, "%s/autoapprovercron.yml" % plandir, overrides=data)
    with open("%s/autoapprovercron.yml" % clusterdir, 'w') as f:
        f.write(autoapprover)
    run = call('openshift-install --dir=%s create manifests' % clusterdir, shell=True)
    if run != 0:
        error("Leaving environment for debugging purposes")
        error("You can delete it with kcli delete kube --yes %s" % cluster)
        os._exit(run)
    if minimal:
        warning("Deploying cvo overrides to provide a minimal install")
        with open("%s/cvo-overrides.yaml" % plandir) as f:
            cvo_override = f.read()
        with open("%s/manifests/cvo-overrides.yaml" % clusterdir, "a") as f:
            f.write(cvo_override)
    if ipv6:
        for role in ['master', 'worker']:
            blacklist = config.process_inputfile(cluster, "%s/99-blacklist-ipi.yaml" % plandir,
                                                 overrides={'role': role})
            with open("%s/openshift/99-blacklist-ipi-%s.yaml" % (clusterdir, role), 'w') as f:
                f.write(blacklist)
    for f in glob("%s/customisation/*.yaml" % plandir):
        if '99-ingress-controller.yaml' in f:
            ingressrole = 'master' if workers == 0 else 'worker'
            replicas = masters if workers == 0 else workers
            ingressconfig = config.process_inputfile(cluster, f, overrides={'replicas': replicas, 'role': ingressrole})
            with open("%s/openshift/99-ingress-controller.yaml" % clusterdir, 'w') as f:
                f.write(ingressconfig)
        else:
            copy2(f, "%s/openshift" % clusterdir)
    manifestsdir = pwd_path("manifests")
    if os.path.exists(manifestsdir) and os.path.isdir(manifestsdir):
        for f in glob("%s/*.yaml" % manifestsdir):
            copy2(f, "%s/openshift" % clusterdir)
    if 'network_type' in data and data['network_type'] == 'Calico':
        for asset in calicoassets:
            fetch(asset, manifestsdir)
    if dualstack:
        copy2("%s/dualstack.yml" % plandir, "%s/openshift" % clusterdir)
    call('openshift-install --dir=%s create ignition-configs' % clusterdir, shell=True)
    for role in ['master', 'worker']:
        ori = "%s/%s.ign" % (clusterdir, role)
        copy2(ori, "%s.ori" % ori)
    if masters < 3:
        version_match = re.match("4.([0-9]*).*", INSTALLER_VERSION)
        COS_VERSION = "4%s" % version_match.group(1) if version_match is not None else '45'
        if not upstream and int(COS_VERSION) > 43:
            bootstrap_patch = open('%s/bootstrap_patch.sh' % plandir).read()
            bootstrap_service = open('%s/bootstrap_patch.service' % plandir).read()
            patch_bootstrap("%s/bootstrap.ign" % clusterdir, bootstrap_patch, bootstrap_service)
    staticdata = gather_dhcp(data, platform)
    domain = data.get('domain')
    if staticdata:
        pprint("Deploying helper dhcp node" % image)
        staticdata.update({'network': network, 'dhcp_image': helper_image, 'prefix': cluster,
                          domain: '%s.%s' % (cluster, domain)})
        result = config.plan(plan, inputfile='%s/dhcp.yml' % plandir, overrides=staticdata)
        if result['result'] != 'success':
            os._exit(1)
    if platform in virtplatforms:
        if data.get('virtual_router_id') is None:
            overrides['virtual_router_id'] = word2number(cluster)
        pprint("Using keepalived virtual_router_id %s" % overrides['virtual_router_id'])
        pprint("Using %s for api vip...." % api_ip)
        host_ip = api_ip if platform != "openstack" else public_api_ip
        ignore_hosts = data.get('ignore_hosts', False)
        if ignore_hosts:
            warning("Ignoring /etc/hosts")
        elif not os.path.exists("/i_am_a_container"):
            hosts = open("/etc/hosts").readlines()
            wronglines = [e for e in hosts if not e.startswith('#') and "api.%s.%s" % (cluster, domain) in e and
                          host_ip not in e]
            if ingress_ip is not None:
                o = "oauth-openshift.apps.%s.%s" % (cluster, domain)
                wrongingresses = [e for e in hosts if not e.startswith('#') and o in e and ingress_ip not in e]
                wronglines.extend(wrongingresses)
            for wrong in wronglines:
                warning("Cleaning wrong entry %s in /etc/hosts" % wrong)
                call("sudo sed -i '/%s/d' /etc/hosts" % wrong.strip(), shell=True)
            hosts = open("/etc/hosts").readlines()
            correct = [e for e in hosts if not e.startswith('#') and "api.%s.%s" % (cluster, domain) in e and
                       host_ip in e]
            if not correct:
                entries = ["api.%s.%s" % (cluster, domain)]
                ingress_entries = ["%s.%s.%s" % (x, cluster, domain) for x in ['console-openshift-console.apps',
                                   'oauth-openshift.apps', 'prometheus-k8s-openshift-monitoring.apps']]
                if ingress_ip is None:
                    entries.extend(ingress_entries)
                entries = ' '.join(entries)
                call("sudo sh -c 'echo %s %s >> /etc/hosts'" % (host_ip, entries), shell=True)
                if ingress_ip is not None:
                    entries = ' '.join(ingress_entries)
                    call("sudo sh -c 'echo %s %s >> /etc/hosts'" % (ingress_ip, entries), shell=True)
        else:
            entries = ["api.%s.%s" % (cluster, domain)]
            ingress_entries = ["%s.%s.%s" % (x, cluster, domain) for x in ['console-openshift-console.apps',
                                                                           'oauth-openshift.apps',
                                                                           'prometheus-k8s-openshift-monitoring.apps']]
            if ingress_ip is None:
                entries.extend(ingress_entries)
            entries = ' '.join(entries)
            call("sh -c 'echo %s %s >> /etc/hosts'" % (host_ip, entries), shell=True)
            if os.path.exists('/etcdir/hosts'):
                call("sh -c 'echo %s %s >> /etcdir/hosts'" % (host_ip, entries), shell=True)
                if ingress_ip is not None:
                    entries = ' '.join(ingress_entries)
                    call("sudo sh -c 'echo %s %s >> /etcdir/hosts'" % (ingress_ip, entries), shell=True)
        if platform in ['openstack', 'vsphere'] or (platform == 'packet' and config.k.tunnelhost is None):
            # bootstrap ignition is too big in those platforms so we deploy a temporary web server to serve it
            helper_overrides = {}
            if helper_image is None:
                images = [v for v in k.volumes() if 'centos' in v.lower() or 'fedora' in v.lower()]
                if images:
                    image = os.path.basename(images[0])
                else:
                    helper_image = "CentOS-7-x86_64-GenericCloud.qcow2"
                    pprint("Downloading centos helper image")
                    result = config.handle_host(pool=config.pool, image="centos7", download=True,
                                                update_profile=False)
                pprint("Using helper image %s" % helper_image)
            else:
                images = [v for v in k.volumes() if helper_image in v]
                if not images:
                    error("Missing image %s. Indicate correct helper image in your parameters file" % helper_image)
                    os._exit(1)
            if platform == 'openstack':
                helper_overrides['flavor'] = "m1.medium"
            helper_overrides['nets'] = [network]
            helper_overrides['plan'] = cluster
            bootstrap_helper_name = "%s-bootstrap-helper" % cluster
            cmds = ["iptables -F", "yum -y install httpd", "setenforce 0"]
            if platform == 'packet':
                config.k.tunnelhost = bootstrap_helper_ip
                cmds.append("sed -i 's/apache/root/' /etc/httpd/conf/httpd.conf")
            cmds.append("systemctl enable --now httpd")
            helper_overrides['cmds'] = cmds
            config.create_vm("%s-bootstrap-helper" % cluster, helper_image, overrides=helper_overrides, wait=True)
            bootstrap_helper_ip, bootstrap_helper_vmport = _ssh_credentials(bootstrap_helper_name)[1:]
            source, destination = "%s/bootstrap.ign" % clusterdir, "/var/www/html/bootstrap"
            scpcmd = scp(bootstrap_helper_name, ip=bootstrap_helper_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=False, insecure=True,
                         vmport=bootstrap_helper_vmport)
            os.system(scpcmd)
            cmd = "chown apache.apache /var/www/html/bootstrap"
            sshcmd = ssh(bootstrap_helper_name, ip=bootstrap_helper_ip, user='root', tunnel=config.tunnel,
                         tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                         tunneluser=config.tunneluser, insecure=True, cmd=cmd, vmport=bootstrap_helper_vmport)
            os.system(sshcmd)
            sedcmd = 'sed "s@https://api-int.%s.%s:22623/config/master@http://%s/bootstrap@" ' % (cluster, domain,
                                                                                                  bootstrap_helper_ip)
            sedcmd += '%s/master.ign' % clusterdir
            sedcmd += ' > %s/bootstrap.ign' % clusterdir
            call(sedcmd, shell=True)
            sedcmd = 'sed "s@https://api-int.%s.%s:22623/config/master@http://%s/worker@" ' % (cluster, domain,
                                                                                               bootstrap_helper_ip)
            sedcmd += '%s/master.ign' % clusterdir
            sedcmd += ' > %s/worker.ign' % clusterdir
            call(sedcmd, shell=True)
        new_api_ip = api_ip if not ipv6 else "[%s]" % api_ip
        sedcmd = 'sed -i "s@https://api-int.%s.%s:22623/config@http://%s:22624/config@"' % (cluster, domain, new_api_ip)
        sedcmd += ' %s/master.ign %s/worker.ign' % (clusterdir, clusterdir)
        call(sedcmd, shell=True)
    if platform in cloudplatforms:
        bootstrap_helper_name = "%s-bootstrap-helper" % cluster
        helper_overrides = {'reservedns': True, 'domain': '%s.%s' % (cluster, domain), 'tags': [tag], 'plan': cluster,
                            'nets': [network]}
        config.create_vm("%s-bootstrap-helper" % cluster, helper_image, overrides=helper_overrides)
        status = ""
        while status != "running":
            status = k.info(bootstrap_helper_name).get('status')
            pprint("Waiting 5s for bootstrap helper node to be running...")
            sleep(5)
        sleep(5)
        bootstrap_helper_ip, bootstrap_helper_vmport = _ssh_credentials(k, bootstrap_helper_name)[1:]
        cmd = "iptables -F ; yum -y install httpd ; systemctl start httpd"
        sshcmd = ssh(bootstrap_helper_name, ip=bootstrap_helper_ip, user='root', tunnel=config.tunnel,
                     tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                     insecure=True, cmd=cmd, vmport=bootstrap_helper_vmport)
        os.system(sshcmd)
        source, destination = "%s/bootstrap.ign" % clusterdir, "/var/www/html/bootstrap"
        scpcmd = scp(bootstrap_helper_name, ip=bootstrap_helper_ip, user='root', source=source, destination=destination,
                     tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                     tunneluser=config.tunneluser, download=False, insecure=True, vmport=bootstrap_helper_vmport)
        os.system(scpcmd)
        sedcmd = 'sed "s@https://api-int.%s.%s:22623/config/master@' % (cluster, domain)
        sedcmd += 'http://%s-bootstrap-helper.%s.%s/bootstrap@ "' % (cluster, cluster, domain)
        sedcmd += '%s/master.ign' % clusterdir
        sedcmd += ' > %s/bootstrap.ign' % clusterdir
        call(sedcmd, shell=True)
    if platform in virtplatforms:
        pprint("Deploying bootstrap")
        result = config.plan(plan, inputfile='%s/bootstrap.yml' % plandir, overrides=overrides)
        if result['result'] != 'success':
            os._exit(1)
        pprint("Deploying masters")
        result = config.plan(plan, inputfile='%s/masters.yml' % plandir, overrides=overrides)
        if result['result'] != 'success':
            os._exit(1)
        if platform == 'packet':
            allnodes = ["%s-bootstrap" % cluster] + ["%s-master-%s" % (cluster, num) for num in range(masters)]
            for node in allnodes:
                try:
                    k.add_nic(node, network)
                except Exception as e:
                    error("Hit %s. Continuing still" % str(e))
                    continue
        bootstrapcommand = 'openshift-install --dir=%s wait-for bootstrap-complete' % clusterdir
        bootstrapcommand += ' || %s' % bootstrapcommand
        run = call(bootstrapcommand, shell=True)
        if run != 0:
            error("Leaving environment for debugging purposes")
            error("You can delete it with kcli delete cluster --yes %s" % cluster)
            os._exit(run)
        todelete = ["%s-bootstrap" % cluster]
        if platform in ['openstack', 'vsphere', 'packet']:
            todelete.append("%s-bootstrap-helper" % cluster)
    else:
        pprint("Deploying bootstrap")
        result = config.plan(plan, inputfile='%s/cloud_bootstrap.yml' % plandir, overrides=overrides)
        if result['result'] != 'success':
            os._exit(1)
        pprint("Deploying masters")
        result = config.plan(plan, inputfile='%s/cloud_masters.yml' % plandir, overrides=overrides)
        if result['result'] != 'success':
            os._exit(1)
        call('openshift-install --dir=%s wait-for bootstrap-complete || exit 1' % clusterdir, shell=True)
        todelete = ["%s-bootstrap" % cluster, "%s-bootstrap-helper" % cluster]
    if platform in virtplatforms:
        if workers > 0:
            pprint("Deploying workers")
            if 'name' in overrides:
                del overrides['name']
            if platform in virtplatforms:
                result = config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=overrides)
            elif platform in cloudplatforms:
                result = config.plan(plan, inputfile='%s/cloud_workers.yml' % plandir, overrides=overrides)
            if result['result'] != 'success':
                os._exit(1)
            if platform == 'packet':
                allnodes = ["%s-worker-%s" % (cluster, num) for num in range(workers)]
                for node in allnodes:
                    k.add_nic(node, network)
    call("oc adm taint nodes -l node-role.kubernetes.io/master node-role.kubernetes.io/master:NoSchedule-", shell=True)
    pprint("Deploying certs autoapprover cronjob")
    call("oc create -f %s/autoapprovercron.yml" % clusterdir, shell=True)
    if not minimal:
        installcommand = 'openshift-install --dir=%s wait-for install-complete' % clusterdir
        installcommand += " || %s" % installcommand
        pprint("Launching install-complete step. It will be retried one extra time in case of timeouts")
        call(installcommand, shell=True)
    else:
        kubeconf = os.environ['KUBECONFIG']
        kubepassword = open("%s/auth/auth/kubeadmin-password" % clusterdir).read()
        success("Minimal Cluster ready to be used")
        success("INFO Install Complete")
        info2("To access the cluster as the system:admin user when running 'oc', run export KUBECONFIG=%s" % kubeconf)
        info2("Access the Openshift web-console here: https://console-openshift-console.apps.%s.%s" % (cluster, domain))
        info2("Login to the console with user: kubeadmin, password: %s" % kubepassword)
    for vm in todelete:
        pprint("Deleting %s" % vm)
        k.delete(vm)
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    if apps:
        overrides['openshift_version'] = INSTALLER_VERSION[0:3]
        for app in apps:
            appdir = "%s/apps/%s" % (plandir, app)
            if not os.path.exists(appdir):
                warning("Skipping unsupported app %s" % app)
            else:
                pprint("Adding app %s" % app)
                kube_create_app(config, appdir, overrides=overrides)
