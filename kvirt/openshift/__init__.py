#!/usr/bin/env python

from base64 import b64encode
from glob import glob
import json
import os
import sys
from ipaddress import ip_network
from kvirt.common import error, pprint, success, warning, info2
from kvirt.common import get_oc, pwd_path
from kvirt.common import get_commit_rhcos, get_latest_fcos, generate_rhcos_iso, olm_app
from kvirt.common import get_installer_rhcos
from kvirt.common import ssh, scp, _ssh_credentials, get_ssh_pub_key, boot_baremetal_hosts
from kvirt.defaults import LOCAL_OPENSHIFT_APPS, OPENSHIFT_TAG
import re
from shutil import copy2, move, rmtree, which
from subprocess import call
from time import sleep
from urllib.request import urlopen, Request
from random import choice
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
        wronglines = [e for e in hosts if not e.startswith('#') and f"api.{cluster}.{domain}" in e and
                      host_ip not in e]
        if ingress_ip is not None:
            o = f"oauth-openshift.apps.{cluster}.{domain}"
            wrongingresses = [e for e in hosts if not e.startswith('#') and o in e and ingress_ip not in e]
            wronglines.extend(wrongingresses)
        for wrong in wronglines:
            warning(f"Cleaning wrong entry {wrong} in /etc/hosts")
            call(f"sudo sed -i '/{wrong.strip()}/d' /etc/hosts", shell=True)
        hosts = open("/etc/hosts").readlines()
        correct = [e for e in hosts if not e.startswith('#') and f"api.{cluster}.{domain}" in e and host_ip in e]
        if not correct:
            entries = [f"api.{cluster}.{domain}"]
            ingress_entries = [f"{x}.{cluster}.{domain}" for x in ['console-openshift-console.apps',
                               'oauth-openshift.apps', 'prometheus-k8s-openshift-monitoring.apps']]
            if ingress_ip is None:
                entries.extend(ingress_entries)
            entries = ' '.join(entries)
            call(f"sudo sh -c 'echo {host_ip} {entries} >> /etc/hosts'", shell=True)
            if ingress_ip is not None:
                entries = ' '.join(ingress_entries)
                call(f"sudo sh -c 'echo {ingress_ip} {entries} >> /etc/hosts'", shell=True)
    else:
        entries = [f"api.{cluster}.{domain}"]
        ingress_entries = [f"{x}.{cluster}.{domain}" for x in ['console-openshift-console.apps',
                                                               'oauth-openshift.apps',
                                                               'prometheus-k8s-openshift-monitoring.apps']]
        if ingress_ip is None:
            entries.extend(ingress_entries)
        entries = ' '.join(entries)
        call(f"sh -c 'echo {host_ip} {entries} >> /etc/hosts'", shell=True)
        if os.path.exists('/etcdir/hosts'):
            call(f"sh -c 'echo {host_ip} {entries} >> /etcdir/hosts'", shell=True)
            if ingress_ip is not None:
                entries = ' '.join(ingress_entries)
                call(f"sh -c 'echo {ingress_ip} {entries} >> /etcdir/hosts'", shell=True)
        else:
            warning("Make sure to have the following entry in your /etc/hosts")
            warning(f"{host_ip} {entries}")


def get_installer_version():
    installer_version = os.popen('openshift-install version').readlines()[0].split(" ")[1].strip()
    if installer_version.startswith('v'):
        installer_version = installer_version[1:]
    return installer_version


def offline_image(version='stable', tag='4.12', pull_secret='openshift_pull.json'):
    tag = str(tag).split(':')[-1]
    offline = 'xxx'
    if version in ['ci', 'nightly']:
        if version == "nightly":
            nightly_url = f"https://amd64.ocp.releases.ci.openshift.org/api/v1/releasestream/{tag}.0-0.nightly/latest"
            tag = json.loads(urlopen(nightly_url).read())['pullSpec']
        cmd = f"oc adm release info registry.ci.openshift.org/ocp/release:{tag} -a {pull_secret}"
        for line in os.popen(cmd).readlines():
            if 'Pull From: ' in str(line):
                offline = line.replace('Pull From: ', '').strip()
                break
        return offline
    ocp_repo = 'ocp-dev-preview' if version == 'dev-preview' else 'ocp'
    if version in ['dev-preview', 'stable']:
        target = tag if len(str(tag).split('.')) > 2 else f'latest-{tag}'
        url = f"https://mirror.openshift.com/pub/openshift-v4/clients/{ocp_repo}/{target}/release.txt"
    elif version == 'latest':
        url = f"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{version}-{tag}/release.txt"
    for line in urlopen(url).readlines():
        if 'Pull From: ' in str(line):
            offline = line.decode("utf-8").replace('Pull From: ', '').strip()
            break
    return offline


def same_release_images(version='stable', tag='4.12', pull_secret='openshift_pull.json', path='.'):
    try:
        existing = os.popen(f'{path}/openshift-install version').readlines()[2].split(" ")[2].strip()
    except:
        return False
    offline = offline_image(version=version, tag=tag, pull_secret=pull_secret)
    return offline == existing


def get_installer_minor(installer_version):
    return int(installer_version.split('.')[1])


def get_release_image():
    release_image = os.popen('openshift-install version').readlines()[2].split(" ")[2].strip()
    return release_image


def get_rhcos_openstack_url():
    for line in os.popen('openshift-install version').readlines():
        if 'built from commit' in line:
            commit_id = line.replace('built from commit ', '').strip()
            break
    r = urlopen(f"https://raw.githubusercontent.com/openshift/installer/{commit_id}/data/data/rhcos.json")
    r = str(r.read(), 'utf-8').strip()
    data = json.loads(r)
    return f"{data['baseURI']}{data['images']['openstack']['path']}"


def get_minimal_rhcos():
    for line in os.popen('openshift-install version').readlines():
        if 'built from commit' in line:
            commit_id = line.replace('built from commit ', '').strip()
            break
    r = urlopen(f"https://raw.githubusercontent.com/openshift/installer/{commit_id}/data/data/rhcos.json")
    r = str(r.read(), 'utf-8').strip()
    data = json.loads(r)
    ver = os.path.basename(data['images']['qemu']['path']).replace('-0-qemu.x86_64.qcow2.gz', '').replace('rhcos-', '')
    return int(ver.replace('.', ''))


