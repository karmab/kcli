#!/usr/bin/env python

from base64 import b64encode
from getpass import getuser
from glob import glob
import json
import os
from socket import gethostbyname
import sys
from ipaddress import ip_network
from kvirt.common import error, pprint, success, warning, info2
from kvirt.common import get_oc, pwd_path
from kvirt.common import get_commit_rhcos, get_latest_fcos, generate_rhcos_iso, olm_app
from kvirt.common import get_installer_rhcos
from kvirt.common import ssh, scp, _ssh_credentials, copy_ipi_credentials, get_ssh_pub_key
from kvirt.defaults import LOCAL_OPENSHIFT_APPS, OPENSHIFT_TAG
import re
from shutil import copy2, move, rmtree, which
from subprocess import call
from tempfile import TemporaryDirectory
from time import sleep
from urllib.request import urlopen, Request
from random import choice
from requests import post
from string import ascii_letters, digits
import yaml


virtplatforms = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere']
cloudplatforms = ['aws', 'gcp', 'ibm']


def backup_paramfile(installparam, clusterdir, cluster, plan, image, dnsconfig):
    with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
        installparam['cluster'] = cluster
        installparam['plan'] = plan
        installparam['image'] = image
        if dnsconfig is not None:
            installparam['dnsclient'] = dnsconfig.client
        yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)


def update_etc_hosts(cluster, domain, host_ip, ingress_ip=None):
    if not os.path.exists("/i_am_a_container"):
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
                call("sh -c 'echo %s %s >> /etcdir/hosts'" % (ingress_ip, entries), shell=True)
        else:
            warning("Make sure to have the following entry in your /etc/hosts")
            warning("%s %s" % (host_ip, entries))


def get_installer_version():
    INSTALLER_VERSION = os.popen('openshift-install version').readlines()[0].split(" ")[1].strip()
    if INSTALLER_VERSION.startswith('v'):
        INSTALLER_VERSION = INSTALLER_VERSION[1:]
    return INSTALLER_VERSION


def get_release_image():
    RELEASE_IMAGE = os.popen('openshift-install version').readlines()[2].split(" ")[2].strip()
    return RELEASE_IMAGE


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


def get_downstream_installer(nightly=False, macosx=False, tag=None, debug=False, baremetal=False,
                             pull_secret='openshift_pull.json'):
    arch = 'arm64' if os.uname().machine == 'aarch64' else None
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
        error("Couldn't find version")
        return 1
    if baremetal:
        repo = 'ocp-dev-preview' if nightly else 'ocp'
        url = "https://mirror.openshift.com/pub/openshift-v4/clients/%s/%s/release.txt" % (repo, version)
        r = urlopen(url).readlines()
        for line in r:
            if 'Pull From:' in str(line):
                openshift_image = line.decode().replace('Pull From: ', '').strip()
                break
        target = 'openshift-baremetal-install'
        cmd = "oc adm release extract --registry-config %s --command=%s --to . %s" % (pull_secret, target,
                                                                                      openshift_image)
        cmd += "; mv %s openshift-install ; chmod 700 openshift-install" % target
        return call(cmd, shell=True)
    if arch == 'arm64':
        cmd = "curl -s https://mirror.openshift.com/pub/openshift-v4/%s/clients/%s/" % (arch, repo)
    else:
        cmd = "curl -s https://mirror.openshift.com/pub/openshift-v4/clients/%s/" % repo
    cmd += "openshift-install-%s-%s.tar.gz " % (INSTALLSYSTEM, version)
    cmd += "| tar zxf - openshift-install"
    cmd += "; chmod 700 openshift-install"
    if debug:
        pprint(cmd)
    return call(cmd, shell=True)


def get_ci_installer(pull_secret, tag=None, macosx=False, upstream=False, debug=False, baremetal=False):
    arch = 'arm64' if os.uname().machine == 'aarch64' else None
    base = 'openshift' if not upstream else 'origin'
    if tag is None:
        tags = []
        r = urlopen("https://%s-release.ci.openshift.org/graph?format=dot" % base).readlines()
        for line in r:
            tag_match = re.match('.*label="(.*.)", shape=.*', str(line))
            if tag_match is not None:
                tags.append(tag_match.group(1))
        tag = sorted(tags)[-1]
    elif str(tag).startswith('ci-ln'):
        tag = 'registry.build01.ci.openshift.org/%s' % tag
    elif '/' not in str(tag):
        if arch == 'arm64':
            tag = 'registry.ci.openshift.org/ocp-arm64/release-arm64:%s' % tag
        else:
            basetag = 'ocp' if not upstream else 'origin'
            tag = 'registry.ci.openshift.org/%s/release:%s' % (basetag, tag)
    os.environ['OPENSHIFT_RELEASE_IMAGE'] = tag
    msg = 'Downloading openshift-install %s in current directory' % tag
    pprint(msg)
    target = 'openshift-baremetal-install' if baremetal else 'openshift-install'
    if upstream:
        cmd = "oc adm release extract --command=%s --to . %s" % (target, tag)
    else:
        cmd = "oc adm release extract --registry-config %s --command=%s --to . %s" % (pull_secret, target, tag)
    cmd += "; chmod 700 openshift-install"
    if debug:
        pprint(cmd)
    return call(cmd, shell=True)


def get_upstream_installer(macosx=False, tag=None, debug=False):
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
    if debug:
        pprint(cmd)
    return call(cmd, shell=True)


def baremetal_stop(cluster):
    installfile = "%s/install-config.yaml" % os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    with open(installfile) as f:
        data = yaml.safe_load(f)
        hosts = data['platform']['baremetal']['hosts']
        for host in hosts:
            address = host['bmc']['address']
            user, password = host['bmc'].get('username'), host['bmc'].get('password')
            match = re.match(".*(http.*|idrac-virtualmedia.*|redfish-virtualmedia.*)", address)
            address = match.group(1).replace('idrac-virtualmedia', 'https').replace('redfish-virtualmedia', 'https')
            actionaddress = "%s/Actions/ComputerSystem.Reset/" % address
            headers = {'Content-type': 'application/json'}
            post(actionaddress, json={"ResetType": 'ForceOff'}, headers=headers, auth=(user, password), verify=False)


def process_apps(config, clusterdir, apps, overrides):
    if not apps:
        return
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    for app in apps:
        base_data = overrides.copy()
        if isinstance(app, str):
            appname = app
        elif isinstance(app, dict):
            appname = app.get('name')
            if appname is None:
                error(f"Missing name in dict {app}. Skipping")
                continue
            base_data.overrides(app)
        if 'apps_install_cr' in base_data:
            base_data['install_cr'] = base_data['apps_install_cr']
        if appname in LOCAL_OPENSHIFT_APPS:
            name = appname
            app_data = base_data
        else:
            name, source, channel, csv, description, namespace, channels, crd = olm_app(appname)
            if name is None:
                error(f"Couldn't find any app matching {app}. Skipping...")
                continue
            app_data = {'name': name, 'source': source, 'channel': channel, 'namespace': namespace, 'crd': crd}
            app_data.update(base_data)
        pprint(f"Adding app {name}")
        config.create_app_openshift(name, app_data)


def process_postscripts(clusterdir, postscripts):
    if not postscripts:
        return
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    currentdir = pwd_path(".")
    for script in postscripts:
        script_path = os.path.expanduser(script) if script.startswith('/') else '%s/%s' % (currentdir, script)
        pprint("Running script %s" % os.path.basename(script))
        call(script_path, shell=True)


def wait_for_ignition(cluster, domain, role='worker'):
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    ignitionfile = "%s/%s.ign" % (clusterdir, role)
    os.remove(ignitionfile)
    while not os.path.exists(ignitionfile) or os.stat(ignitionfile).st_size == 0:
        try:
            with open(ignitionfile, 'w') as dest:
                req = Request("http://api.%s.%s:22624/config/%s" % (cluster, domain, role))
                req.add_header("Accept", "application/vnd.coreos.ignition+json; version=3.1.0")
                data = urlopen(req).read()
                dest.write(data.decode("utf-8"))
        except:
            pprint("Waiting 10s before retrieving %s ignition data" % role)
            sleep(10)