def get_downstream_installer(devpreview=False, macosx=False, tag=None, debug=False, pull_secret='openshift_pull.json'):
    arch = 'arm64' if os.uname().machine == 'aarch64' else None
    repo = 'ocp-dev-preview' if devpreview else 'ocp'
    if tag is None:
        repo += '/latest'
    elif str(tag).count('.') == 1:
        repo += f'/latest-{tag}'
    else:
        repo += '/%s' % tag.replace('-x86_64', '')
    INSTALLSYSTEM = 'mac' if os.path.exists('/Users') or macosx else 'linux'
    url = f"https://mirror.openshift.com/pub/openshift-v4/clients/{repo}"
    msg = f'Downloading openshift-install from {url}'
    pprint(msg)
    try:
        r = urlopen(f"{url}/release.txt").readlines()
    except:
        error(f"Couldn't open url {url}")
        return 1
    version = None
    for line in r:
        if 'Name' in str(line):
            version = str(line).split(':')[1].strip().replace('\\n', '').replace("'", "")
            break
    if version is None:
        error("Couldn't find version")
        return 1
    if arch == 'arm64':
        cmd = f"curl -s https://mirror.openshift.com/pub/openshift-v4/{arch}/clients/{repo}/"
    else:
        cmd = f"curl -s https://mirror.openshift.com/pub/openshift-v4/clients/{repo}/"
    cmd += f"openshift-install-{INSTALLSYSTEM}-{version}.tar.gz "
    cmd += "| tar zxf - openshift-install"
    cmd += "; chmod 700 openshift-install"
    if debug:
        pprint(cmd)
    return call(cmd, shell=True)


def get_ci_installer(pull_secret, tag=None, macosx=False, upstream=False, debug=False, nightly=False):
    arch = 'arm64' if os.uname().machine == 'aarch64' else None
    base = 'openshift' if not upstream else 'origin'
    if tag is not None and nightly:
        nightly_url = f"https://amd64.ocp.releases.ci.openshift.org/api/v1/releasestream/{tag}.0-0.nightly/latest"
        tag = json.loads(urlopen(nightly_url).read())['pullSpec']
    if tag is None:
        tags = []
        r = urlopen(f"https://{base}-release.ci.openshift.org/graph?format=dot").readlines()
        for line in r:
            tag_match = re.match('.*label="(.*.)", shape=.*', str(line))
            if tag_match is not None:
                tags.append(tag_match.group(1))
        tag = sorted(tags)[-1]
    elif str(tag).startswith('ci-ln'):
        tag = f'registry.build01.ci.openshift.org/{tag}'
    elif '/' not in str(tag):
        if arch == 'arm64':
            tag = f'registry.ci.openshift.org/ocp-arm64/release-arm64:{tag}'
        else:
            basetag = 'ocp' if not upstream else 'origin'
            tag = f'registry.ci.openshift.org/{basetag}/release:{tag}'
    os.environ['OPENSHIFT_RELEASE_IMAGE'] = tag
    msg = f'Downloading openshift-install {tag} in current directory'
    pprint(msg)
    if upstream:
        cmd = f"oc adm release extract --command=openshift-install --to . {tag}"
    else:
        cmd = f"oc adm release extract --registry-config {pull_secret} --command=openshift-install --to . {tag}"
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
    cmd += f"{version}/openshift-install-{INSTALLSYSTEM}-{version}.tar.gz"
    cmd += "| tar zxf - openshift-install"
    cmd += "; chmod 700 openshift-install"
    if debug:
        pprint(cmd)
    return call(cmd, shell=True)


def process_apps(config, clusterdir, apps, overrides):
    if not apps:
        return
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    for app in apps:
        base_data = overrides.copy()
        if isinstance(app, str):
            appname = app
        elif isinstance(app, dict):
            appname = app.get('name')
            if appname is None:
                error(f"Missing name in dict {app}. Skipping")
                continue
            base_data.update(app)
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
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    currentdir = pwd_path(".")
    for script in postscripts:
        script_path = os.path.expanduser(script) if script.startswith('/') else f'{currentdir}/{script}'
        pprint(f"Running script {os.path.basename(script)}")
        call(script_path, shell=True)


def wait_for_ignition(cluster, domain, role='worker'):
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    ignitionfile = "{clusterdir}/ctlplane.ign" if role == 'master' else f"{clusterdir}/worker.ign"
    os.remove(ignitionfile)
    while not os.path.exists(ignitionfile) or os.stat(ignitionfile).st_size == 0:
        try:
            with open(ignitionfile, 'w') as dest:
                req = Request(f"http://api.{cluster}.{domain}:22624/config/{role}")
                req.add_header("Accept", "application/vnd.coreos.ignition+json; version=3.1.0")
                data = urlopen(req).read()
                dest.write(data.decode("utf-8"))
        except:
            pprint(f"Waiting 10s before retrieving {role} ignition data")
            sleep(10)


def handle_baremetal_iso(config, plandir, cluster, overrides, baremetal_hosts=[], iso_pool=None):
    baremetal_iso_overrides = overrides.copy()
    baremetal_iso_overrides['noname'] = True
    baremetal_iso_overrides['workers'] = 1
    baremetal_iso_overrides['role'] = 'worker'
    result = config.plan(cluster, inputfile=f'{plandir}/workers.yml', overrides=baremetal_iso_overrides,
                         onlyassets=True)
    iso_data = result['assets'][0]
    ignitionfile = f'{cluster}-worker'
    with open(ignitionfile, 'w') as f:
        f.write(iso_data)
    config.create_openshift_iso(cluster, overrides=baremetal_iso_overrides, ignitionfile=ignitionfile,
                                podman=True, installer=True, uefi=True)
    os.remove(ignitionfile)
    if baremetal_hosts:
        iso_pool_path = config.k.get_pool_path(iso_pool)
        chmodcmd = f"chmod 666 {iso_pool_path}/{cluster}-worker.iso"
        call(chmodcmd, shell=True)
        pprint("Creating httpd deployment to host iso for baremetal workers")
        timeout = 0
        while True:
            if os.popen('oc -n default get pod -l app=httpd-kcli -o name').read() != "":
                break
            if timeout > 60:
                error("Timeout waiting for httpd deployment to be up")
                sys.exit(1)
            httpdcmd = f"oc create -f {plandir}/httpd.yaml"
            call(httpdcmd, shell=True)
            timeout += 5
            sleep(5)
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


def handle_baremetal_iso_sno(config, plandir, cluster, data, baremetal_hosts=[], iso_pool=None):
    iso_name = f"{cluster}-sno.iso"
    baremetal_web = data.get('baremetal_web', True)
    baremetal_web_dir = data.get('baremetal_web_dir', '/var/www/html')
    baremetal_web_port = data.get('baremetal_web_port', 80)
    iso_pool_path = config.k.get_pool_path(iso_pool)
    if baremetal_web:
        if os.path.exists(f"{baremetal_web_dir}/{iso_name}"):
            call(f"sudo rm {baremetal_web_dir}/{iso_name}", shell=True)
        copy2(f'{iso_pool_path}/{iso_name}', baremetal_web_dir)
        if baremetal_web_dir == '/var/www/html':
            call(f"sudo chown apache.apache {baremetal_web_dir}/{iso_name}", shell=True)
    else:
        call(f"sudo chmod a+r {iso_pool_path}/{iso_name}", shell=True)
    nic = os.popen('ip r | grep default | cut -d" " -f5 | head -1').read().strip()
    ip_cmd = f"ip -o addr show {nic} | awk '{{print $4}}' | cut -d '/' -f 1 | head -1"
    host_ip = os.popen(ip_cmd).read().strip()
    if baremetal_web_port != 80:
        host_ip += f":{baremetal_web_port}"
    return f'http://{host_ip}/{iso_name}'


def scale(config, plandir, cluster, overrides):
    plan = cluster
    client = config.client
    platform = config.type
    k = config.k
    data = {}
    pprint(f"Scaling on client {client}")
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    if os.path.exists(clusterdir):
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
            yaml.safe_dump(data, paramfile)
    image = data.get('image')
    if image is None:
        cluster_image = k.info(f"{cluster}-ctlplane-0").get('image')
        if cluster_image is None:
            error("Missing image...")
            sys.exit(1)
        else:
            pprint(f"Using image {cluster_image}")
            image = cluster_image
    data['image'] = image
    old_baremetal_hosts = installparam.get('baremetal_hosts', [])
    new_baremetal_hosts = overrides.get('baremetal_hosts', [])
    baremetal_hosts = [entry for entry in new_baremetal_hosts if entry not in old_baremetal_hosts]
    if baremetal_hosts:
        if not old_baremetal_hosts:
            iso_pool = data.get('pool') or config.pool
            iso_url = handle_baremetal_iso(config, plandir, cluster, data, baremetal_hosts, iso_pool)
        else:
            svcip_cmd = 'oc get node -o yaml'
            svcip = yaml.safe_load(os.popen(svcip_cmd).read())['items'][0]['status']['addresses'][0]['address']
            svcport_cmd = 'oc get svc -n default httpd-kcli-svc -o yaml'
            svcport = yaml.safe_load(os.popen(svcport_cmd).read())['spec']['ports'][0]['nodePort']
            iso_url = f'http://{svcip}:{svcport}/{cluster}-worker.iso'
        boot_baremetal_hosts(baremetal_hosts, iso_url, overrides=overrides, debug=config.debug)
        overrides['workers'] = overrides.get('workers', 0) - len(new_baremetal_hosts)
    for role in ['ctlplanes', 'workers']:
        overrides = data.copy()
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        if overrides.get(role, 0) <= 0:
            continue
        if platform in virtplatforms:
            os.chdir(os.path.expanduser("~/.kcli"))
            result = config.plan(plan, inputfile=f'{plandir}/{role}.yml', overrides=overrides, threaded=threaded)
        elif platform in cloudplatforms:
            result = config.plan(plan, inputfile=f'{plandir}/cloud_{role}.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            sys.exit(1)


def create(config, plandir, cluster, overrides, dnsconfig=None):
    k = config.k
    log_level = 'debug' if config.debug else 'info'
    client = config.client
    platform = config.type
    arch = k.get_capabilities()['arch'] if platform == 'kvm' else 'x86_64'
    pprint(f"Deploying on client {client}")
    data = {'domain': 'karmalabs.corp',
            'network': 'default',
            'ctlplanes': 3,
            'workers': 0,
            'tag': OPENSHIFT_TAG,
            'ipv6': False,
            'pull_secret': 'openshift_pull.json',
            'version': 'stable',
            'macosx': False,
            'upstream': False,
            'fips': False,
            'apps': [],
            'minimal': False,
            'dualstack': False,
            'kvm_forcestack': False,
            'kvm_openstack': True,
            'ipsec': False,
            'ovn_hostrouting': False,
            'manifests': 'manifests',
            'sno': False,
            'sno_ctlplanes': False,
            'sno_workers': False,
            'sno_wait': False,
            'sno_localhost_fix': False,
            'sno_disable_nics': [],
            'notify': False,
            'async': False,
            'kubevirt_api_service': False,
            'kubevirt_ignore_node_port': False,
            'baremetal_web': True,
            'baremetal_web_dir': '/var/www/html',
            'baremetal_web_port': 80,
            'baremetal_cidr': None,
            'sushy': False,
            'coredns': True,
            'mdns': True,
            'sslip': False,
            'retries': 2}
    data.update(overrides)
    if 'cluster' in overrides:
        clustervalue = overrides.get('cluster')
    elif cluster is not None:
        clustervalue = cluster
    else:
        clustervalue = 'myopenshift'
    retries = data.get('retries')
    data['cluster'] = clustervalue
    domain = data.get('domain')
    original_domain = None
    async_install = data.get('async')
    sslip = data.get('sslip')
    baremetal_hosts = data.get('baremetal_hosts', [])
    notify = data.get('notify')
    postscripts = data.get('postscripts', [])
    pprint(f"Deploying cluster {clustervalue}")
    plan = cluster if cluster is not None else clustervalue
    overrides['kubetype'] = 'openshift'
    apps = overrides.get('apps', [])
    if ('localstorage' in apps or 'ocs' in apps) and 'extra_disks' not in overrides\
            and 'extra_ctlplane_disks' not in overrides and 'extra_worker_disks' not in overrides:
        warning("Storage apps require extra disks to be set")
    overrides['kube'] = data['cluster']
    installparam = overrides.copy()
    installparam['cluster'] = clustervalue
    sno = data.get('sno', False)
    ignore_hosts = data.get('ignore_hosts', False)
    if sno:
        sno_ctlplanes = data.get('sno_ctlplanes')
        sno_workers = data.get('sno_workers')
        sno_wait = data.get('sno_wait')
        sno_disk = data.get('sno_disk')
        if sno_disk is None:
            warning("sno_disk will be discovered")
        ctlplanes = 1
        workers = 0
        data['mdns'] = False
        data['kubetype'] = 'openshift'
        data['kube'] = data['cluster']
        if data.get('network_type', 'OpenShiftSDN') == 'OpenShiftSDN':
            warning("Forcing network_type to OVNKubernetes")
            data['network_type'] = 'OVNKubernetes'
    ctlplanes = data.get('ctlplanes', 1)
    if ctlplanes == 0:
        error("Invalid number of ctlplanes")
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
    ovn_hostrouting = data.get('ovn_hostrouting')
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
    if os.path.exists('coreos-installer'):
        pprint("Removing old coreos-installer")
        os.remove('coreos-installer')
    minimal = data.get('minimal')
    if version not in ['ci', 'dev-preview', 'nightly', 'stable']:
        error(f"Incorrect version {version}")
        sys.exit(1)
    else:
        pprint(f"Using {version} version")
    cluster = data.get('cluster')
    image = data.get('image')
    api_ip = data.get('api_ip')
    cidr = None
    if platform in virtplatforms and not sno and api_ip is None:
        network = data.get('network')
        networkinfo = k.info_network(network)
        if not networkinfo:
            sys.exit(1)
        if platform == 'kvm' and networkinfo['type'] == 'routed':
            cidr = networkinfo['cidr']
            if cidr == 'N/A':
                error("Couldnt gather an api_ip from your specified network")
                sys.exit(1)
            api_index = 2 if ':' in cidr else -3
            api_ip = str(ip_network(cidr)[api_index])
            warning(f"Using {api_ip} as api_ip")
            overrides['api_ip'] = api_ip
        elif platform == 'kubevirt':
            selector = {'kcli/plan': plan, 'kcli/role': 'ctlplane'}
            service_type = "LoadBalancer" if k.access_mode == 'LoadBalancer' else 'NodePort'
            if service_type == 'NodePort':
                kubevirt_api_service_node_port = True
            api_ip = k.create_service(f"{cluster}-api", k.namespace, selector, _type=service_type,
                                      ports=[6443, 22623, 22624, 80, 443], openshift_hack=True)
            if api_ip is None:
                error("Couldnt gather an api_ip from your specified network")
                sys.exit(1)
            else:
                pprint(f"Using api_ip {api_ip}")
                overrides['api_ip'] = api_ip
                overrides['kubevirt_api_service'] = True
                kubevirt_api_service = True
                overrides['mdns'] = False
        else:
            error("You need to define api_ip in your parameters file")
            sys.exit(1)
    if platform in virtplatforms and not sno and ':' in api_ip:
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
    if sslip and platform in virtplatforms:
        original_domain = domain
        domain = '%s.sslip.io' % api_ip.replace('.', '-').replace(':', '-')
        data['domain'] = domain
        pprint(f"Setting domain to {domain}")
        ignore_hosts = False
    public_api_ip = data.get('public_api_ip')
    network = data.get('network')
    ctlplanes = data.get('ctlplanes')
    workers = data.get('workers')
    tag = data.get('tag')
    pull_secret = pwd_path(data.get('pull_secret')) if not upstream else f"{plandir}/fake_pull.json"
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
            warning(f"Using {api_ip} as api_ip")
        if public_api_ip is None:
            public_api_ip = config.k.create_network_port(f"{cluster}-vip", network, ip=api_ip,
                                                         floating=True)['floating']
    if not os.path.exists(pull_secret):
        error(f"Missing pull secret file {pull_secret}")
        sys.exit(1)
    if which('oc') is None:
        get_oc(macosx=macosx)
    pub_key = data.get('pub_key') or get_ssh_pub_key()
    keys = data.get('keys', [])
    if pub_key is None:
        if keys:
            warning("Using first key from your keys array")
            pub_key = keys[0]
        else:
            error("No usable public key found, which is required for the deployment. Create one using ssh-keygen")
            sys.exit(1)
    pub_key = os.path.expanduser(pub_key)
    if pub_key.startswith('ssh-'):
        data['pub_key'] = pub_key
    elif os.path.exists(pub_key):
        data['pub_key'] = open(pub_key).read().strip()
    else:
        error(f"Publickey file {pub_key} not found")
        sys.exit(1)
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        if [v for v in config.k.list() if v.get('plan', 'kvirt') == cluster]:
            error(f"Please remove existing directory {clusterdir} first...")
            sys.exit(1)
        else:
            pprint(f"Removing directory {clusterdir}")
            rmtree(clusterdir)
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    if version == 'ci':
        if '/' not in str(tag):
            if arch in ['aarch64', 'arm64']:
                tag = f'registry.ci.openshift.org/ocp-arm64/release-arm64:{tag}'
            else:
                basetag = 'ocp' if not upstream else 'origin'
                tag = f'registry.ci.openshift.org/{basetag}/release:{tag}'
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = tag
        pprint(f"Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to {tag}")
    os.environ["PATH"] += f":{os.getcwd()}"
    which_openshift = which('openshift-install')
    if which_openshift is None or not same_release_images(version=version, tag=tag, pull_secret=pull_secret,
                                                          path=os.path.dirname(which_openshift)):
        if upstream:
            run = get_upstream_installer(tag=tag)
        elif version in ['ci', 'nightly'] or '/' in str(tag):
            nightly = version == 'nigthly'
            run = get_ci_installer(pull_secret, tag=tag, upstream=upstream, nightly=nightly)
        elif version == 'dev-preview':
            run = get_downstream_installer(devpreview=True, tag=tag, pull_secret=pull_secret)
        else:
            run = get_downstream_installer(tag=tag, pull_secret=pull_secret)
        if run != 0:
            error("Couldn't download openshift-install")
            sys.exit(run)
        pprint("Move downloaded openshift-install somewhere in your PATH if you want to reuse it")
    elif not os.path.exists('openshift-install'):
        warning("Using existing openshift-install found in your PATH")
    else:
        pprint("Reusing matching openshift-install")
    if disconnected_url is not None:
        if disconnected_user is None:
            error("disconnected_user needs to be set")
            sys.exit(1)
        if disconnected_password is None:
            error("disconnected_password needs to be set")
            sys.exit(1)
        if disconnected_url.startswith('http'):
            warning(f"Removing scheme from {disconnected_url}")
            disconnected_url = disconnected_url.replace('http://', '').replace('https://', '')
        if '/' not in str(tag):
            tag = f'{disconnected_url}/{disconnected_prefix}:{tag}'
            os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = tag
        pprint(f"Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to {tag}")
        data['openshift_release_image'] = {tag}
        if 'ca' not in data and 'quay.io' not in disconnected_url:
            pprint(f"Trying to gather registry ca cert from {disconnected_url}")
            cacmd = f"openssl s_client -showcerts -connect {disconnected_url} </dev/null 2>/dev/null|"
            cacmd += "openssl x509 -outform PEM"
            data['ca'] = os.popen(cacmd).read()
    INSTALLER_VERSION = get_installer_version()
    COMMIT_ID = os.popen('openshift-install version').readlines()[1].replace('built from commit', '').strip()
    pprint(f"Using installer version {INSTALLER_VERSION}")
    if sno:
        pass
    elif image is None:
        image_type = 'openstack' if data.get('kvm_openstack') and config.type == 'kvm' else config.type
        region = config.k.region if config.type == 'aws' else None
        if upstream:
            fcos_base = 'stable' if version == 'stable' else 'testing'
            fcos_url = f"https://builds.coreos.fedoraproject.org/streams/{fcos_base}.json"
            image_url = get_latest_fcos(fcos_url, _type=image_type, region=region)
        else:
            try:
                image_url = get_installer_rhcos(_type=image_type, region=region, arch=arch)
            except:
                try:
                    image_url = get_commit_rhcos(COMMIT_ID, _type=image_type, region=region)
                except:
                    error(f"Couldn't gather the {config.type} image associated to commit {COMMIT_ID}")
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
        pprint(f"Using image {image}")
    else:
        pprint(f"Checking if image {image} is available")
        images = [v for v in k.volumes() if image in v]
        if not images:
            error(f"Missing {image}. Indicate correct image in your parameters file...")
            sys.exit(1)
    overrides['image'] = image
    static_networking_ctlplane, static_networking_worker = False, False
    macentries = []
    vmrules = overrides.get('vmrules', [])
    for entry in vmrules:
        if isinstance(entry, dict):
            hostname = list(entry.keys())[0]
            if isinstance(entry[hostname], dict):
                rule = entry[hostname]
                if 'nets' in rule and isinstance(rule['nets'], list):
                    netrule = rule['nets'][0]
                    if isinstance(netrule, dict) and 'ip' in netrule and 'netmask' in netrule:
                        mac, ip = netrule.get('mac'), netrule['ip']
                        netmask, gateway = netrule['netmask'], netrule.get('gateway')
                        nameserver = netrule.get('dns', gateway)
                        if mac is not None and gateway is not None:
                            macentries.append(f"{mac};{hostname};{ip};{netmask};{gateway};{nameserver}")
                        if hostname.startswith(f"{cluster}-ctlplane"):
                            static_networking_ctlplane = True
                        elif hostname.startswith(f"{cluster}-worker"):
                            static_networking_worker = True
    overrides['cluster'] = cluster
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
    if platform in virtplatforms and disconnected_deploy:
        disconnected_vm = f"{data.get('disconnected_reuse_name', cluster)}-disconnected"
        pprint(f"Deploying disconnected vm {disconnected_vm}")
        data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
        disconnected_plan = f"{plan}-reuse" if disconnected_reuse else plan
        disconnected_overrides = data.copy()
        disconnected_overrides['kube'] = f"{cluster}-reuse" if disconnected_reuse else cluster
        disconnected_overrides['openshift_version'] = INSTALLER_VERSION
        disconnected_overrides['disconnected_operators_version'] = '.'.join(INSTALLER_VERSION.split('.')[:-1])
        disconnected_overrides['openshift_release_image'] = get_release_image()
        data['openshift_release_image'] = disconnected_overrides['openshift_release_image']
        x_apps = ['users', 'autolabeller', 'metal3', 'nfs']
        for app in apps:
            if app not in x_apps and app not in disconnected_operators:
                warning(f"Adding app {app} to disconnected_operators array")
                disconnected_operators.append(app)
        disconnected_overrides['disconnected_operators'] = disconnected_operators
        result = config.plan(disconnected_plan, inputfile=f'{plandir}/disconnected.yml',
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
        if disconnected_operators or disconnected_certified_operators or disconnected_community_operators or\
           disconnected_marketplace_operators:
            source = "/root/imageContentSourcePolicy.yaml"
            destination = f"{clusterdir}/imageContentSourcePolicy.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        if disconnected_operators:
            source = "/root/catalogSource-redhat-operator-index.yaml"
            destination = f"{clusterdir}/catalogSource-redhat.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        if disconnected_certified_operators:
            source = "/root/catalogSource-certified-operator-index.yaml"
            destination = f"{clusterdir}/catalogSource-certified.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        if disconnected_community_operators:
            source = "/root/catalogSource-community-operator-index.yaml"
            destination = f"{clusterdir}/catalogSource-community.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        if disconnected_marketplace_operators:
            source = "/root/catalogSource-redhat-marketplace-index.yaml"
            destination = f"{clusterdir}/catalogSource-marketplace.yaml"
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source,
                         destination=destination, tunnel=config.tunnel, tunnelhost=config.tunnelhost,
                         tunnelport=config.tunnelport, tunneluser=config.tunneluser, download=True, insecure=True,
                         vmport=disconnected_vmport)
            os.system(scpcmd)
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = disconnected_version
        pprint(f"Setting OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE to {disconnected_version}")
    if disconnected_url is not None:
        key = f"{disconnected_user}:{disconnected_password}"
        key = str(b64encode(key.encode('utf-8')), 'utf-8')
        auths = {'auths': {disconnected_url: {'auth': key, 'email': 'jhendrix@karmalabs.corp'}}}
        data['pull_secret'] = json.dumps(auths)
    else:
        data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
    # if platform == 'gcp':
    #    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser(config.ini[config.client]['credentials'])
    #    data['region'] = k.region
    installconfig = config.process_inputfile(cluster, f"{plandir}/install-config.yaml", overrides=data)
    with open(f"{clusterdir}/install-config.yaml", 'w') as f:
        f.write(installconfig)
    with open(f"{clusterdir}/install-config.yaml.bck", 'w') as f:
        f.write(installconfig)
    run = call(f'openshift-install --dir={clusterdir} --log-level={log_level} create manifests', shell=True)
    if run != 0:
        error("Leaving environment for debugging purposes")
        error(f"You can delete it with kcli delete kube --yes {cluster}")
        sys.exit(run)
    if minimal:
        warning("Deploying cvo overrides to provide a minimal install")
        with open(f"{plandir}/cvo-overrides.yaml") as f:
            cvo_override = f.read()
        with open(f"{clusterdir}/manifests/cvo-overrides.yaml", "a") as f:
            f.write(cvo_override)
    ntp_server = data.get('ntp_server')
    if ntp_server is not None:
        ntp_data = config.process_inputfile(cluster, f"{plandir}/chrony.conf", overrides={'ntp_server': ntp_server})
        for role in ['master', 'worker']:
            ntp = config.process_inputfile(cluster, f"{plandir}/99-chrony.yaml",
                                           overrides={'role': role, 'ntp_data': ntp_data})
            with open(f"{clusterdir}/manifests/99-chrony-{role}.yaml", 'w') as f:
                f.write(ntp)
    baremetal_cidr = data.get('baremetal_cidr')
    if baremetal_cidr is not None:
        node_ip_hint = f"KUBELET_NODEIP_HINT={baremetal_cidr.split('/')[0]}"
        for role in ['master', 'worker']:
            hint = config.process_inputfile(cluster, f"{plandir}/10-node-ip-hint.yaml",
                                            overrides={'role': role, 'node_ip_hint': node_ip_hint})
            with open(f"{clusterdir}/manifests/99-chrony-{role}.yaml", 'w') as f:
                f.write(hint)
    manifestsdir = data.get('manifests')
    manifestsdir = pwd_path(manifestsdir)
    if os.path.exists(manifestsdir) and os.path.isdir(manifestsdir):
        for f in glob(f"{manifestsdir}/*.y*ml"):
            pprint(f"Injecting manifest {f}")
            copy2(f, f"{clusterdir}/openshift")
    elif isinstance(manifestsdir, list):
        for manifest in manifestsdir:
            f, content = list(manifest.keys())[0], list(manifest.values())[0]
            if not f.endswith('.yml') and not f.endswith('.yaml'):
                warning(f"Skipping manifest {f}")
                continue
            pprint(f"Injecting manifest {f}")
            with open(f'{clusterdir}/openshift/{f}', 'w') as f:
                f.write(content)
    for yamlfile in glob(f"{clusterdir}/*.yaml"):
        if os.stat(yamlfile).st_size == 0:
            warning(f"Skipping empty file {yamlfile}")
        elif 'catalogSource' in yamlfile or 'imageContentSourcePolicy' in yamlfile:
            copy2(yamlfile, f"{clusterdir}/openshift")
    if 'network_type' in data and data['network_type'] == 'Calico':
        calicocmd = "curl https://projectcalico.docs.tigera.io/manifests/ocp.tgz | tar xvz --strip-components=1 "
        calicocmd += f"-C {clusterdir}/manifests"
        call(calicocmd, shell=True)
    if ipsec or ovn_hostrouting:
        ovn_data = config.process_inputfile(cluster, f"{plandir}/99-ovn.yaml",
                                            overrides={'ipsec': ipsec, 'ovn_hostrouting': ovn_hostrouting})
        with open(f"{clusterdir}/openshift/99-ovn.yaml", 'w') as f:
            f.write(ovn_data)
    if workers == 0 or not mdns or kubevirt_api_service:
        copy2(f'{plandir}/cluster-scheduler-02-config.yml', f"{clusterdir}/manifests")
    if disconnected_operators:
        if os.path.exists(f'{clusterdir}/imageContentSourcePolicy.yaml'):
            copy2(f'{clusterdir}/imageContentSourcePolicy.yaml', f"{clusterdir}/openshift")
        if os.path.exists(f'{clusterdir}/catalogsource.yaml'):
            copy2(f'{clusterdir}/catalogsource.yaml', f"{clusterdir}/openshift")
        copy2(f'{plandir}/99-operatorhub.yaml', f"{clusterdir}/openshift")
    if 'sslip' in domain:
        ingress_sslip_data = config.process_inputfile(cluster, f"{plandir}/cluster-ingress-02-config.yml",
                                                      overrides={'cluster': cluster, 'domain': domain})
        with open(f"{clusterdir}/manifests/cluster-ingress-02-config.yml", 'w') as f:
            f.write(ingress_sslip_data)
    cron_overrides = {'registry': disconnected_url or 'quay.io'}
    cron_overrides['version'] = 'v1beta1' if get_installer_minor(INSTALLER_VERSION) < 8 else 'v1'
    autoapproverdata = config.process_inputfile(cluster, f"{plandir}/autoapprovercron.yml", overrides=cron_overrides)
    with open(f"{clusterdir}/autoapprovercron.yml", 'w') as f:
        f.write(autoapproverdata)
    for f in glob(f"{plandir}/customisation/*.yaml"):
        if '99-ingress-controller.yaml' in f:
            ingressrole = 'master' if workers == 0 or not mdns or kubevirt_api_service else 'worker'
            replicas = ctlplanes if workers == 0 or not mdns or kubevirt_api_service else workers
            if platform in virtplatforms and sslip and ingress_ip is None:
                replicas = ctlplanes
                ingressrole = 'master'
                warning("Forcing router pods on ctlplanes since sslip is set and api_ip will be used for ingress")
                copy2(f'{plandir}/cluster-scheduler-02-config.yml', f"{clusterdir}/manifests")
            ingressconfig = config.process_inputfile(cluster, f, overrides={'replicas': replicas, 'role': ingressrole,
                                                                            'cluster': cluster, 'domain': domain})
            with open(f"{clusterdir}/openshift/99-ingress-controller.yaml", 'w') as _f:
                _f.write(ingressconfig)
            continue
        if '99-autoapprovercron-cronjob.yaml' in f:
            crondata = config.process_inputfile(cluster, f, overrides=cron_overrides)
            with open(f"{clusterdir}/openshift/99-autoapprovercron-cronjob.yaml", 'w') as _f:
                _f.write(crondata)
            continue
        if '99-monitoring.yaml' in f:
            monitoring_retention = data['monitoring_retention']
            monitoringfile = config.process_inputfile(cluster, f, overrides={'retention': monitoring_retention})
            with open(f"{clusterdir}/openshift/99-monitoring.yaml", 'w') as _f:
                _f.write(monitoringfile)
            continue
        copy2(f, f"{clusterdir}/openshift")
    if async_install:
        registry = disconnected_url or 'quay.io'
        config.import_in_kube(network=network, dest=f"{clusterdir}/openshift", secure=True)
        deletionfile = f"{plandir}/99-bootstrap-deletion.yaml"
        deletionfile = config.process_inputfile(cluster, deletionfile, overrides={'cluster': cluster,
                                                                                  'registry': registry,
                                                                                  'client': config.client})
        with open(f"{clusterdir}/openshift/99-bootstrap-deletion.yaml", 'w') as _f:
            _f.write(deletionfile)
        if not sushy:
            deletionfile2 = f"{plandir}/99-bootstrap-deletion-2.yaml"
            deletionfile2 = config.process_inputfile(cluster, deletionfile2, overrides={'registry': registry})
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
                                                                                  'cmds': notifycmds,
                                                                                  'mailcontent': mailcontent})
            with open(f"{clusterdir}/openshift/99-notifications.yaml", 'w') as _f:
                _f.write(notifyfile)
    if apps and (async_install or sno):
        registry = disconnected_url or 'quay.io'
        final_apps = []
        for a in apps:
            if isinstance(a, str) and a not in ['users', 'autolabellers', 'metal3', 'nfs']:
                final_apps.append(a)
            elif isinstance(a, dict) and 'name' in a:
                final_apps.append(a['name'])
            else:
                error(f"Invalid app {a}. Skipping")
        appsfile = f"{plandir}/99-apps.yaml"
        appsfile = config.process_inputfile(cluster, appsfile, overrides={'registry': registry, 'apps': final_apps})
        with open(f"{clusterdir}/openshift/99-apps.yaml", 'w') as _f:
            _f.write(appsfile)
        appdir = f"{plandir}/apps"
        apps_namespace = {'advanced-cluster-management': 'open-cluster-management',
                          'multicluster-engine': 'multicluster-engine', 'kubevirt-hyperconverged': 'openshift-cnv',
                          'local-storage-operator': 'openshift-local-storage',
                          'ocs-operator': 'openshift-storage', 'odf-lvm-operator': 'openshift-storage',
                          'odf-operator': 'openshift-storage', 'metallb-operator': 'openshift-operators',
                          'autolabeller': 'autorules'}
        apps = [a for a in apps if a not in ['users', 'metal3', 'nfs']]
        for appname in apps:
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
                with open(f"{clusterdir}/openshift/99-apps-{appname}.yaml", 'w') as g:
                    g.write(rendered)
    if metal3:
        copy2(f"{plandir}/99-metal3-provisioning.yaml", f"{clusterdir}/openshift")
        copy2(f"{plandir}/99-metal3-fake-machine.yaml", f"{clusterdir}/openshift")
    if sushy:
        config.import_in_kube(network=network, dest=f"{clusterdir}/openshift", secure=True)
        copy2(f"{plandir}/sushy/deployment.yaml", f"{clusterdir}/openshift/99-sushy-deployment.yaml")
        copy2(f"{plandir}/sushy/service.yaml", f"{clusterdir}/openshift/99-sushy-service.yaml")
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
            localctlplane = config.process_inputfile(cluster, f"{plandir}/99-localhost-fix.yaml",
                                                     overrides={'role': 'master'})
            with open(f"{clusterdir}/openshift/99-localhost-fix-ctlplane.yaml", 'w') as _f:
                _f.write(localctlplane)
            localworker = config.process_inputfile(cluster, f"{plandir}/99-localhost-fix.yaml",
                                                   overrides={'role': 'worker'})
            with open(f"{clusterdir}/openshift/99-localhost-fix-worker.yaml", 'w') as _f:
                _f.write(localworker)
        if sno_ctlplanes:
            ingress = config.process_inputfile(cluster, f"{plandir}/customisation/99-ingress-controller.yaml",
                                               overrides={'role': 'master', 'cluster': cluster, 'domain': domain,
                                                          'replicas': 3})
            with open(f"{clusterdir}/openshift/99-ingress-controller.yaml", 'w') as _f:
                _f.write(ingress)
        pprint("Generating bootstrap-in-place ignition")
        run = call(f'openshift-install --dir={clusterdir} --log-level={log_level} create single-node-ignition-config',
                   shell=True)
        if run != 0:
            error("Hit issue.Leaving")
            sys.exit(run)
        move(f"{clusterdir}/bootstrap-in-place-for-live-iso.ign", f"./{sno_name}.ign")
        with open("iso.ign", 'w') as f:
            iso_overrides = {}
            extra_args = overrides.get('extra_args')
            if sno_disk is None or extra_args is not None:
                _files = [{"path": "/root/sno-finish.service", "origin": f"{plandir}/sno-finish.service"},
                          {"path": "/usr/local/bin/sno-finish.sh", "origin": f"{plandir}/sno-finish.sh", "mode": 700}]
                iso_overrides['files'] = _files
            iso_overrides.update(data)
            result = config.create_vm(sno_name, 'rhcos46', overrides=iso_overrides, onlyassets=True)
            pprint("Writing iso.ign to current dir")
            f.write(result['data'])
        if config.type == 'fake':
            pprint("Storing generated iso in current dir")
            generate_rhcos_iso(k, f"{cluster}-sno", 'default', installer=True, extra_args=extra_args)
        elif config.type not in ['kvm', 'kubevirt']:
            pprint(f"Additional workflow not available on {config.type}")
            pprint("Embed iso.ign in rhcos live iso")
            sys.exit(0)
        else:
            iso_pool = data['pool'] or config.pool
            pprint(f"Storing generated iso in pool {iso_pool}")
            generate_rhcos_iso(k, f"{cluster}-sno", iso_pool, installer=True, extra_args=extra_args)
        if sno_ctlplanes:
            if api_ip is None:
                warning("sno ctlplanes requires api vip to be defined. Skipping")
            else:
                ctlplane_overrides = overrides.copy()
                ctlplane_overrides['role'] = 'master'
                ctlplane_overrides['image'] = 'rhcos410'
                config.create_openshift_iso(cluster, overrides=ctlplane_overrides, installer=True)
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
        if baremetal_hosts:
            iso_pool = data['pool'] or config.pool
            iso_url = handle_baremetal_iso_sno(config, plandir, cluster, data, baremetal_hosts, iso_pool)
            boot_baremetal_hosts(baremetal_hosts, iso_url, overrides=overrides, debug=config.debug)
        if sno_wait:
            installcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for install-complete'
            installcommand = ' || '.join([installcommand for x in range(retries)])
            pprint("Launching install-complete step. It will be retried extra times in case of timeouts")
            run = call(installcommand, shell=True)
            if run != 0:
                error("Leaving environment for debugging purposes")
                error(f"You can delete it with kcli delete cluster --yes {cluster}")
                sys.exit(run)
        else:
            c = os.environ['KUBECONFIG']
            kubepassword = open(f"{clusterdir}/auth/kubeadmin-password").read()
            console = f"https://console-openshift-console.apps.{cluster}.{domain}"
            info2(f"To access the cluster as the system:admin user when running 'oc', run export KUBECONFIG={c}")
            info2(f"Access the Openshift web-console here: {console}")
            info2(f"Login to the console with user: kubeadmin, password: {kubepassword}")
            pprint(f"Plug {cluster}-sno.iso to your SNO node to complete the installation")
            if sno_ctlplanes:
                pprint(f"Plug {cluster}-master.iso to get additional ctlplanes")
            if sno_workers:
                pprint(f"Plug {cluster}-worker.iso to get additional workers")
        backup_paramfile(installparam, clusterdir, cluster, plan, image, dnsconfig)
        sys.exit(0)
    run = call(f'openshift-install --dir={clusterdir} --log-level={log_level} create ignition-configs', shell=True)
    if run != 0:
        error("Hit issues when generating ignition-config files")
        error("Leaving environment for debugging purposes")
        error(f"You can delete it with kcli delete kube --yes {cluster}")
        sys.exit(run)
    copy2(f"{clusterdir}/master.ign", f"{clusterdir}/ctlplane.ign")
    move(f"{clusterdir}/master.ign", f"{clusterdir}/master.ign.ori")
    copy2(f"{clusterdir}/worker.ign", f"{clusterdir}/worker.ign.ori")
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
        sedcmd = f'sed -i "s@api-int.{cluster}.{domain}@{api_ip}@" {clusterdir}/ctlplane.ign {clusterdir}/worker.ign'
        call(sedcmd, shell=True)
        sedcmd = f'sed -i "s@https://{api_ip}:22623/config@http://{api_ip}:22624/config@"'
        sedcmd += f' {clusterdir}/ctlplane.ign {clusterdir}/worker.ign'
        call(sedcmd, shell=True)
        if ipv6:
            sedcmd = f'sed -i "s@{api_ip}@[{api_ip}]@" {clusterdir}/ctlplane.ign {clusterdir}/worker.ign'
            call(sedcmd, shell=True)
    if platform in cloudplatforms + ['openstack']:
        bucket = "%s-%s" % (cluster, domain.replace('.', '-'))
        if bucket not in config.k.list_buckets():
            config.k.create_bucket(bucket)
        config.k.upload_to_bucket(bucket, f"{clusterdir}/bootstrap.ign", public=True)
        bucket_url = config.k.public_bucketfile_url(bucket, "bootstrap.ign")
        if platform == 'openstack':
            ori_url = f"http://{api_ip}:22624"
        else:
            ori_url = f"https://api-int.{cluster}.{domain}:22623"
        sedcmd = f'sed "s@{ori_url}/config/master@{bucket_url}@" '
        sedcmd += f'{clusterdir}/ctlplane.ign > {clusterdir}/bootstrap.ign'
        call(sedcmd, shell=True)
    backup_paramfile(installparam, clusterdir, cluster, plan, image, dnsconfig)
    if platform in virtplatforms:
        if platform == 'vsphere':
            pprint(f"Creating vm folder /vm/{cluster}")
            k.create_vm_folder(cluster)
        pprint("Deploying bootstrap")
        result = config.plan(plan, inputfile=f'{plandir}/bootstrap.yml', overrides=overrides)
        if result['result'] != 'success':
            sys.exit(1)
        if static_networking_ctlplane:
            wait_for_ignition(cluster, domain, role='master')
        pprint("Deploying ctlplanes")
        threaded = data.get('threaded', False) or data.get('ctlplanes_threaded', False)
        if baremetal_hosts:
            overrides['workers'] = overrides['workers'] - len(baremetal_hosts)
        result = config.plan(plan, inputfile=f'{plandir}/ctlplanes.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            sys.exit(1)
        todelete = [f"{cluster}-bootstrap"]
        if dnsconfig is not None:
            dns_overrides = {'api_ip': api_ip, 'ingress_ip': ingress_ip, 'cluster': cluster, 'domain': domain}
            result = dnsconfig.plan(plan, inputfile=f'{plandir}/cloud_dns.yml', overrides=dns_overrides)
            if result['result'] != 'success':
                sys.exit(1)
    else:
        pprint("Deploying bootstrap")
        result = config.plan(plan, inputfile=f'{plandir}/cloud_bootstrap.yml', overrides=overrides)
        if result['result'] != 'success':
            sys.exit(1)
        sedcmd = 'sed -i "s@https://api-int.%s.%s:22623/config@http://api-int.%s.%s:22624/config@"' % (cluster, domain,
                                                                                                       cluster, domain)
        sedcmd += f' {clusterdir}/ctlplane.ign {clusterdir}/worker.ign'
        call(sedcmd, shell=True)
        if platform == 'ibm':
            while api_ip is None:
                api_ip = k.info(f"{cluster}-bootstrap").get('private_ip')
                pprint("Gathering bootstrap private ip")
                sleep(10)
            sedcmd = f'sed -i "s@api-int.{cluster}.{domain}@{api_ip}@" {clusterdir}/ctlplane.ign'
            call(sedcmd, shell=True)
        pprint("Deploying ctlplanes")
        threaded = data.get('threaded', False) or data.get('ctlplanes_threaded', False)
        result = config.plan(plan, inputfile=f'{plandir}/cloud_ctlplanes.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            sys.exit(1)
        if platform == 'ibm':
            first_ctlplane_ip = None
            while first_ctlplane_ip is None:
                first_ctlplane_ip = k.info(f"{cluster}-ctlplane-0").get('private_ip')
                pprint("Gathering first ctlplane bootstrap ip")
                sleep(10)
            sedcmd = f'sed -i "s@api-int.{cluster}.{domain}@{first_ctlplane_ip}@" {clusterdir}/worker.ign'
            call(sedcmd, shell=True)
        result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_api.yml', overrides=overrides)
        if result['result'] != 'success':
            sys.exit(1)
        lb_overrides = {'cluster': cluster, 'domain': domain, 'members': ctlplanes, 'role': 'master'}
        if 'dnsclient' in overrides:
            lb_overrides['dnsclient'] = overrides['dnsclient']
        if workers == 0:
            result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_apps.yml', overrides=lb_overrides)
            if result['result'] != 'success':
                sys.exit(1)
        todelete = [f"{cluster}-bootstrap"]
    if not kubevirt_ignore_node_port and kubevirt_api_service and kubevirt_api_service_node_port:
        nodeport = k.get_node_ports(f'{cluster}-api', k.namespace)[6443]
        sedcmd = f'sed -i "s@:6443@:{nodeport}@" {clusterdir}/auth/kubeconfig'
        call(sedcmd, shell=True)
        while True:
            nodehost = k.info(f"{cluster}-bootstrap").get('host')
            if nodehost is not None:
                break
            else:
                pprint("Waiting 5s for bootstrap vm to be up")
                sleep(5)
        if 'KUBECONFIG' in os.environ or 'kubeconfig' in config.ini[config.client]:
            kubeconfig = config.ini[config.client].get('kubeconfig') or os.environ['KUBECONFIG']
            hostip_cmd = f'KUBECONFIG={kubeconfig} oc get node {nodehost} -o yaml'
            hostip = yaml.safe_load(os.popen(hostip_cmd).read())['status']['addresses'][0]['address']
            update_etc_hosts(cluster, domain, hostip)
    if not async_install:
        bootstrapcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for bootstrap-complete'
        bootstrapcommand = ' || '.join([bootstrapcommand for x in range(retries)])
        run = call(bootstrapcommand, shell=True)
        if run != 0:
            error("Leaving environment for debugging purposes")
            error(f"You can delete it with kcli delete cluster --yes {cluster}")
            sys.exit(run)
    if workers > 0:
        if static_networking_worker:
            wait_for_ignition(cluster, domain, role='worker')
        pprint("Deploying workers")
        if 'name' in overrides:
            del overrides['name']
        if platform in virtplatforms:
            if baremetal_hosts:
                iso_pool = data.get('pool') or config.pool
                iso_url = handle_baremetal_iso(config, plandir, cluster, data, baremetal_hosts, iso_pool)
                boot_baremetal_hosts(baremetal_hosts, iso_url, overrides=overrides, debug=config.debug)
            if overrides['workers'] > 0:
                threaded = data.get('threaded', False) or data.get('workers_threaded', False)
                result = config.plan(plan, inputfile=f'{plandir}/workers.yml', overrides=overrides, threaded=threaded)
                if result['result'] != 'success':
                    sys.exit(1)
        elif platform in cloudplatforms:
            result = config.plan(plan, inputfile=f'{plandir}/cloud_workers.yml', overrides=overrides)
            if result['result'] != 'success':
                sys.exit(1)
            lb_overrides['role'] = 'worker'
            lb_overrides['members'] = workers
            result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_apps.yml', overrides=lb_overrides)
            if result['result'] != 'success':
                sys.exit(1)
    if minimal or async_install:
        kubeconf = os.environ['KUBECONFIG']
        kubepassword = open(f"{clusterdir}/auth/kubeadmin-password").read()
        if minimal:
            success("Minimal Cluster ready to be used")
            success("INFO Install Complete")
        if async_install:
            success("Async Cluster created")
            info2("You will need to wait before it is fully available")
        info2(f"To access the cluster as the system:admin user when running 'oc', run export KUBECONFIG={kubeconf}")
        info2(f"Access the Openshift web-console here: https://console-openshift-console.apps.{cluster}.{domain}")
        info2(f"Login to the console with user: kubeadmin, password: {kubepassword}")
        if async_install:
            return
    else:
        installcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for install-complete'
        installcommand += f" || {installcommand}"
        pprint("Launching install-complete step. It will be retried one extra time in case of timeouts")
        run = call(installcommand, shell=True)
        if run != 0:
            error("Leaving environment for debugging purposes")
            error(f"You can delete it with kcli delete cluster --yes {cluster}")
            sys.exit(run)
    for vm in todelete:
        pprint(f"Deleting {vm}")
        k.delete(vm)
        if dnsconfig is not None:
            pprint(f"Deleting Dns entry for {vm} in {domain}")
            z = dnsconfig.k
            z.delete_dns(vm, domain)
    if sushy:
        call("oc expose -n kcli-infra svc/sushy", shell=True)
    if platform in cloudplatforms:
        bucket = "%s-%s" % (cluster, domain.replace('.', '-'))
        config.k.delete_bucket(bucket)
    if original_domain is not None:
        overrides['domain'] = original_domain
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    process_apps(config, clusterdir, apps, overrides)
    process_postscripts(clusterdir, postscripts)
    if platform in cloudplatforms and ctlplanes == 1 and workers == 0 and data.get('sno_cloud_remove_lb', True):
        pprint("Removing loadbalancers as there is a single ctlplane")
        k.delete_loadbalancer(f"api.{cluster}")
        k.delete_loadbalancer(f"apps.{cluster}")
        api_ip = k.info(f"{cluster}-ctlplane-0").get('ip')
        k.delete_dns(f'api.{cluster}', domain=domain)
        k.reserve_dns(f'api.{cluster}', domain=domain, ip=api_ip)
        k.delete_dns(f'apps.{cluster}', domain=domain)
        k.reserve_dns(f'apps.{cluster}', domain=domain, ip=api_ip, alias=['*'])
        if platform == 'ibm':
            k._add_sno_security_group(cluster)