def scale(config, plandir, cluster, overrides):
    plan = cluster
    client = config.client
    platform = config.type
    k = config.k
    data = {}
    pprint("Scaling on client %s" % client)
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    if os.path.exists(clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'w') as paramfile:
            yaml.safe_dump(data, paramfile)
    image = data.get('image')
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
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        if overrides.get(role, 0) == 0:
            continue
        if platform in virtplatforms:
            os.chdir(os.path.expanduser("~/.kcli"))
            result = config.plan(plan, inputfile='%s/%s.yml' % (plandir, role), overrides=overrides, threaded=threaded)
        elif platform in cloudplatforms:
            result = config.plan(plan, inputfile='%s/cloud_%s.yml' % (plandir, role), overrides=overrides,
                                 threaded=threaded)
        if result['result'] != 'success':
            sys.exit(1)


def create(config, plandir, cluster, overrides, dnsconfig=None):
    k = config.k
    log_level = 'debug' if config.debug else 'info'
    client = config.client
    platform = config.type
    arch = k.get_capabilities()['arch'] if platform == 'kvm' else 'x86_64'
    arch_tag = 'arm64' if arch in ['aarch64', 'arm64'] else 'latest'
    overrides['arch_tag'] = arch_tag
    pprint("Deploying on client %s" % client)
    data = {'domain': 'karmalabs.com',
            'network': 'default',
            'masters': 1,
            'workers': 0,
            'tag': OPENSHIFT_TAG,
            'ipv6': False,
            'pub_key': os.path.expanduser('~/.ssh/id_rsa.pub'),
            'pull_secret': 'openshift_pull.json',
            'version': 'stable',
            'macosx': False,
            'upstream': False,
            'fips': False,
            'apps': [],
            'minimal': False,
            'dualstack': False,
            'kvm_forcestack': False,
            'ipsec': False,
            'sno': False,
            'sno_virtual': False,
            'sno_masters': False,
            'sno_workers': False,
            'sno_wait': True,
            'sno_localhost_fix': False,
            'sno_disable_nics': [],
            'notify': False,
            'async': False,
            'kubevirt_api_service': False,
            'kubevirt_ignore_node_port': False,
            'baremetal': False,
            'sushy': False,
            'coredns': True,
            'mdns': True,
            'retries': 2}
    data.update(overrides)
    if 'cluster' in overrides:
        clustervalue = overrides.get('cluster')
    elif cluster is not None:
        clustervalue = cluster
    else:
        clustervalue = 'testk'
    retries = data.get('retries')
    data['cluster'] = clustervalue
    domain = data.get('domain')
    async_install = data.get('async')
    baremetal_iso = data.get('baremetal')
    baremetal_iso_bootstrap = data.get('baremetal_bootstrap', baremetal_iso)
    baremetal_iso_master = data.get('baremetal_master', baremetal_iso)
    baremetal_iso_worker = data.get('baremetal_worker', baremetal_iso)
    baremetal_iso_any = baremetal_iso_bootstrap or baremetal_iso_master or baremetal_iso_worker
    baremetal_iso_all = baremetal_iso_bootstrap and baremetal_iso_master and baremetal_iso_worker
    notify = data.get('notify')
    postscripts = data.get('postscripts', [])
    pprint("Deploying cluster %s" % clustervalue)
    plan = cluster if cluster is not None else clustervalue
    overrides['kubetype'] = 'openshift'
    apps = overrides.get('apps', [])
    if ('localstorage' in apps or 'ocs' in apps) and 'extra_disks' not in overrides\
            and 'extra_master_disks' not in overrides and 'extra_worker_disks' not in overrides:
        warning("Storage apps require extra disks to be set")
    overrides['kube'] = data['cluster']
    installparam = overrides.copy()
    sno = data.get('sno', False)
    ignore_hosts = data.get('ignore_hosts', False)
    if sno:
        sno_virtual = data.get('sno_virtual')
        sno_masters = data.get('sno_masters')
        sno_workers = data.get('sno_workers')
        sno_wait = data.get('sno_wait')
        if sno_virtual:
            sno_memory = data.get('master_memory', data.get('memory', 8192))
            if sno_memory < 20480:
                error("Sno won't deploy with less than 20gb of RAM")
                sys.exit(1)
            sno_cpus = data.get('master_numcpus', data.get('numcpus', 4))
            if sno_cpus < 8:
                error("Sno won't deploy with less than 8 cpus")
                sys.exit(1)
        sno_disk = data.get('sno_disk')
        if sno_disk is None:
            warning("sno_disk will be discovered")
        masters = 1
        workers = 0
        data['mdns'] = False
        data['kubetype'] = 'openshift'
        data['kube'] = data['cluster']
        if data.get('network_type', 'OpenShiftSDN') == 'OpenShiftSDN':
            warning("Forcing network_type to OVNKubernetes")
            data['network_type'] = 'OVNKubernetes'
    masters = data.get('masters', 1)
    if masters == 0:
        error("Invalid number of masters")
        sys.exit(1)
    network = data.get('network')
    ipv6 = data['ipv6']
    disconnected_deploy = data.get('disconnected_deploy', False)
    disconnected_reuse = data.get('disconnected_reuse', False)
    disconnected_operators = data.get('disconnected_operators', [])
    disconnected_certified_operators = data.get('disconnected_certified_operators', [])
    disconnected_community_operators = data.get('disconnected_community_operators', [])
    disconnected_marketplace_operators = data.get('disconnected_marketplace_operators', [])
    disconnected_url = data.get('disconnected_url')
    disconnected_user = data.get('disconnected_user')
    disconnected_password = data.get('disconnected_password')
    disconnected_prefix = data.get('disconnected_prefix', 'ocp4')
    ipsec = data.get('ipsec')
    upstream = data.get('upstream')
    metal3 = data.get('metal3')
    sushy = data.get('sushy')
    if not data.get('coredns'):
        warning("You will need to provide DNS records for api and ingress on your own")
    mdns = data.get('mdns')
    sno_localhost_fix = data.get('sno_localhost_fix', False)
    kubevirt_api_service, kubevirt_api_service_node_port = False, False
    kubevirt_ignore_node_port = data['kubevirt_ignore_node_port']
    version = data.get('version')
    tag = data.get('tag')
    if str(tag) == '4.1':
        tag = '4.10'
        data['tag'] = tag
    if os.path.exists('openshift-install'):
        pprint("Removing old openshift-install")
        os.remove('openshift-install')
    if os.path.exists('coreos-installer'):
        pprint("Removing old coreos-installer")
        os.remove('coreos-installer')
    minimal = data.get('minimal')
    if version not in ['ci', 'nightly', 'stable']:
        error(f"Incorrect version {version}")
        sys.exit(1)
    else:
        pprint("Using %s version" % version)
    cluster = data.get('cluster')
    image = data.get('image')
    ipi = data.get('ipi', False)
    api_ip = data.get('api_ip')
    cidr = None
    if platform in virtplatforms and not sno and not ipi and api_ip is None:
        network = data.get('network')
        networkinfo = k.info_network(network)
        if not networkinfo:
            sys.exit(1)
        if platform == 'kvm' and networkinfo['type'] == 'routed':
            cidr = networkinfo['cidr']
            api_index = 2 if ':' in cidr else -3
            api_ip = str(ip_network(cidr)[api_index])
            warning("Using %s as api_ip" % api_ip)
            overrides['api_ip'] = api_ip
        elif platform == 'kubevirt':
            selector = {'kcli/plan': plan, 'kcli/role': 'master'}
            service_type = "LoadBalancer" if k.access_mode == 'LoadBalancer' else 'NodePort'
            if service_type == 'NodePort':
                kubevirt_api_service_node_port = True
            api_ip = k.create_service("%s-api" % cluster, k.namespace, selector, _type=service_type,
                                      ports=[6443, 22623, 22624, 80, 443], openshift_hack=True)
            if api_ip is None:
                error("Couldnt gather an api_ip from your cluster")
                sys.exit(1)
            else:
                pprint("Using api_ip %s" % api_ip)
                overrides['api_ip'] = api_ip
                overrides['kubevirt_api_service'] = True
                kubevirt_api_service = True
                overrides['mdns'] = False
        else:
            error("You need to define api_ip in your parameters file")
            sys.exit(1)
    if platform in virtplatforms and not sno and not ipi and ':' in api_ip:
        ipv6 = True
    if ipv6:
        if data.get('network_type', 'OpenShiftSDN') == 'OpenShiftSDN':
            warning("Forcing network_type to OVNKubernetes")
            data['network_type'] = 'OVNKubernetes'
        data['ipv6'] = True
        overrides['ipv6'] = True
        data['disconnected_ipv6_network'] = True
        if not disconnected_deploy and disconnected_url is None:
            warning("Forcing disconnected_deploy to True as no disconnected_url was provided")
            data['disconnected_deploy'] = True
            disconnected_deploy = True
        if sno and not data['dualstack'] and 'extra_args' not in overrides:
            warning("Forcing extra_args to ip=dhcp6 for sno to boot with ipv6")
            data['extra_args'] = 'ip=dhcp6'
    ingress_ip = data.get('ingress_ip')
    if ingress_ip is not None and api_ip is not None and ingress_ip == api_ip:
        ingress_ip = None
        overrides['ingress_ip'] = None
    public_api_ip = data.get('public_api_ip')
    network = data.get('network')
    masters = data.get('masters')
    workers = data.get('workers')
    tag = data.get('tag')
    pub_key = data.get('pub_key')
    pull_secret = pwd_path(data.get('pull_secret')) if not upstream else "%s/fake_pull.json" % plandir
    pull_secret = os.path.expanduser(pull_secret)
    macosx = data.get('macosx')
    if macosx and not os.path.exists('/i_am_a_container'):
        macosx = False
    if platform == 'openstack':
        if data.get('flavor') is None:
            error("Missing flavor in parameter file")
            sys.exit(1)
        if api_ip is None:
            cidr = k.info_network(network)['cidr']
            api_ip = str(ip_network(cidr)[-3])
            data['api_ip'] = api_ip
            warning("Using %s as api_ip" % api_ip)
        if public_api_ip is None:
            public_api_ip = config.k.create_network_port("%s-vip" % cluster, network, ip=api_ip,
                                                         floating=True)['floating']
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
    orikubeconfig = os.environ.get('KUBECONFIG')
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    if which('oc') is None:
        get_oc(macosx=macosx)
    if version == 'ci':
        if '/' not in str(tag):
            if arch in ['aarch64', 'arm64']:
                tag = 'registry.ci.openshift.org/ocp-arm64/release-arm64:%s' % tag
            else:
                basetag = 'ocp' if not upstream else 'origin'
                tag = 'registry.ci.openshift.org/%s/release:%s' % (basetag, tag)
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = tag
        pprint("Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to %s" % tag)
    if which('openshift-install') is None:
        if data.get('ipi', False) and data.get('ipi_platform', platform) in ['kvm', 'libvirt', 'baremetal']:
            baremetal = True
        else:
            baremetal = False
        if upstream:
            run = get_upstream_installer(tag=tag)
        elif version == 'ci' or '/' in str(tag):
            run = get_ci_installer(pull_secret, tag=tag, upstream=upstream, baremetal=baremetal)
        elif version == 'nightly':
            run = get_downstream_installer(nightly=True, tag=tag, baremetal=baremetal, pull_secret=pull_secret)
        else:
            run = get_downstream_installer(tag=tag, baremetal=baremetal, pull_secret=pull_secret)
        if run != 0:
            error("Couldn't download openshift-install")
            sys.exit(run)
        pprint("Move downloaded openshift-install somewhere in your PATH if you want to reuse it")
    else:
        warning("Using existing openshift-install found in your PATH")
    os.environ["PATH"] += ":%s" % os.getcwd()
    if disconnected_url is not None:
        if '/' not in str(tag):
            tag = f'{disconnected_url}/{disconnected_prefix}:{tag}'
            os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = tag
        pprint(f"Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to {tag}")
    INSTALLER_VERSION = get_installer_version()
    COMMIT_ID = os.popen('openshift-install version').readlines()[1].replace('built from commit', '').strip()
    pprint(f"Using installer version {INSTALLER_VERSION}")
    if sno or ipi or baremetal_iso_all:
        pass
    elif image is None:
        image_type = 'openstack' if data.get('kvm_openstack', False) and config.type == 'kvm' else config.type
        region = config.k.region if config.type == 'aws' else None
        if upstream:
            fcos_base = 'stable' if version == 'stable' else 'testing'
            fcos_url = "https://builds.coreos.fedoraproject.org/streams/%s.json" % fcos_base
            image_url = get_latest_fcos(fcos_url, _type=image_type, region=region)
        else:
            try:
                image_url = get_installer_rhcos(_type=image_type, region=region, arch=arch)
            except:
                try:
                    image_url = get_commit_rhcos(COMMIT_ID, _type=image_type, region=region)
                except:
                    error("Couldn't gather the %s image associated to commit %s" % (config.type, COMMIT_ID))
                    error("Force an image in your parameter file")
                    sys.exit(1)
        if platform in ['aws', 'gcp']:
            image = image_url
        else:
            image = os.path.basename(os.path.splitext(image_url)[0])
            if platform == 'ibm':
                image = image.replace('.', '-').replace('_', '-').lower()
            if platform == 'vsphere':
                image = image.replace(f'.{arch}', '')
            images = [v for v in k.volumes() if image in v]
            if not images:
                result = config.handle_host(pool=config.pool, image=image, download=True, update_profile=False,
                                            url=image_url, size=data.get('kubevirt_disk_size'))
                if result['result'] != 'success':
                    sys.exit(1)
        pprint("Using image %s" % image)
    else:
        pprint("Checking if image %s is available" % image)
        images = [v for v in k.volumes() if image in v]
        if not images:
            error("Missing %s. Indicate correct image in your parameters file..." % image)
            sys.exit(1)
    overrides['image'] = image
    static_networking_master, static_networking_worker = False, False
    macentries = []
    vmrules = overrides.get('vmrules', [])
    for entry in vmrules:
        if isinstance(entry, dict):
            hostname = list(entry.keys())[0]
            if isinstance(entry[hostname], dict):
                rule = entry[hostname]
                if 'nets' in rule and isinstance(rule['nets'], list):
                    netrule = rule['nets'][0]
                    if isinstance(netrule, dict) and 'ip' in netrule and 'netmask' in netrule and 'gateway' in netrule:
                        mac, ip = netrule.get('mac'), netrule['ip']
                        netmask, gateway = netrule['netmask'], netrule['gateway']
                        nameserver = netrule.get('dns', gateway)
                        if mac is not None:
                            macentries.append("%s;%s;%s;%s;%s;%s" % (mac, hostname, ip, netmask, gateway, nameserver))
                        if hostname.startswith("%s-master" % cluster):
                            static_networking_master = True
                        elif hostname.startswith("%s-worker" % cluster):
                            static_networking_worker = True
    if macentries and (baremetal_iso_master or baremetal_iso_worker):
        pprint("Creating a macs.txt to include in isos for static networking")
        with open('macs.txt', 'w') as f:
            f.write('\n'.join(macentries))
    overrides['cluster'] = cluster
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
    data['pub_key'] = open(pub_key).read().strip()
    if not data['pub_key'].startswith('ssh-'):
        error(f"File {pub_key} doesnt seem to contain a valid public key")
        sys.exit(1)
    if platform in virtplatforms and disconnected_deploy:
        disconnected_vm = "%s-disconnected" % data.get('disconnected_reuse_name', cluster)
        pprint("Deploying disconnected vm %s" % disconnected_vm)
        data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
        disconnected_plan = "%s-reuse" % plan if disconnected_reuse else plan
        disconnected_overrides = data.copy()
        disconnected_overrides['arch_tag'] = arch_tag
        disconnected_overrides['kube'] = "%s-reuse" % cluster if disconnected_reuse else cluster
        disconnected_overrides['openshift_version'] = INSTALLER_VERSION
        disconnected_overrides['disconnected_operators_version'] = '.'.join(INSTALLER_VERSION.split('.')[:-1])
        disconnected_overrides['openshift_release_image'] = get_release_image()
        data['openshift_release_image'] = disconnected_overrides['openshift_release_image']
        x_apps = ['users', 'autolabeller']
        for app in apps:
            if app not in x_apps and app not in disconnected_operators:
                warning(f"Adding app {app} to disconnected_operators array")
                disconnected_operators.append(app)
        disconnected_overrides['disconnected_operators'] = disconnected_operators
        result = config.plan(disconnected_plan, inputfile='%s/disconnected.yml' % plandir,
                             overrides=disconnected_overrides)
        if result['result'] != 'success':
            sys.exit(1)
        disconnected_ip, disconnected_vmport = _ssh_credentials(k, disconnected_vm)[1:]
        cacmd = "cat /opt/registry/certs/domain.crt"
        cacmd = ssh(disconnected_vm, ip=disconnected_ip, user='root', tunnel=config.tunnel,
                    tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                    insecure=True, cmd=cacmd, vmport=disconnected_vmport)
        disconnected_ca = os.popen(cacmd).read().strip()
        if data.get('ca') is not None:
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
        if disconnected_operators:
            source = "/root/redhat-imageContentSourcePolicy.yaml"
            destination = f"{clusterdir}/redhat-imageContentSourcePolicy.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
            source = "/root/redhat-catalogSource.yaml"
            destination = f"{clusterdir}/redhat-catalogSource.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        if disconnected_certified_operators:
            source = "/root/certified-imageContentSourcePolicy.yaml"
            destination = f"{clusterdir}/certified-imageContentSourcePolicy.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
            source = "/root/certified-catalogSource.yaml"
            destination = f"{clusterdir}/certified-catalogSource.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        if disconnected_community_operators:
            source = "/root/community-imageContentSourcePolicy.yaml"
            destination = f"{clusterdir}/community-imageContentSourcePolicy.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
            source = "/root/community-catalogSource.yaml"
            destination = f"{clusterdir}/community-catalogSource.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        if disconnected_marketplace_operators:
            source = "/root/redhat-marketplace-imageContentSourcePolicy.yaml"
            destination = f"{clusterdir}/redhat-marketplace-imageContentSourcePolicy.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
            source = "/root/redhat-marketplace-catalogSource.yaml"
            destination = f"{clusterdir}/redhat-marketplace-catalogSource.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = disconnected_version
        pprint("Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to %s" % disconnected_version)
    if disconnected_url is not None and disconnected_user is not None and disconnected_password is not None:
        key = "%s:%s" % (disconnected_user, disconnected_password)
        key = str(b64encode(key.encode('utf-8')), 'utf-8')
        auths = {'auths': {disconnected_url: {'auth': key, 'email': 'jhendrix@karmalabs.com'}}}
        data['pull_secret'] = json.dumps(auths)
    else:
        data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
    if ipi:
        ipi_platform = data.get('ipi_platform', platform)
        if ipi_platform in ['ovirt', 'baremetal', 'vsphere']:
            if data.get('api_ip') is None:
                error("You need to define api_ip in your parameters file")
                sys.exit(1)
            if data.get('ingress_ip') is None:
                error("You need to define ingress_ip in your parameters file")
                sys.exit(1)
            if ipi_platform == 'baremetal' and data['network_type'] == 'OVNKubernetes'\
                    and data.get('baremetal_cidr') is None:
                error("You need to define baremetal_cidr in your parameters file")
                sys.exit(1)
        if ipi_platform not in cloudplatforms + virtplatforms + ['baremetal']:
            warning("Target platform not supported in kcli, you will need to provide credentials on your own")
        if ipi_platform == 'ovirt':
            cluster_id, storage_id, vnic_id = k.openshift_installer_data(data['pool'])
            data['ovirt_cluster_id'] = cluster_id
            data['ovirt_storage_domain_id'] = storage_id
            data['ovirt_vnic_profile_id'] = vnic_id
        if ipi_platform in ['baremetal', 'libvirt', 'kvm']:
            data['libvirt_url'] = k.url
        if ipi_platform == 'baremetal':
            baremetal_masters = data.get('baremetal_masters', [])
            baremetal_workers = data.get('baremetal_workers', [])
            if not baremetal_masters:
                error("You need to define baremetal_masters in your parameters file")
                sys.exit(1)
            if len(baremetal_masters) != masters:
                warning("Forcing masters number to match baremetal_masters length")
                masters = len(baremetal_masters)
                data['masters'] = masters
            if len(baremetal_workers) != workers:
                warning("Forcing worker number to match baremetal_workers length")
                workers = len(baremetal_workers)
                data['workers'] = workers
        copy_ipi_credentials(platform, k)
    installconfig = config.process_inputfile(cluster, "%s/install-config.yaml" % plandir, overrides=data)
    with open("%s/install-config.yaml" % clusterdir, 'w') as f:
        f.write(installconfig)
    with open("%s/install-config.yaml.bck" % clusterdir, 'w') as f:
        f.write(installconfig)
    if ipi:
        if ipi_platform in ['baremetal', 'vsphere', 'ovirt']:
            if ignore_hosts:
                warning("Ignoring /etc/hosts")
            else:
                update_etc_hosts(cluster, domain, data['api_ip'], data['ingress_ip'])
        if ipi_platform in ['kvm', 'libvirt']:
            run = call('openshift-install --dir=%s --log-level=%s create manifests' % (clusterdir, log_level),
                       shell=True)
            if run != 0:
                error("Leaving environment for debugging purposes")
                sys.exit(run)
            mastermanifest = "%s/openshift/99_openshift-cluster-api_master-machines-0.yaml" % clusterdir
            workermanifest = "%s/openshift/99_openshift-cluster-api_worker-machineset-0.yaml" % clusterdir
            master_memory = data.get('master_memory') if data.get('master_memory') is not None else data['memory']
            worker_memory = data.get('worker_memory') if data.get('worker_memory') is not None else data['memory']
            call('sed -i "s/domainMemory: .*/domainMemory: %s/" %s' % (master_memory, mastermanifest), shell=True)
            call('sed -i "s/domainMemory: .*/domainMemory: %s/" %s' % (worker_memory, workermanifest), shell=True)
            master_numcpus = data.get('master_numcpus') if data.get('master_numcpus') is not None else data['numcpus']
            worker_numcpus = data.get('worker_numcpus') if data.get('worker_numcpus') is not None else data['numcpus']
            call('sed -i "s/domainVcpu: .*/domainVcpu: %s/" %s' % (master_numcpus, mastermanifest), shell=True)
            call('sed -i "s/domainVcpu: .*/domainVcpu: %s/" %s' % (worker_numcpus, workermanifest), shell=True)
            old_libvirt_url = data['libvirt_url']
            if 'ssh' in old_libvirt_url or old_libvirt_url == 'qemu:///system':
                warning("Patching machineset providerSpec uri to allow provisioning workers")
                warning("Put a valid private key in /tmp/id_rsa in the machine-api-controllers pod")
                new_libvirt_url = old_libvirt_url
                if new_libvirt_url == 'qemu:///system':
                    new_libvirt_url = 'qemu+ssh://%s@192.168.122.1/system?no_verify=1&keyfile=/tmp/id_rsa' % getuser()
                    new_libvirt_url += "&known_hosts_verify=1"
                elif 'no_verify' not in new_libvirt_url:
                    if '?' in new_libvirt_url:
                        new_libvirt_url += '&no_verify=1'
                    else:
                        new_libvirt_url += '?no_verify=1'
                elif 'keyfile' in new_libvirt_url:
                    match = re.match('.*keyfile=(.*)', new_libvirt_url)
                    old_keyfile = match.group(1)
                    new_libvirt_url = new_libvirt_url.replace(old_keyfile, '/tmp/id_rsa')
                    if '?' in new_libvirt_url:
                        new_libvirt_url += '&keyfile=/tmp/id_rsa'
                    else:
                        new_libvirt_url += '?keyfile=/tmp/id_rsa'
                new_libvirt_url = new_libvirt_url.replace('&', '\\&')
                call('sed -i "s#uri:.*#uri: %s#" %s' % (new_libvirt_url, workermanifest), shell=True)
            dnsmasqfile = "/etc/NetworkManager/dnsmasq.d/%s.%s.conf" % (cluster, domain)
            dnscmd = 'echo -e "[main]\ndns=dnsmasq" > /etc/NetworkManager/conf.d/dnsmasq.conf'
            dnscmd += "; echo server=/%s.%s/192.168.126.1 > %s" % (cluster, domain, dnsmasqfile)
            dnscmd += "; systemctl restart NetworkManager"
            if k.host in ['localhost', '127.0.0.1'] and k.user == 'root':
                call(dnscmd, shell=True)
            else:
                warning("Run the following commands on %s as root" % k.host)
                pprint(dnscmd)
        if ipi_platform == 'baremetal':
            pprint("Stopping nodes through redfish")
            baremetal_stop(cluster)
    run = call('openshift-install --dir=%s --log-level=%s create manifests' % (clusterdir, log_level), shell=True)
    if run != 0:
        error("Leaving environment for debugging purposes")
        error("You can delete it with kcli delete kube --yes %s" % cluster)
        sys.exit(run)
    if minimal:
        warning("Deploying cvo overrides to provide a minimal install")
        with open("%s/cvo-overrides.yaml" % plandir) as f:
            cvo_override = f.read()
        with open("%s/manifests/cvo-overrides.yaml" % clusterdir, "a") as f:
            f.write(cvo_override)
    ntp_server = data.get('ntp_server')
    if ntp_server is not None:
        ntp_data = config.process_inputfile(cluster, "%s/chrony.conf" % plandir, overrides={'ntp_server': ntp_server})
        for role in ['master', 'worker']:
            ntp = config.process_inputfile(cluster, "%s/99-chrony.yaml" % plandir,
                                           overrides={'role': role, 'ntp_data': ntp_data})
            with open("%s/manifests/99-chrony-%s.yaml" % (clusterdir, role), 'w') as f:
                f.write(ntp)
    manifestsdir = pwd_path("manifests")
    if os.path.exists(manifestsdir) and os.path.isdir(manifestsdir):
        for f in glob("%s/*.y*ml" % manifestsdir):
            pprint(f"Injecting manifest {f}")
            copy2(f, "%s/openshift" % clusterdir)
    for yamlfile in glob(f"{clusterdir}/*.yaml"):
        if os.stat(yamlfile).st_size == 0:
            warning(f"Skipping empty file {yamlfile}")
        elif 'catalogSource' in yamlfile or 'imageContentSourcePolicy' in yamlfile:
            copy2(yamlfile, f"{clusterdir}/openshift")
    if 'network_type' in data and data['network_type'] == 'Calico':
        with TemporaryDirectory() as tmpdir:
            calicodata = {'clusterdir': clusterdir}
            calicoscript = config.process_inputfile(cluster, "%s/calico.sh.j2" % plandir, overrides=calicodata)
            with open("%s/calico.sh" % tmpdir, 'w') as f:
                f.write(calicoscript)
            call('bash %s/calico.sh' % tmpdir, shell=True)
    if ipsec:
        copy2("%s/99-ipsec.yaml" % plandir, "%s/openshift" % clusterdir)
    if workers == 0 or not mdns or kubevirt_api_service:
        copy2('%s/99-scheduler.yaml' % plandir, "%s/openshift" % clusterdir)
    if disconnected_operators:
        if os.path.exists('%s/imageContentSourcePolicy.yaml' % clusterdir):
            copy2('%s/imageContentSourcePolicy.yaml' % clusterdir, "%s/openshift" % clusterdir)
        if os.path.exists('%s/catalogsource.yaml' % clusterdir):
            copy2('%s/catalogsource.yaml' % clusterdir, "%s/openshift" % clusterdir)
        copy2('%s/99-operatorhub.yaml' % plandir, "%s/openshift" % clusterdir)
    if ipi:
        run = call('openshift-install --dir=%s --log-level=%s create cluster' % (clusterdir, log_level), shell=True)
        if run != 0:
            error("Leaving environment for debugging purposes")
        process_apps(config, clusterdir, apps, overrides)
        process_postscripts(clusterdir, postscripts)
        sys.exit(run)
    autoapprover = config.process_inputfile(cluster, "%s/autoapprovercron.yml" % plandir, overrides=data)
    with open("%s/autoapprovercron.yml" % clusterdir, 'w') as f:
        f.write(autoapprover)
    for f in glob("%s/customisation/*.yaml" % plandir):
        if '99-ingress-controller.yaml' in f:
            ingressrole = 'master' if workers == 0 or not mdns or kubevirt_api_service else 'worker'
            replicas = masters if workers == 0 or not mdns or kubevirt_api_service else workers
            ingressconfig = config.process_inputfile(cluster, f, overrides={'replicas': replicas, 'role': ingressrole,
                                                                            'cluster': cluster, 'domain': domain})
            with open("%s/openshift/99-ingress-controller.yaml" % clusterdir, 'w') as _f:
                _f.write(ingressconfig)
            continue
        if '99-autoapprovercron-cronjob.yaml' in f:
            registry = disconnected_url if disconnected_url is not None else 'quay.io'
            cronfile = config.process_inputfile(cluster, f, overrides={'registry': registry, 'arch_tag': arch_tag})
            with open("%s/openshift/99-autoapprovercron-cronjob.yaml" % clusterdir, 'w') as _f:
                _f.write(cronfile)
            continue
        if '99-monitoring.yaml' in f:
            monitoring_retention = data['monitoring_retention']
            monitoringfile = config.process_inputfile(cluster, f, overrides={'retention': monitoring_retention})
            with open("%s/openshift/99-monitoring.yaml" % clusterdir, 'w') as _f:
                _f.write(monitoringfile)
            continue
        copy2(f, "%s/openshift" % clusterdir)
    if async_install:
        registry = disconnected_url if disconnected_url is not None else 'quay.io'
        if not baremetal_iso_bootstrap:
            deletionfile = "%s/99-bootstrap-deletion.yaml" % plandir
            deletionfile = config.process_inputfile(cluster, deletionfile, overrides={'cluster': cluster,
                                                                                      'registry': registry,
                                                                                      'arch_tag': arch_tag})
            with open("%s/openshift/99-bootstrap-deletion.yaml" % clusterdir, 'w') as _f:
                _f.write(deletionfile)
            oriconf = os.path.expanduser('~/.kcli')
            orissh = os.path.expanduser('~/.ssh')
            with TemporaryDirectory() as tmpdir:
                if config.type == 'kvm' and config.k.host in ['localhost', '127.0.0.1']:
                    oriconf = f"{tmpdir}/.kcli"
                    orissh = f"{tmpdir}/.ssh"
                    os.mkdir(oriconf)
                    os.mkdir(orissh)
                    kcliconf = config.process_inputfile(cluster, f"{plandir}/local_kcli_conf.j2",
                                                        overrides={'network': network, 'user': getuser()})
                    with open(f"{oriconf}/config.yml", 'w') as _f:
                        _f.write(kcliconf)
                    sshcmd = f"ssh-keygen -t rsa -N '' -f {orissh}/id_rsa > /dev/null"
                    call(sshcmd, shell=True)
                    authorized_keys_file = os.path.expanduser('~/.ssh/authorized_keys')
                    file_mode = 'a' if os.path.exists(authorized_keys_file) else 'w'
                    with open(authorized_keys_file, file_mode) as f:
                        publickey = open(f"{orissh}/id_rsa.pub").read().strip()
                        f.write(f"\n{publickey}")
                elif config.type == 'kubevirt':
                    destkubeconfig = config.options.get('kubeconfig', orikubeconfig)
                    if destkubeconfig is not None:
                        destkubeconfig = os.path.expanduser(destkubeconfig)
                        copy2(destkubeconfig, f"{oriconf}/kubeconfig")
                    oriconf = f"{tmpdir}/.kcli"
                    os.mkdir(oriconf)
                    kubeconfig_overrides = {'kubeconfig': True if destkubeconfig is not None else False}
                    kcliconf = config.process_inputfile(cluster, f"{plandir}/kubevirt_kcli_conf.j2",
                                                        overrides=kubeconfig_overrides)
                    with open(f"{oriconf}/config.yml", 'w') as _f:
                        _f.write(kcliconf)
                ns = "openshift-kcli-infra"
                dest = f"{clusterdir}/openshift/99-kcli-conf-cm.yaml"
                cmcmd = f'KUBECONFIG={plandir}/fake_kubeconfig.json '
                cmcmd += f"oc create cm -n {ns} kcli-conf --from-file={oriconf} --dry-run=client -o yaml > {dest}"
                call(cmcmd, shell=True)
                dest = f"{clusterdir}/openshift/99-kcli-ssh-cm.yaml"
                cmcmd = f'KUBECONFIG={plandir}/fake_kubeconfig.json  '
                cmcmd += f"oc create cm -n {ns} kcli-ssh --from-file={orissh} --dry-run=client -o yaml > {dest}"
                call(cmcmd, shell=True)
            deletionfile2 = f"{plandir}/99-bootstrap-deletion-2.yaml"
            deletionfile2 = config.process_inputfile(cluster, deletionfile2, overrides={'registry': registry,
                                                                                        'arch_tag': arch_tag})
            with open(f"{clusterdir}/openshift/99-bootstrap-deletion-2.yaml", 'w') as _f:
                _f.write(deletionfile2)
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
                                                                                  'arch_tag': arch_tag,
                                                                                  'cmds': notifycmds,
                                                                                  'mailcontent': mailcontent})
            with open(f"{clusterdir}/openshift/99-notifications.yaml", 'w') as _f:
                _f.write(notifyfile)
    if apps and (async_install or sno):
        final_apps = []
        for a in apps:
            if isinstance(a, str) and a not in ['users', 'autolabellers']:
                final_apps.append(a)
            elif isinstance(a, dict) and 'name' in a:
                final_apps.append(a['name'])
            else:
                error(f"Invalid app {a}. Skipping")
        appsfile = f"{plandir}/99-apps.yaml"
        appsfile = config.process_inputfile(cluster, appsfile, overrides={'registry': registry,
                                                                          'arch_tag': arch_tag,
                                                                          'apps': final_apps})
        with open(f"{clusterdir}/openshift/99-apps.yaml", 'w') as _f:
            _f.write(appsfile)
        appdir = f"{plandir}/apps"
        apps_namespace = {'advanced-cluster-management': 'open-cluster-management',
                          'kubevirt-hyperconverged': 'openshift-cnv',
                          'local-storage-operator': 'openshift-local-storage',
                          'ocs-operator': 'openshift-storage', 'autolabeller': 'autorules'}
        apps = [a for a in apps if a not in ['users']]
        for appname in apps:
            app_data = data.copy()
            if data.get('apps_install_cr') and os.path.exists(f"{appdir}/{appname}/cr.yml"):
                app_data['namespace'] = apps_namespace[appname]
                cr_content = config.process_inputfile(cluster, f"{appdir}/{appname}/cr.yml", overrides=app_data)
                rendered = config.process_inputfile(cluster, f"{plandir}/99-apps-cr.yaml",
                                                    overrides={'registry': registry,
                                                               'arch_tag': arch_tag,
                                                               'app': appname,
                                                               'cr_content': cr_content})
                with open("%s/openshift/99-apps-%s.yaml" % (clusterdir, appname), 'w') as g:
                    g.write(rendered)
    if metal3:
        copy2(f"{plandir}/99-metal3-provisioning.yaml", f"{clusterdir}/openshift")
    if sushy:
        if config.type != 'kvm':
            warning(f"Ignoring sushy request as platform is {config.type}")
        else:
            with TemporaryDirectory() as tmpdir:
                copy2(f"{plandir}/sushy/deployment.yaml", f"{clusterdir}/openshift/99-sushy-deployment.yaml")
                copy2(f"{plandir}/sushy/service.yaml", f"{clusterdir}/openshift/99-sushy-service.yaml")
                listen = "::" if ':' in api_ip else "0.0.0.0"
                sushyconf = config.process_inputfile(cluster, f"{plandir}/sushy/conf.j2",
                                                     overrides={'network': network, 'listen': listen})
                with open(f"{tmpdir}/sushy.conf", 'w') as _f:
                    _f.write(sushyconf)
                # routedata = config.process_inputfile(cluster, f"{plandir}/sushy/route.yaml",
                #                                     overrides={'cluster': cluster, 'domain': domain})
                # with open(f"{clusterdir}/openshift/99-sushy-route.yaml", 'w') as _f:
                #    _f.write(routedata)
                if config.k.host in ['localhost', '127.0.0.1']:
                    sshcmd = f"ssh-keygen -t rsa -N '' -f {tmpdir}/id_rsa > /dev/null"
                    call(sshcmd, shell=True)
                    authorized_keys_file = os.path.expanduser('~/.ssh/authorized_keys')
                    file_mode = 'a' if os.path.exists(authorized_keys_file) else 'w'
                    with open(authorized_keys_file, file_mode) as f:
                        publickey = open(f"{tmpdir}/id_rsa.pub").read().strip()
                        f.write(f"\n{publickey}")
                else:
                    privkey = get_ssh_pub_key().replace('.pub', '')
                    copy2(privkey, f"{tmpdir}/id_rsa")
                dest = f"{clusterdir}/openshift/99-sushy-cm.yaml"
                cmcmd = f'KUBECONFIG={plandir}/fake_kubeconfig.json  '
                cmcmd += f"oc create cm -n openshift-kcli-infra sushy-credentials --from-file={tmpdir} --dry-run=client"
                cmcmd += f" -o yaml > {dest}"
                call(cmcmd, shell=True)
    if sno:
        sno_name = f"{cluster}-sno"
        sno_files = []
        sno_disable_nics = data.get('sno_disable_nics', [])
        if ipv6 or sno_disable_nics:
            nm_data = config.process_inputfile(cluster, f"{plandir}/ipv6.conf", overrides=data)
            sno_files.append({'path': "/etc/NetworkManager/conf.d/ipv6.conf", 'data': nm_data})
        sno_dns = data.get('sno_dns', True)
        if sno_dns:
            coredns_data = config.process_inputfile(cluster, f"{plandir}/staticpods/coredns.yml", overrides=data)
            corefile_data = config.process_inputfile(cluster, f"{plandir}/Corefile", overrides=data)
            forcedns_data = config.process_inputfile(cluster, f"{plandir}/99-forcedns", overrides=data)
            sno_files.extend([{'path': "/etc/kubernetes/manifests/coredns.yml", 'data': coredns_data},
                              {'path': "/etc/kubernetes/Corefile.template", 'data': corefile_data},
                              {"path": "/etc/NetworkManager/dispatcher.d/99-forcedns", "data": forcedns_data,
                               "mode": int('755', 8)}])
        if api_ip is not None:
            data['virtual_router_id'] = data.get('virtual_router_id') or hash(cluster) % 254 + 1
            virtual_router_id = data['virtual_router_id']
            pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
            data['auth_pass'] = ''.join(choice(ascii_letters + digits) for i in range(5))
            vips = [api_ip, ingress_ip] if ingress_ip is not None else [api_ip]
            pprint("Injecting keepalived static pod with %s" % ','.join(vips))
            keepalived_data = config.process_inputfile(cluster, f"{plandir}/staticpods/keepalived.yml", overrides=data)
            keepalivedconf_data = config.process_inputfile(cluster, f"{plandir}/keepalived.conf", overrides=data)
            sno_files.extend([{"path": "/etc/kubernetes/manifests/keepalived.yml", "data": keepalived_data},
                              {"path": "/etc/kubernetes/keepalived.conf.template", "data": keepalivedconf_data}])
        if sno_files:
            rendered = config.process_inputfile(cluster, f"{plandir}/99-sno.yaml", overrides={'files': sno_files})
            with open(f"{clusterdir}/openshift/99-sno.yaml", 'w') as f:
                f.write(rendered)
        if sno_localhost_fix:
            localmaster = config.process_inputfile(cluster, f"{plandir}/99-localhost-fix.yaml",
                                                   overrides={'role': 'master'})
            with open(f"{clusterdir}/openshift/99-localhost-fix-master.yaml", 'w') as _f:
                _f.write(localmaster)
            localworker = config.process_inputfile(cluster, f"{plandir}/99-localhost-fix.yaml",
                                                   overrides={'role': 'worker'})
            with open(f"{clusterdir}/openshift/99-localhost-fix-worker.yaml", 'w') as _f:
                _f.write(localworker)
        if sno_masters:
            ingress = config.process_inputfile(cluster, f"{plandir}/customisation/99-ingress-controller.yaml",
                                               overrides={'role': 'master', 'cluster': cluster, 'domain': domain,
                                                          'replicas': 3})
            with open(f"{clusterdir}/openshift/99-ingress-controller.yaml", 'w') as _f:
                _f.write(ingress)
        pprint("Generating bootstrap-in-place ignition")
        run = call('openshift-install --dir=%s --log-level=%s create single-node-ignition-config' % (clusterdir,
                                                                                                     log_level),
                   shell=True)
        if run != 0:
            error("Hit issue.Leaving")
            sys.exit(run)
        move("%s/bootstrap-in-place-for-live-iso.ign" % clusterdir, "./%s.ign" % sno_name)
        with open("iso.ign", 'w') as f:
            iso_overrides = {}
            extra_args = overrides.get('extra_args')
            if sno_disk is None or extra_args is not None:
                _files = [{"path": "/root/sno-finish.service", "origin": "%s/sno-finish.service" % plandir},
                          {"path": "/usr/local/bin/sno-finish.sh", "origin": "%s/sno-finish.sh" % plandir, "mode": 700}]
                iso_overrides['files'] = _files
            iso_overrides.update(data)
            result = config.create_vm(sno_name, 'rhcos46', overrides=iso_overrides, onlyassets=True)
            pprint("Writing iso.ign to current dir")
            f.write(result['data'])
        if config.type == 'fake':
            pprint("Storing generated iso in current dir")
            generate_rhcos_iso(k, f"{cluster}-sno", 'default', installer=True, extra_args=extra_args)
        elif config.type not in ['kvm', 'kubevirt']:
            pprint("Additional workflow not available on %s" % config.type)
            pprint("Embed iso.ign in rhcos live iso")
            sys.exit(0)
        else:
            iso_pool = data['pool'] or config.pool
            pprint(f"Storing generated iso in pool {iso_pool}")
            generate_rhcos_iso(k, f"{cluster}-sno", iso_pool, installer=True, extra_args=extra_args)
            if sno_virtual:
                warning("You can also get a sno by setting masters to 1")
                pprint("Deploying sno vm")
                result = config.plan(plan, inputfile='%s/sno.yml' % plandir, overrides=data)
                if result['result'] != 'success':
                    sys.exit(1)
                if api_ip is None:
                    while api_ip is None:
                        api_ip = k.info(sno_name).get('ip')
                        pprint("Waiting 5s to retrieve sno ip...")
                        sleep(5)
        if sno_masters:
            if api_ip is None:
                warning("sno masters requires api vip to be defined. Skipping")
            else:
                master_overrides = overrides.copy()
                master_overrides['role'] = 'master'
                master_overrides['image'] = 'rhcos410'
                config.create_openshift_iso(cluster, overrides=master_overrides, installer=True)
        if sno_workers:
            worker_overrides = overrides.copy()
            worker_overrides['role'] = 'worker'
            worker_overrides['image'] = 'rhcos410'
            config.create_openshift_iso(cluster, overrides=worker_overrides, installer=True)
        if ignore_hosts:
            warning("Not updating /etc/hosts as per your request")
        elif api_ip is not None:
            update_etc_hosts(cluster, domain, api_ip)
        else:
            warning("Add the following entry in /etc/hosts if needed")
            dnsentries = ['api', 'console-openshift-console.apps', 'oauth-openshift.apps',
                          'prometheus-k8s-openshift-monitoring.apps']
            dnsentry = ' '.join([f"{entry}.{cluster}.{domain}" for entry in dnsentries])
            warning(f"$your_node_ip {dnsentry}")
        if sno_wait:
            installcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for install-complete'
            installcommand = ' || '.join([installcommand for x in range(retries)])
            pprint("Launching install-complete step. It will be retried extra times in case of timeouts")
            call(installcommand, shell=True)
        else:
            c = os.environ['KUBECONFIG']
            kubepassword = open(f"{clusterdir}/auth/kubeadmin-password").read()
            console = f"https://console-openshift-console.apps.{cluster}.{domain}"
            info2(f"To access the cluster as the system:admin user when running 'oc', run export KUBECONFIG={c}")
            info2(f"Access the Openshift web-console here: {console}")
            info2(f"Login to the console with user: kubeadmin, password: {kubepassword}")
            pprint(f"Plug {cluster}-sno.iso to your SNO node to complete the installation")
            if sno_masters:
                pprint(f"Plug {cluster}-master.iso to get additional masters")
            if sno_workers:
                pprint(f"Plug {cluster}-worker.iso to get additional workers")
        backup_paramfile(installparam, clusterdir, cluster, plan, image, dnsconfig)
        sys.exit(0)
    call('openshift-install --dir=%s --log-level=%s create ignition-configs' % (clusterdir, log_level), shell=True)
    for role in ['master', 'worker']:
        ori = "%s/%s.ign" % (clusterdir, role)
        copy2(ori, "%s.ori" % ori)
    if platform in virtplatforms:
        overrides['virtual_router_id'] = data.get('virtual_router_id') or hash(cluster) % 254 + 1
        virtual_router_id = overrides['virtual_router_id']
        pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
        installparam['virtual_router_id'] = virtual_router_id
        auth_pass = ''.join(choice(ascii_letters + digits) for i in range(5))
        overrides['auth_pass'] = auth_pass
        installparam['auth_pass'] = auth_pass
        pprint(f"Using {api_ip} for api vip....")
        host_ip = api_ip if platform != "openstack" else public_api_ip
        if ignore_hosts or (not kubevirt_ignore_node_port and kubevirt_api_service and kubevirt_api_service_node_port):
            warning("Ignoring /etc/hosts")
        else:
            update_etc_hosts(cluster, domain, host_ip, ingress_ip)
        sedcmd = f'sed -i "s@api-int.{cluster}.{domain}@{api_ip}@" {clusterdir}/master.ign {clusterdir}/worker.ign'
        call(sedcmd, shell=True)
        sedcmd = f'sed -i "s@https://{api_ip}:22623/config@http://{api_ip}:22624/config@"'
        sedcmd += f' {clusterdir}/master.ign {clusterdir}/worker.ign'
        call(sedcmd, shell=True)
        if ipv6:
            sedcmd = f'sed -i "s@{api_ip}@[{api_ip}]@" {clusterdir}/master.ign {clusterdir}/worker.ign'
            call(sedcmd, shell=True)
    if platform in cloudplatforms + ['openstack']:
        bucket = "%s-%s" % (cluster, domain.replace('.', '-'))
        if bucket not in config.k.list_buckets():
            config.k.create_bucket(bucket)
        config.k.upload_to_bucket(bucket, "%s/bootstrap.ign" % clusterdir, public=True)
        bucket_url = config.k.public_bucketfile_url(bucket, "bootstrap.ign")
        if platform == 'openstack':
            ori_url = "http://%s:22624" % api_ip
        else:
            ori_url = "https://api-int.%s.%s:22623" % (cluster, domain)
        sedcmd = 'sed "s@%s/config/master@%s@" ' % (ori_url, bucket_url)
        sedcmd += '%s/master.ign > %s/bootstrap.ign' % (clusterdir, clusterdir)
        call(sedcmd, shell=True)
    if baremetal_iso_any:
        baremetal_iso_overrides = overrides.copy()
        baremetal_iso_overrides['image'] = 'rhcos49'
        baremetal_iso_overrides['noname'] = True
        baremetal_iso_overrides['compact'] = True
        baremetal_iso_overrides['version'] = tag
    backup_paramfile(installparam, clusterdir, cluster, plan, image, dnsconfig)
    if platform in virtplatforms:
        pprint("Deploying bootstrap")
        if baremetal_iso_bootstrap:
            bootstrap_iso_overrides = baremetal_iso_overrides.copy()
            bootstrap_iso_overrides['noname'] = False
            result = config.plan(plan, inputfile='%s/bootstrap.yml' % plandir, overrides=bootstrap_iso_overrides,
                                 onlyassets=True)
            iso_data = result['assets'][0]
            with open('iso.ign', 'w') as f:
                f.write(iso_data)
            ignitionfile = '%s-bootstrap.ign' % cluster
            with open(ignitionfile, 'w') as f:
                f.write(iso_data)
            iso_pool = data['pool'] or config.pool
            generate_rhcos_iso(k, cluster + '-bootstrap', iso_pool, installer=True)
        else:
            result = config.plan(plan, inputfile='%s/bootstrap.yml' % plandir, overrides=overrides)
            if result['result'] != 'success':
                sys.exit(1)
        if static_networking_master and not baremetal_iso_master:
            wait_for_ignition(cluster, domain, role='master')
        pprint("Deploying masters")
        if baremetal_iso_master:
            result = config.plan(plan, inputfile='%s/masters.yml' % plandir, overrides=baremetal_iso_overrides,
                                 onlyassets=True)
            iso_data = result['assets'][0]
            ignitionfile = '%s-master.ign' % cluster
            with open(ignitionfile, 'w') as f:
                f.write(iso_data)
            baremetal_iso_overrides['role'] = 'master'
            config.create_openshift_iso(cluster, overrides=baremetal_iso_overrides, ignitionfile=ignitionfile,
                                        podman=True, installer=True)
            os.remove(ignitionfile)
        else:
            threaded = data.get('threaded', False) or data.get('masters_threaded', False)
            result = config.plan(plan, inputfile='%s/masters.yml' % plandir, overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            sys.exit(1)
        todelete = ["%s-bootstrap" % cluster]
        if dnsconfig is not None:
            dns_overrides = {'api_ip': api_ip, 'ingress_ip': ingress_ip, 'cluster': cluster, 'domain': domain}
            result = dnsconfig.plan(plan, inputfile='%s/cloud_dns.yml' % plandir, overrides=dns_overrides)
            if result['result'] != 'success':
                sys.exit(1)
    else:
        pprint("Deploying bootstrap")
        result = config.plan(plan, inputfile='%s/cloud_bootstrap.yml' % plandir, overrides=overrides)
        if result['result'] != 'success':
            sys.exit(1)
        sedcmd = 'sed -i "s@https://api-int.%s.%s:22623/config@http://api-int.%s.%s:22624/config@"' % (cluster, domain,
                                                                                                       cluster, domain)
        sedcmd += ' %s/master.ign %s/worker.ign' % (clusterdir, clusterdir)
        call(sedcmd, shell=True)
        if platform == 'ibm':
            while api_ip is None:
                api_ip = k.info("%s-bootstrap" % cluster).get('private_ip')
                pprint("Gathering bootstrap private ip")
                sleep(10)
            sedcmd = 'sed -i "s@api-int.%s.%s@%s@" %s/master.ign' % (cluster, domain, api_ip, clusterdir)
            call(sedcmd, shell=True)
        pprint("Deploying masters")
        threaded = data.get('threaded', False) or data.get('masters_threaded', False)
        result = config.plan(plan, inputfile='%s/cloud_masters.yml' % plandir, overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            sys.exit(1)
        if platform == 'ibm':
            first_master_ip = None
            while first_master_ip is None:
                first_master_ip = k.info("%s-master-0" % cluster).get('private_ip')
                pprint("Gathering first master bootstrap ip")
                sleep(10)
            sedcmd = 'sed -i "s@api-int.%s.%s@%s@" %s/worker.ign' % (cluster, domain, first_master_ip, clusterdir)
            call(sedcmd, shell=True)
        result = config.plan(plan, inputfile='%s/cloud_lb_api.yml' % plandir, overrides=overrides)
        if result['result'] != 'success':
            sys.exit(1)
        lb_overrides = {'cluster': cluster, 'domain': domain, 'members': masters, 'role': 'master'}
        if 'dnsclient' in overrides:
            lb_overrides['dnsclient'] = overrides['dnsclient']
        if workers == 0:
            result = config.plan(plan, inputfile='%s/cloud_lb_apps.yml' % plandir, overrides=lb_overrides)
            if result['result'] != 'success':
                sys.exit(1)
        todelete = ["%s-bootstrap" % cluster]
    if not kubevirt_ignore_node_port and kubevirt_api_service and kubevirt_api_service_node_port:
        nodeport = k.get_node_ports('%s-api-svc' % cluster, k.namespace)[6443]
        while True:
            nodehost = k.info("%s-bootstrap" % cluster).get('host')
            if nodehost is not None:
                break
            else:
                pprint("Waiting 5s for bootstrap vm to be up")
                sleep(5)
        nodehostip = gethostbyname(nodehost)
        update_etc_hosts(cluster, domain, nodehostip)
        sedcmd = 'sed -i "s@:6443@:%s@" %s/auth/kubeconfig' % (nodeport, clusterdir)
        call(sedcmd, shell=True)
    if not async_install:
        bootstrapcommand = 'openshift-install --dir=%s --log-level=%s wait-for bootstrap-complete' % (clusterdir,
                                                                                                      log_level)
        bootstrapcommand = ' || '.join([bootstrapcommand for x in range(retries)])
        run = call(bootstrapcommand, shell=True)
        if run != 0:
            error("Leaving environment for debugging purposes")
            error("You can delete it with kcli delete cluster --yes %s" % cluster)
            sys.exit(run)
    if workers > 0:
        if static_networking_worker and not baremetal_iso_worker:
            wait_for_ignition(cluster, domain, role='worker')
        pprint("Deploying workers")
        if 'name' in overrides:
            del overrides['name']
        if platform in virtplatforms:
            if baremetal_iso_worker:
                result = config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=baremetal_iso_overrides,
                                     onlyassets=True)
                iso_data = result['assets'][0]
                ignitionfile = '%s-worker' % cluster
                with open(ignitionfile, 'w') as f:
                    f.write(iso_data)
                baremetal_iso_overrides['role'] = 'worker'
                config.create_openshift_iso(cluster, overrides=baremetal_iso_overrides, ignitionfile=ignitionfile,
                                            podman=True, installer=True)
                os.remove(ignitionfile)
            else:
                threaded = data.get('threaded', False) or data.get('workers_threaded', False)
                result = config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=overrides, threaded=threaded)
            if result['result'] != 'success':
                sys.exit(1)
        elif platform in cloudplatforms:
            result = config.plan(plan, inputfile='%s/cloud_workers.yml' % plandir, overrides=overrides)
            if result['result'] != 'success':
                sys.exit(1)
            lb_overrides['role'] = 'worker'
            lb_overrides['members'] = workers
            result = config.plan(plan, inputfile='%s/cloud_lb_apps.yml' % plandir, overrides=lb_overrides)
            if result['result'] != 'success':
                sys.exit(1)
    if minimal or async_install:
        kubeconf = os.environ['KUBECONFIG']
        kubepassword = open("%s/auth/kubeadmin-password" % clusterdir).read()
        if minimal:
            success("Minimal Cluster ready to be used")
            success("INFO Install Complete")
        if async_install:
            success("Async Cluster created")
            info2("You will need to wait before it is fully available")
        info2("To access the cluster as the system:admin user when running 'oc', run export KUBECONFIG=%s" % kubeconf)
        info2("Access the Openshift web-console here: https://console-openshift-console.apps.%s.%s" % (cluster, domain))
        info2("Login to the console with user: kubeadmin, password: %s" % kubepassword)
        if async_install:
            return
    else:
        installcommand = 'openshift-install --dir=%s --log-level=%s wait-for install-complete' % (clusterdir, log_level)
        installcommand += " || %s" % installcommand
        pprint("Launching install-complete step. It will be retried one extra time in case of timeouts")
        call(installcommand, shell=True)
    for vm in todelete:
        pprint("Deleting %s" % vm)
        k.delete(vm)
        if dnsconfig is not None:
            pprint("Deleting Dns entry for %s in %s" % (vm, domain))
            z = dnsconfig.k
            z.delete_dns(vm, domain)
    if sushy and config.type == 'kvm':
        call("oc expose -n openshift-kcli-infra svc/sushy", shell=True)
    if platform in cloudplatforms:
        bucket = "%s-%s" % (cluster, domain.replace('.', '-'))
        config.k.delete_bucket(bucket)
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    process_apps(config, clusterdir, apps, overrides)
    process_postscripts(clusterdir, postscripts)
    if platform in cloudplatforms and masters == 1 and workers == 0 and data.get('sno_cloud_remove_lb', True):
        pprint("Removing loadbalancers as there is a single master")
        k.delete_loadbalancer("api.%s" % cluster)
        k.delete_loadbalancer("apps.%s" % cluster)
        api_ip = k.info("%s-master-0" % cluster).get('ip')
        k.delete_dns('api.%s' % cluster, domain=domain)
        k.reserve_dns('api.%s' % cluster, domain=domain, ip=api_ip)
        k.delete_dns('apps.%s' % cluster, domain=domain)
        k.reserve_dns('apps.%s' % cluster, domain=domain, ip=api_ip, alias=['*'])
        if platform == 'ibm':
            k._add_sno_security_group(cluster)
