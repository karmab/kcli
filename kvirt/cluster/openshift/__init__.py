from base64 import b64encode, b64decode
from fnmatch import fnmatch
from glob import glob
from ipaddress import ip_address, ip_network
import json
from kvirt.common import error, pprint, success, warning, info2, fix_typos
from kvirt.common import get_oc, pwd_path, get_oc_mirror, patch_ingress_controller_wildcard
from kvirt.common import generate_rhcos_iso, olm_app
from kvirt.common import get_installer_rhcos, wait_cloud_dns, delete_lastvm, detect_openshift_version
from kvirt.common import ssh, scp, _ssh_credentials, get_ssh_pub_key
from kvirt.common import start_baremetal_hosts_with_iso, update_baremetal_hosts, get_new_vip, process_postscripts
from kvirt.defaults import LOCAL_OPENSHIFT_APPS, OPENSHIFT_TAG
import os
import re
from random import choice
from shutil import copy2, move, rmtree, which
from socket import gethostbyname, create_connection
from string import ascii_letters, digits
from subprocess import call
import sys
from tempfile import TemporaryDirectory
from time import sleep
from urllib.request import urlopen, Request
from yaml import safe_dump, safe_load, safe_load_all, safe_dump_all


virt_providers = ['kvm', 'kubevirt', 'openstack', 'ovirt', 'proxmox', 'vsphere']
cloud_providers = ['aws', 'azure', 'gcp', 'ibm', 'hcloud']


def patch_oc_mirror(clusterdir):
    for _fic in [f'{clusterdir}/idms-oc-mirror.yaml', f'{clusterdir}/itms-oc-mirror.yaml']:
        if not os.path.exists(_fic):
            continue
        entries = []
        for document in safe_load_all(open(_fic)):
            if 'release' in document['metadata']['name']:
                continue
            if os.path.basename(_fic) == 'idms-oc-mirror.yaml':
                document = json.loads(json.dumps(document).replace('quay.io/prega/test', 'registry.redhat.io'))
            entries.append(document)
        with open(_fic, 'w') as f:
            safe_dump_all(entries, f, default_flow_style=False, encoding='utf-8', allow_unicode=True)


def aws_credentials(config):
    if os.path.exists(os.path.expanduser('~/.aws/credentials')):
        return
    aws_dir = f'{os.environ["HOME"]}/.aws'
    if not os.path.exists(aws_dir):
        os.mkdir(aws_dir)
    access_key_id = config.options.get('access_key_id')
    access_key_secret = config.options.get('access_key_secret')
    session_token = config.options.get('session_token')
    with open(f"{aws_dir}/credentials", "w") as f:
        data = """[default]
aws_access_key_id={access_key_id}
aws_secret_access_key={access_key_secret}""".format(access_key_id=access_key_id, access_key_secret=access_key_secret)
        f.write(data)
        if session_token is not None:
            f.write(f"aws_session_token={session_token}")


def azure_credentials(config):
    if os.path.exists(os.path.expanduser('~/.azure/osServicePrincipal.json')):
        return
    azure_dir = f'{os.environ["HOME"]}/.azure'
    if not os.path.exists(azure_dir):
        os.mkdir(azure_dir)
    data = {'subscriptionId': config.k.subscription_id,
            'clientId': config.k.app_id,
            "tenantId": config.k.tenant_id,
            'clientSecret': config.k.secret}
    with open(f'{azure_dir}/osServicePrincipal.json', 'w') as dest_file:
        json.dump(data, dest_file)


def update_pull_secret(pull_secret, registry, user, password):
    pull_secret = os.path.expanduser(pull_secret)
    data = json.load(open(pull_secret))
    auths = data['auths']
    if registry not in auths or b64decode(auths[registry]['auth']).decode("utf-8").split(':') != [user, password]:
        pprint(f"Updating your pull secret with entry for {registry}")
        key = f"{user}:{password}"
        key = str(b64encode(key.encode('utf-8')), 'utf-8')
        data['auths'][registry] = {'auth': key, 'email': 'jhendrix@karmalabs.corp'}
        with open(pull_secret, 'w') as p:
            json.dump(data, p)


def update_registry(config, plandir, cluster, data):
    disconnected_url = data['disconnected_url']
    pull_secret_path = data['pull_secret_path']
    version = data['version']
    tag = data.get('ori_tag') or data.get('tag')
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}") if cluster is not None else '.'
    if data.get('ca') is None:
        pprint(f"Trying to gather registry ca cert from {disconnected_url}")
        cacmd = f"openssl s_client -showcerts -connect {disconnected_url} </dev/null 2>/dev/null|"
        cacmd += "awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/'"
        data['ca'] = os.popen(cacmd).read()
    with open(f'{clusterdir}/ca.crt', 'w') as f:
        f.write(data['ca'])
    call(f'sudo cp {clusterdir}/ca.crt /etc/pki/ca-trust/source/anchors ; sudo update-ca-trust extract',
         shell=True)
    if which('oc-mirror') is None:
        get_oc_mirror(version=version, tag=OPENSHIFT_TAG)
    else:
        warning("Using oc-mirror from your PATH")
    mirror_data = data.copy()
    mirror_data['tag'] = tag
    extra_images = data.get('disconnected_extra_images', [])
    mirror_data['extra_images'] = extra_images
    mirror_data['OPENSHIFT_TAG'] = OPENSHIFT_TAG
    mirrorconf = config.process_inputfile(cluster, f"{plandir}/disconnected/mirror-config.yaml", overrides=mirror_data)
    with open(f"{clusterdir}/mirror-config.yaml", 'w') as f:
        f.write(mirrorconf)
    dockerdir = os.path.expanduser('~/.docker')
    if not os.path.isdir(dockerdir):
        os.mkdir(dockerdir)
    copy2(pull_secret_path, f"{dockerdir}/config.json")
    mirrordir = data.get('mirror_dir') or clusterdir
    olmcmd = f"oc-mirror --v2 --workspace file://{mirrordir} --config {clusterdir}/mirror-config.yaml "
    olmcmd += f" docker://{disconnected_url}"
    pprint(f"Running {olmcmd}")
    code = call(olmcmd, shell=True)
    if code != 0:
        error("Hit issue when running oc-mirror")
        sys.exit(1)
    resourcesdir = f"{mirrordir}/working-dir/cluster-resources"
    for manifest in glob(f"{resourcesdir}/cs-*.yaml") + glob(f"{resourcesdir}/*oc-mirror*.yaml"):
        copy2(manifest, clusterdir)
    patch_oc_mirror(clusterdir)


def create_ignition_files(config, plandir, cluster, domain, api_ip=None, bucket_url=None, ignition_version=None):
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    ignition_overrides = {'api_ip': api_ip, 'cluster': cluster, 'domain': domain, 'role': 'master'}
    ctlplane_ignition = config.process_inputfile(cluster, f"{plandir}/ignition.j2", overrides=ignition_overrides)
    with open(f"{clusterdir}/ctlplane.ign", 'w') as f:
        f.write(ctlplane_ignition)
    del ignition_overrides['role']
    worker_ignition = config.process_inputfile(cluster, f"{plandir}/ignition.j2", overrides=ignition_overrides)
    with open(f"{clusterdir}/worker.ign", 'w') as f:
        f.write(worker_ignition)
    if bucket_url is not None:
        if config.type == 'openstack':
            ignition_overrides['ca_file'] = config.k.ca_file
        ignition_overrides['bucket_url'] = bucket_url
        bootstrap_ignition = config.process_inputfile(cluster, f"{plandir}/ignition.j2", overrides=ignition_overrides)
        with open(f"{clusterdir}/bootstrap.ign", 'w') as f:
            f.write(bootstrap_ignition)


def backup_paramfile(client, installparam, clusterdir, cluster, plan, image, dnsconfig):
    with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
        installparam['client'] = client
        installparam['cluster'] = cluster
        installparam['plan'] = plan
        installparam['image'] = image
        if dnsconfig is not None:
            installparam['dnsclient'] = dnsconfig.client
        safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)


def update_openshift_etc_hosts(cluster, domain, host_ip, ingress_ip=None):
    if not os.path.exists("/i_am_a_container"):
        hosts = open("/etc/hosts").readlines()
        wronglines = [e for e in hosts if not e.startswith('#') and (f"api.{cluster}.{domain}" in e and
                      host_ip not in e) or (host_ip in e and 'api.' in e and f"{cluster}.{domain}" not in e)]
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


def has_internet():
    try:
        create_connection(('mirror.openshift.com', 443), 5)
        return True
    except Exception:
        return False


def offline_image(version='stable', tag=OPENSHIFT_TAG, pull_secret='openshift_pull.json'):
    tag = str(tag).split(':')[-1]
    for arch in ['x86_64', 'amd64', 'arm64', 'ppc64le', 's390x', 'x86_64']:
        tag.replace(f'-{arch}', '')
    offline = 'xxx'
    if version in ['ci', 'nightly']:
        if version == "nightly" and str(tag).count('.') == 1:
            nightly_url = f"https://amd64.ocp.releases.ci.openshift.org/api/v1/releasestream/{tag}.0-0.nightly/latest"
            tag = json.loads(urlopen(nightly_url).read())['name']
        cmd = f"oc adm release info registry.ci.openshift.org/ocp/release:{tag} -a {pull_secret}"
        for line in os.popen(cmd).readlines():
            if 'Pull From: ' in str(line):
                offline = line.replace('Pull From: ', '').strip()
                break
        return offline
    ocp_repo = 'ocp-dev-preview' if version == 'candidate' else 'ocp'
    if version in ['candidate', 'stable']:
        baselink = 'stable' if version == 'stable' else 'latest'
        target = tag if len(str(tag).split('.')) > 2 else f'{baselink}-{tag}'
        url = f"https://mirror.openshift.com/pub/openshift-v4/clients/{ocp_repo}/{target}/release.txt"
    elif version == 'latest':
        url = f"https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{version}-{tag}/release.txt"
    else:
        error(f"Invalid version {version}")
        return offline
    try:
        lines = urlopen(url).readlines()
        for line in lines:
            if 'Pull From: ' in str(line):
                offline = line.decode("utf-8").replace('Pull From: ', '').strip()
                break
    except Exception as e:
        error(f"Hit {e} when opening {url}")
    return offline


def same_release_images(version='stable', tag=OPENSHIFT_TAG, pull_secret='openshift_pull.json', path='.'):
    if not os.path.exists(f'{path}/openshift-install'):
        return False
    try:
        existing = os.popen(f'{path}/openshift-install version').readlines()[2].split(" ")[2].strip()
    except:
        return False
    if os.path.abspath(path) != os.getcwd() and not existing.startswith('quay.io/openshift-release-dev/ocp-release')\
       and not existing.startswith('registry.ci.openshift.org/ocp/release'):
        warning("Assuming your disconnected openshift-install has the correct version")
        return True
    try:
        offline = offline_image(version=version, tag=tag, pull_secret=pull_secret)
        return offline == existing
    except:
        return False


def get_installer_minor(installer_version):
    if '.' not in installer_version:
        return 100
    return int(installer_version.split('.')[1])


def get_release_image():
    release_image = os.popen('openshift-install version').readlines()[2].split(" ")[2].strip()
    return release_image


def get_downstream_installer(version='stable', macosx=False, tag=None, debug=False, pull_secret='openshift_pull.json',
                             baremetal=False):
    if baremetal:
        offline = offline_image(version=version, tag=tag, pull_secret=pull_secret)
        binary = 'openshift-baremetal-install' if get_installer_minor(tag) < 16 else 'openshift-install'
        cmd = f"oc adm release extract --registry-config {pull_secret} --command={binary} --to . {offline}"
        if get_installer_minor(tag) >= 16:
            cmd += '; mv openshift-install openshift-baremetal-install'
        cmd += "; chmod 700 openshift-baremetal-install"
        if debug:
            pprint(cmd)
        return call(cmd, shell=True)
    arch_map = {'aarch64': 'arm64', 's390x': 's390x'}
    arch = os.uname().machine
    arch = arch_map.get(arch, arch)
    repo = 'ocp-dev-preview' if version == 'candidate' else 'ocp'
    if tag is None:
        repo += '/{version}'
    elif str(tag).count('.') == 1:
        baselink = version if version in ['stable', 'candidate'] else 'latest'
        repo += f'/{baselink}-{tag}'
    else:
        repo += f"/{tag.replace('-x86_64', '')}"
    INSTALLSYSTEM = 'mac' if os.path.exists('/Users') or macosx else 'linux'
    url = f"https://mirror.openshift.com/pub/openshift-v4/{arch}/clients/{repo}"
    pprint(f'Downloading openshift-install from {url}')
    try:
        r = urlopen(f"{url}/release.txt").readlines()
    except:
        error(f"Couldn't open url {url}/release.txt")
        return 1
    version = None
    for line in r:
        if 'Name' in str(line):
            version = str(line).split(':')[1].strip().replace('\\n', '').replace("'", "")
            break
    if version is None:
        error("Couldn't find version")
        return 1
    cmd = f"curl -Ls https://mirror.openshift.com/pub/openshift-v4/{arch}/clients/{repo}/"
    cmd += f"openshift-install-{INSTALLSYSTEM}-{version}.tar.gz "
    cmd += "| tar zxf - openshift-install"
    cmd += "; chmod 700 openshift-install"
    if debug:
        pprint(cmd)
    return call(cmd, shell=True)


def get_okd_installer(tag, version='stable', debug=False):
    if version == 'stable' and str(tag).count('.') == 1:
        tag = f'quay.io/okd/scos-release:{tag}.0-okd-scos.1'
    elif 'quay.io' not in str(tag) and 'registry.ci.openshift.org' not in str(tag):
        if version == 'candidate':
            url = "https://amd64.origin.releases.ci.openshift.org/api/v1/releasestream/4-scos-next/latest"
        elif version in ['ci', 'nightly']:
            url = f"https://amd64.origin.releases.ci.openshift.org/api/v1/releasestream/{tag}.0-0.okd-scos/latest"
        else:
            url = "https://amd64.origin.releases.ci.openshift.org/api/v1/releasestream/4-scos-stable/latest"
        tag = json.loads(urlopen(url).read())['pullSpec']
    cmd = f"oc adm release extract --command=openshift-install --to . {tag}"
    cmd += "; chmod 700 openshift-install"
    pprint(f'Downloading openshift-install {tag} in current directory')
    if debug:
        pprint(cmd)
    return call(cmd, shell=True)


def get_ci_installer(pull_secret, tag=None, macosx=False, debug=False, nightly=False, baremetal=False):
    arch = 'arm64' if os.uname().machine == 'aarch64' else None
    pull_secret = os.path.expanduser(pull_secret)
    if not os.path.exists(pull_secret):
        error(f"Pull secret {pull_secret} not found")
        return 1
    if 'registry.ci.openshift.org' not in open(pull_secret).read():
        error("Entry for registry.ci.openshift.org missing in pull secret")
        return 1
    if tag is not None and str(tag).count('.') == 1:
        _type = 'nightly' if nightly else 'ci'
        ci_url = f"https://amd64.ocp.releases.ci.openshift.org/api/v1/releasestream/{tag}.0-0.{_type}/latest"
        tag = json.loads(urlopen(ci_url).read())['pullSpec']
    if tag is None:
        tags = []
        r = urlopen("https://openshift-release.ci.openshift.org/graph?format=dot").readlines()
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
            basetag = 'ocp'
            tag = f'registry.ci.openshift.org/{basetag}/release:{tag}'
    os.environ['OPENSHIFT_RELEASE_IMAGE'] = tag
    pprint(f'Downloading openshift-install {tag} in current directory')
    binary = 'openshift-baremetal-install' if baremetal else 'openshift-install'
    cmd = f"oc adm release extract --registry-config {pull_secret} --command={binary} --to . {tag}"
    cmd += f"; chmod 700 {binary}"
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
            name, catalog, channel, csv, description, namespace, channels, crds = olm_app(appname, base_data)
            if name is None:
                error(f"Couldn't find any app matching {app}. Skipping...")
                continue
            app_data = {'name': name, 'catalog': catalog, 'channel': channel, 'namespace': namespace, 'csv': csv}
            app_data.update(base_data)
        pprint(f"Adding app {name}")
        result = config.create_app_openshift(name, app_data)
        if result != 0:
            error(f"Issue adding app {name}")


def wait_for_ignition(cluster, domain, role='worker'):
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    ignitionfile = f"{clusterdir}/ctlplane.ign" if role == 'master' else f"{clusterdir}/worker.ign"
    os.remove(ignitionfile)
    while not os.path.exists(ignitionfile) or os.stat(ignitionfile).st_size == 0:
        try:
            with open(ignitionfile, 'w') as dest:
                req = Request(f"http://api.{cluster}.{domain}:22624/config/{role}")
                req.add_header("Accept", "application/vnd.coreos.ignition+json; version=3.1.0")
                data = urlopen(req).read()
                dest.write(data.decode("utf-8"))
        except:
            pprint(f"Waiting 10s before retrieving full {ignitionfile}")
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
    config.create_openshift_iso(cluster, overrides=baremetal_iso_overrides, ignitionfile=ignitionfile, installer=True)
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
        svcip = safe_load(os.popen(svcip_cmd).read())['items'][0]['status']['addresses'][0]['address']
        svcport_cmd = 'oc get svc -n default httpd-kcli-svc -o yaml'
        svcport = safe_load(os.popen(svcport_cmd).read())['spec']['ports'][0]['nodePort']
        podname = os.popen('oc -n default get pod -l app=httpd-kcli -o name').read().split('/')[1].strip()
        try:
            call(f"oc wait -n default --for=condition=Ready pod/{podname}", shell=True)
        except Exception as e:
            error(f"Hit {e}")
            sys.exit(1)
        copycmd = f"oc -n default cp {iso_pool_path}/{cluster}-worker.iso {podname}:/var/www/html"
        call(copycmd, shell=True)
        return f'http://{svcip}:{svcport}/{cluster}-worker.iso'


def handle_baremetal_iso_sno(config, plandir, cluster, data, iso_pool=None):
    baremetal_web = data.get('baremetal_web', True)
    baremetal_web_dir = data.get('baremetal_web_dir', '/var/www/html')
    baremetal_web_subdir = data.get('baremetal_web_subdir')
    if baremetal_web_subdir is not None:
        baremetal_web_dir += f'/{baremetal_web_subdir}'
    baremetal_web_port = data.get('baremetal_web_port', 80)
    iso_pool_path = config.k.get_pool_path(iso_pool)
    if baremetal_web:
        call(f"sudo rm {baremetal_web_dir}/{cluster}-*.iso", shell=True)
        call(f'sudo cp {iso_pool_path}/{cluster}-*.iso {baremetal_web_dir}', shell=True)
        if baremetal_web_dir == '/var/www/html':
            call(f"sudo chown apache:apache {baremetal_web_dir}/{cluster}-*.iso", shell=True)
            if which('getenforce') is not None and os.popen('getenforce').read().strip() == 'Enforcing':
                call(f"sudo restorecon -Frvv {baremetal_web_dir}/{cluster}-*.iso", shell=True)
    else:
        call(f"sudo chmod a+r {iso_pool_path}/{cluster}-*.iso", shell=True)
    nic_name = data.get('baremetal_web_nic', 'default')
    nic = os.popen(f'ip r | grep {nic_name} | cut -d" " -f5 | head -1').read().strip()
    ip_cmd = f"ip -o addr show {nic} | awk '{{print $4}}' | cut -d '/' -f 1 | head -1"
    host_ip = os.popen(ip_cmd).read().strip()
    if baremetal_web_port != 80:
        host_ip += f":{baremetal_web_port}"
    iso_name = f"{cluster}-sno.iso"
    if baremetal_web_subdir is not None:
        iso_name = f'{baremetal_web_subdir}/{iso_name}'
    return f'http://{host_ip}/{iso_name}'


def process_baremetal_rules(config, cluster, baremetal_hosts, vmrules=[], overrides={}):
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    default_netmask = overrides.get('netmask') or overrides.get('prefix')
    default_gateway = overrides.get('gateway')
    default_nameserver = overrides.get('nameserver')
    default_domain = overrides.get('domain')
    baremetal_rules = {}
    for entry in baremetal_hosts:
        if isinstance(entry, dict):
            if 'name' in entry:
                baremetal_rules[entry['name']] = entry.get('nets')
            elif 'nets' in entry and ':9000' in entry.get('bmc_url', ''):
                baremetal_rules[os.path.basename(entry['bmc_url'])] = entry['nets']
    for name in baremetal_rules:
        for entry in vmrules:
            if len(entry) != 1:
                error(f"Wrong vm rule {entry}")
                sys.exit(1)
            rule = list(entry.keys())[0]
            if (re.match(rule, name) or fnmatch(name, rule)) and isinstance(entry[rule], dict)\
               and 'nets' in entry[rule] and baremetal_rules[name] is None:
                baremetal_rules[name] = entry[rule]['nets']
    if not baremetal_rules:
        return
    with open(f'{clusterdir}/macs.txt', 'w') as f:
        for name in baremetal_rules:
            netinfo = baremetal_rules[name]
            if netinfo is None or not isinstance(netinfo, list) or not isinstance(netinfo[0], dict):
                continue
            if len(netinfo) > 1:
                warning(f"Net entry above the first one will be ignored for {name}")
            netinfo = netinfo[0]
            if '.' not in name and default_domain is not None:
                name += f'.{default_domain}'
            mac, ip = netinfo.get('mac'), netinfo.get('ip')
            netmask = netinfo.get('netmask') or default_netmask
            gateway = netinfo.get('gateway') or default_gateway
            nameserver = netinfo.get('nameserver') or default_nameserver or gateway
            if mac is None or ip is None or netmask is None or gateway is None:
                warning(f"Ignoring incomplete entry {netinfo} for {name}")
            else:
                entry = f"{mac};{name};{ip};{netmask};{gateway};{nameserver}\n"
                f.write(entry)


def scale(config, plandir, cluster, overrides):
    storedparameters = overrides.get('storedparameters', True)
    plan = cluster
    client = config.client
    provider = config.type
    k = config.k
    data = {}
    installparam = {}
    pprint(f"Scaling on client {client}")
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if not os.path.exists(clusterdir):
        warning(f"Creating {clusterdir} from your input (auth creds will be missing)")
        data['client'] = config.client
        overrides['cluster'] = cluster
        api_ip = overrides.get('api_ip')
        if provider not in cloud_providers and api_ip is None:
            return {'result': 'failure', 'reason': 'Missing api_ip...'}
        domain = overrides.get('domain')
        if domain is None:
            return {'result': 'failure', 'reason': "Missing domain..."}
        os.mkdir(clusterdir)
        ignition_version = overrides['ignition_version']
        create_ignition_files(config, plandir, cluster, domain, api_ip=api_ip, ignition_version=ignition_version)
    if storedparameters and os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml", 'r') as install:
            installparam = safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    data['scale'] = True
    if os.path.exists(clusterdir):
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as paramfile:
            safe_dump(data, paramfile)
    image = data.get('image')
    if image is None:
        cluster_image = k.info(f"{cluster}-ctlplane-0").get('image')
        if cluster_image is None:
            return {'result': 'failure', 'reason': "Missing image..."}
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
            svcip = safe_load(os.popen(svcip_cmd).read())['items'][0]['status']['addresses'][0]['address']
            svcport_cmd = 'oc get svc -n default httpd-kcli-svc -o yaml'
            svcport = safe_load(os.popen(svcport_cmd).read())['spec']['ports'][0]['nodePort']
            iso_url = f'http://{svcip}:{svcport}/{cluster}-worker.iso'
        if 'secureboot' in overrides or [h for h in baremetal_hosts if 'secureboot' in h or 'bmc_secureboot' in h]:
            result = update_baremetal_hosts(baremetal_hosts, overrides=overrides, debug=config.debug)
            if result['result'] != 'success':
                return result
        result = start_baremetal_hosts_with_iso(baremetal_hosts, iso_url, overrides=overrides, debug=config.debug)
        if result['result'] != 'success':
            return result
        overrides['workers'] = overrides.get('workers', 0) - len(new_baremetal_hosts)
    for role in ['ctlplanes', 'workers']:
        overrides = data.copy()
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        if overrides.get(role, 0) <= 0:
            continue
        if provider in virt_providers:
            os.chdir(os.path.expanduser("~/.kcli"))
            if role == 'ctlplanes' and ('virtual_router_id' not in overrides or 'auth_pass' not in overrides):
                warning("Scaling up of ctlplanes won't work without virtual_router_id and auth_pass")
            result = config.plan(plan, inputfile=f'{plandir}/{role}.yml', overrides=overrides, threaded=threaded)
        elif provider in cloud_providers:
            result = config.plan(plan, inputfile=f'{plandir}/cloud_{role}.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            return result
        elif result.get('newvms', []):
            pprint(f"{role.capitalize()} nodes will join the cluster in a few minutes")
    return {'result': 'success'}


def create(config, plandir, cluster, overrides, dnsconfig=None):
    k = config.k
    log_level = 'debug' if config.debug else 'info'
    client = config.client
    provider = config.type
    arch = k.get_capabilities()['arch'] if provider == 'kvm' else 'x86_64'
    pprint(f"Deploying on client {client}")
    data = safe_load(open(f'{plandir}/kcli_default.yml'))
    data.update(overrides)
    fix_typos(data)
    esx = config.type == 'vsphere' and k.esx
    data['esx'] = esx
    ctlplanes = data['ctlplanes']
    if ctlplanes <= 0:
        return {'result': 'failure', 'reason': f"Invalid number of ctlplanes {ctlplanes}"}
    workers = data['workers']
    if workers < 0:
        return {'result': 'failure', 'reason': f"Invalid number of workers {workers}"}
    if data['dual_api_ip'] is not None:
        warning("Forcing dualstack")
        data['dualstack'] = True
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    if 'http_proxy' not in data and http_proxy is not None:
        pprint("Using proxy settings from environment")
        data['http_proxy'] = http_proxy
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        if 'https_proxy' not in data and https_proxy is not None:
            data['https_proxy'] = https_proxy
        no_proxy = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
        if 'no_proxy' not in data and no_proxy is not None:
            data['no_proxy'] = no_proxy
    if data['ctlplanes'] == 1 and data['workers'] == 0\
       and 'ctlplane_memory' not in overrides and 'memory' not in overrides:
        overrides['ctlplane_memory'] = 32768
        warning("Forcing memory of single ctlplane vm to 32G")
    retries = data['retries']
    data['cluster'] = cluster
    domain = data['domain']
    dns_k = dnsconfig.k if dnsconfig is not None else k
    if provider in cloud_providers:
        dns_zones = dns_k.list_dns_zones()
        if domain not in dns_zones and f'{domain}.' not in dns_zones:
            return {'result': 'failure', 'reason': f'domain {domain} needs to exist'}
    original_domain = None
    async_install = data['async']
    okd = data['okd']
    autoscale = data['autoscale']
    sslip = data['sslip']
    if 'baremetal_hosts' not in data and 'bmc_url' in data:
        host = {'bmc_url': data['bmc_url'], 'bmc_user': data.get('bmc_user'), 'bmc_password': data.get('bmc_password')}
        data['baremetal_hosts'] = [host]
    baremetal_hosts = data['baremetal_hosts']
    notify = data['notify']
    postscripts = data['postscripts']
    pprint(f"Deploying cluster {cluster}")
    plan = cluster
    overrides['kubetype'] = 'openshift'
    apps = overrides.get('apps', [])
    disks = overrides.get('disks', [30])
    overrides['kube'] = data['cluster']
    installparam = overrides.copy()
    installparam['cluster'] = cluster
    baremetal_sno = workers == 0 and len(baremetal_hosts) == 1
    baremetal_ctlplane = data['workers'] == 0 and len(baremetal_hosts) > 1
    sno_vm = data['sno_vm']
    sno = sno_vm or data['sno'] or baremetal_ctlplane or baremetal_sno
    data['sno'] = sno
    sno_wait = overrides.get('sno_wait') or baremetal_sno or data['api_ip'] is not None or sno_vm
    sno_disk = data['sno_disk']
    sno_ctlplanes = data['sno_ctlplanes'] or baremetal_ctlplane
    sno_workers = data['sno_workers']
    ignore_hosts = data['ignore_hosts'] or sslip
    if sno:
        if sno_disk is None:
            warning("sno_disk will be discovered")
        ctlplanes = 1
        workers = 0
        data['mdns'] = False
        data['kubetype'] = 'openshift'
        data['kube'] = data['cluster']
        if data['network_type'] == 'OpenShiftSDN':
            warning("Forcing network_type to OVNKubernetes")
            data['network_type'] = 'OVNKubernetes'
    elif ('lvms-operator' in apps or 'localstorage' in apps or 'ocs' in apps) and 'extra_disks' not in overrides\
            and 'extra_ctlplane_disks' not in overrides and 'extra_worker_disks' not in overrides and len(disks) == 1:
        warning("Storage apps require extra disks to be set")
    network = data['network']
    post_dualstack = False
    if data['dualstack'] and provider in cloud_providers:
        warning("Dual stack will be enabled at the end of the install")
        data['dualstack'] = False
        post_dualstack = True
    ipv6 = data['ipv6']
    disconnected_update = data['disconnected_update']
    disconnected_reuse = data['disconnected_reuse']
    disconnected_operators = data['disconnected_operators']
    certified_operators = data['disconnected_certified_operators']
    community_operators = data['disconnected_community_operators']
    marketplace_operators = data['disconnected_marketplace_operators']
    disconnected_url = data['disconnected_url']
    disconnected_user = data['disconnected_user']
    disconnected_password = data['disconnected_password']
    operators = disconnected_operators + community_operators + certified_operators + marketplace_operators
    disconnected = data['disconnected']
    disconnected_vm = data['disconnected_vm'] or (disconnected_url is None and (disconnected or operators))
    ipsec = data['ipsec']
    ipsec_mode = data['ipsec_mode']
    mtu = data['mtu']
    ovn_hostrouting = data['ovn_hostrouting']
    metal3 = data['metal3']
    autologin = data['autologin']
    dedicated_etcd = data['dedicated_etcd']
    if not data['coredns']:
        warning("You will need to provide DNS records for api and ingress on your own")
    keepalived = data['keepalived']
    if not keepalived:
        warning("You will need to provide LB for api and ingress on your own")
    mdns = data['mdns']
    localhost_fix = data['localhost_fix']
    ctlplane_localhost_fix = data['ctlplane_localhost_fix'] or localhost_fix
    worker_localhost_fix = data['worker_localhost_fix'] or localhost_fix
    sno_cpuset = data['sno_cpuset']
    kubevirt_api_service, kubevirt_api_service_node_port = False, False
    kubevirt_ignore_node_port = data['kubevirt_ignore_node_port']
    prega = data['prega']
    virtualization_nightly = data['virtualization_nightly']
    version = data['version']
    tag = data['tag']
    version = overrides.get('version') or detect_openshift_version(tag, OPENSHIFT_TAG)
    data['version'] = version
    if os.path.exists('coreos-installer'):
        pprint("Removing old coreos-installer")
        os.remove('coreos-installer')
    if version not in ['ci', 'candidate', 'nightly', 'stable']:
        return {'result': 'failure', 'reason': f"Incorrect version {version}"}
    else:
        pprint(f"Using {version} version")
    cluster = data.get('cluster')
    image = data['image']
    api_ip = data['api_ip']
    cidr = None
    if provider in virt_providers and keepalived and not sno and api_ip is None:
        network = data['network']
        networkinfo = k.info_network(network)
        if not networkinfo:
            return {'result': 'failure', 'reason': f"Issue getting network {network}"}
        if provider == 'kvm' and networkinfo['type'] == 'routed':
            cidr = networkinfo['cidr']
            if cidr == 'N/A':
                return {'result': 'failure', 'reason': "Couldnt gather an api_ip from your specified network"}
            api_index = 2 if ':' in cidr else -3
            api_ip = str(get_new_vip(network, ipv6=':' in cidr) or ip_network(cidr)[api_index])
            warning(f"Using {api_ip} as api_ip")
            overrides['api_ip'] = api_ip
            installparam['automatic_api_ip'] = True
            installparam['api_ip'] = api_ip
        elif provider == 'kubevirt':
            selector = {'kcli/plan': plan, 'kcli/role': 'ctlplane'}
            service_type = "LoadBalancer" if k.access_mode == 'LoadBalancer' else 'NodePort'
            namespace = k.namespace
            if service_type == 'NodePort':
                kubevirt_api_service_node_port = True
            api_ip = k.create_service(f"{cluster}-api", namespace, selector, _type=service_type,
                                      ports=[6443, 22623, 22624], openshift_hack=True)
            if api_ip is None:
                return {'result': 'failure', 'reason': "Couldnt gather an api_ip from your specified network"}
            else:
                pprint(f"Using api_ip {api_ip}")
                overrides['api_ip'] = api_ip
                overrides['kubevirt_api_service'] = True
                kubevirt_api_service = True
                overrides['mdns'] = False
                try:
                    patch_ingress_controller_wildcard()
                    selector = {'kcli/plan': plan, 'kcli/role': 'worker' if workers > 0 else 'ctlplane'}
                    k.create_service(f"{cluster}-ingress", namespace, selector, ports=[80, 443])
                    routecmd = f'oc -n {namespace} create route passthrough --service={cluster}-ingress '
                    routecmd += f'--hostname=http.apps.{cluster}.{domain} --wildcard-policy=Subdomain --port=443'
                    call(routecmd, shell=True)
                except:
                    pass
        else:
            return {'result': 'failure', 'reason': "You need to define api_ip in your parameters file"}
    if api_ip is not None:
        try:
            ip_address(api_ip)
        except:
            return {'result': 'failure', 'reason': f"Invalid api_ip {api_ip}"}
    if provider in virt_providers and keepalived and not sno and ':' in api_ip:
        ipv6 = True
    if ipv6:
        if data['network_type'] == 'OpenShiftSDN':
            warning("Forcing network_type to OVNKubernetes")
            data['network_type'] = 'OVNKubernetes'
        data['ipv6'] = True
        overrides['ipv6'] = True
        data['disconnected_ipv6_network'] = True
        if not disconnected_vm and disconnected_url is None:
            warning("Forcing disconnected_vm to True as no disconnected_url was provided")
            data['disconnected_vm'] = True
            disconnected_vm = True
        if sno and not data['dualstack'] and 'extra_args' not in overrides:
            warning("Forcing extra_args to ip=dhcp6 for sno to boot with ipv6")
            data['extra_args'] = 'ip=dhcp6'
    ingress_ip = data['ingress_ip']
    if ingress_ip is not None:
        if api_ip is not None and ingress_ip == api_ip:
            ingress_ip = None
            overrides['ingress_ip'] = None
        else:
            try:
                ip_address(ingress_ip)
            except:
                return {'result': 'failure', 'reason': f"Invalid ingress_ip {ingress_ip}"}
    if sslip and provider in virt_providers:
        if api_ip is None:
            return {'result': 'failure', 'reason': "Missing api_ip which is required with sslip"}
        original_domain = domain
        domain = f"{api_ip.replace('.', '-').replace(':', '-')}.sslip.io"
        data['domain'] = domain
        pprint(f"Setting domain to {domain}")
        ignore_hosts = False
    public_api_ip = data['public_api_ip']
    provider_network = False
    network = data['network']
    ctlplanes = data['ctlplanes']
    workers = data['workers']
    tag = data['tag']
    pull_secret = pwd_path(data.get('pull_secret')) if not okd else f"{plandir}/fake_pull.json"
    pull_secret = os.path.expanduser(pull_secret)
    macosx = data['macosx']
    if macosx and not os.path.exists('/i_am_a_container'):
        macosx = False
    if provider == 'openstack' and keepalived and not sno:
        if data['flavor'] is None:
            return {'result': 'failure', 'reason': "Missing flavor in parameter file"}
        provider_network = k.provider_network(network)
        if not provider_network:
            if api_ip is None:
                cidr = k.info_network(network)['cidr']
                api_ip = str(ip_network(cidr)[-3])
                data['api_ip'] = api_ip
                warning(f"Using {api_ip} as api_ip")
            if public_api_ip is None:
                public_api_ip = k.create_network_port(f"{cluster}-vip", network, ip=api_ip, floating=True)['floating']
    if not os.path.exists(pull_secret):
        return {'result': 'failure', 'reason': f"Missing pull secret file {pull_secret}"}
    if prega and 'quay.io/prega' not in open(os.path.expanduser(pull_secret)).read():
        return {'result': 'failure', 'reason': "entry for quay.io/prega missing in pull secret"}
    if virtualization_nightly and 'quay.io/openshift-cnv' not in open(os.path.expanduser(pull_secret)).read():
        return {'result': 'failure', 'reason': "entry for quay.io/openshift-cnv missing in pull secret"}
    if which('oc') is None:
        get_oc(macosx=macosx)
    pub_key = data['pub_key'] or get_ssh_pub_key()
    keys = data['keys']
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
        return {'result': 'failure', 'reason': f"Publickey file {pub_key} not found"}
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        if [v for v in k.list() if v.get('plan', 'kvirt') == cluster]:
            return {'result': 'failure', 'reason': f"Remove existing directory {clusterdir} or use --force"}
        else:
            pprint(f"Removing existing directory {clusterdir}")
            rmtree(clusterdir)
    if version == 'ci':
        if '/' not in str(tag) and str(tag).count('.') != 1:
            if arch in ['aarch64', 'arm64']:
                tag = f'registry.ci.openshift.org/ocp-arm64/release-arm64:{tag}'
            else:
                basetag = 'ocp'
                tag = f'registry.ci.openshift.org/{basetag}/release:{tag}'
    which_openshift = which('openshift-install')
    openshift_dir = os.path.dirname(which_openshift) if which_openshift is not None else '.'
    if which_openshift is not None and not has_internet():
        pprint("Using existing openshift-install found in your PATH")
        warning("Not checking version")
    elif okd:
        run = get_okd_installer(tag, version=version)
    elif not same_release_images(version=version, tag=tag, pull_secret=pull_secret, path=openshift_dir):
        if version in ['ci', 'nightly'] or '/' in str(tag):
            nightly = version == 'nightly'
            run = get_ci_installer(pull_secret, tag=tag, nightly=nightly)
        elif version in ['candidate', 'stable', 'latest']:
            run = get_downstream_installer(version=version, tag=tag, pull_secret=pull_secret)
        else:
            return {'result': 'failure', 'reason': f"Invalid version {version}"}
        if run != 0:
            return {'result': 'failure', 'reason': "Couldn't download openshift-install"}
        pprint("Move downloaded openshift-install somewhere in your PATH if you want to reuse it")
    elif which_openshift is not None:
        pprint("Using existing openshift-install found in your PATH")
    else:
        pprint("Reusing matching openshift-install")
    os.environ["PATH"] = f'{os.getcwd()}:{os.environ["PATH"]}'
    INSTALLER_VERSION = get_installer_version()
    pprint(f"Using installer version {INSTALLER_VERSION}")
    if disconnected_url is not None:
        if disconnected_user is None:
            return {'result': 'failure', 'reason': "disconnected_user needs to be set"}
        if disconnected_password is None:
            return {'result': 'failure', 'reason': "disconnected_password needs to be set"}
        if disconnected_url.startswith('http'):
            warning(f"Removing scheme from {disconnected_url}")
            disconnected_url = disconnected_url.replace('http://', '').replace('https://', '')
        update_pull_secret(pull_secret, disconnected_url, disconnected_user, disconnected_password)
        data['ori_tag'] = tag
        if '/' not in str(tag):
            disconnected_prefix = data['disconnected_prefix'] or 'openshift-release-dev/ocp-release'
            tag = f'{disconnected_url}/{disconnected_prefix}:{INSTALLER_VERSION}-{arch}'
            os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = tag
        if 'ca' not in data and 'quay.io' not in disconnected_url:
            pprint(f"Trying to gather registry ca cert from {disconnected_url}")
            cacmd = f"openssl s_client -showcerts -connect {disconnected_url} </dev/null 2>/dev/null|"
            cacmd += "openssl x509 -outform PEM"
            data['ca'] = os.popen(cacmd).read()
    if sno:
        pass
    elif image is None:
        image_type = provider
        region = k.region if provider == 'aws' else None
        try:
            image_url = get_installer_rhcos(_type=image_type, region=region, arch=arch)
        except:
            msg = f"Couldn't gather the {provider} image associated to this installer version"
            msg += "Force an image in your parameter file"
            return {'result': 'failure', 'reason': msg}
        if provider in ['aws', 'gcp']:
            image = image_url
        elif esx:
            image = image_url
            overrides['image_url'] = image
        else:
            if image_url.endswith('.vhd'):
                image = os.path.basename(image_url)
            else:
                image = os.path.basename(os.path.splitext(image_url)[0])
            if provider in ['ibm', 'kubevirt', 'proxmox']:
                image = image.replace('.', '-').replace('_', '-').lower()
            if provider == 'vsphere':
                image = image.replace(f'.{arch}', '')
            images = [v for v in k.volumes() if image in v]
            if not images:
                result = config.download_image(pool=config.pool, image=image, url=image_url,
                                               size=data['kubevirt_disk_size'])
                if result['result'] != 'success':
                    return result
        pprint(f"Using image {image}")
    elif provider == 'kubevirt' and '/' in image:
        warning(f"Assuming image {image} is available")
    else:
        pprint(f"Checking if image {image} is available")
        images = [v for v in k.volumes() if image in v]
        if not images:
            msg = f"Missing {image}. Indicate correct image in your parameters file..."
            return {'result': 'failure', 'reason': msg}
    overrides['image'] = image
    static_networking_ctlplane, static_networking_worker = False, False
    macentries = []
    custom_names = {}
    vmrules = overrides.get('vmrules', [])
    for entry in vmrules:
        if isinstance(entry, dict):
            hostname = list(entry.keys())[0]
            if isinstance(entry[hostname], dict):
                rule = entry[hostname]
                if 'name' in rule:
                    custom_names[hostname] = rule['name']
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
    if custom_names:
        overrides['custom_names'] = custom_names
    overrides['cluster'] = cluster
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
    if provider in virt_providers and disconnected_vm:
        disconnected_vm = f"{data['disconnected_reuse_name'] or cluster}-registry"
        pprint(f"Deploying disconnected vm {disconnected_vm}")
        data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
        disconnected_plan = f"{plan}-reuse" if disconnected_reuse else plan
        disconnected_overrides = data.copy()
        disconnected_overrides['OPENSHIFT_TAG'] = OPENSHIFT_TAG
        disconnected_overrides['kube'] = f"{cluster}-reuse" if disconnected_reuse else cluster
        disconnected_overrides['openshift_version'] = INSTALLER_VERSION
        disconnected_overrides['disconnected_operators_version'] = f"v4.{INSTALLER_VERSION.split('.')[1]}"
        x_apps = ['users', 'autolabeller', 'metal3', 'nfs']
        disconnected_operators_2 = [o['name'] for o in disconnected_operators if isinstance(o, dict) and 'name' in o]
        for app in apps:
            if app not in x_apps and app not in disconnected_operators and app not in disconnected_operators_2:
                warning(f"Adding app {app} to disconnected_operators array")
                disconnected_operators.append(app)
        disconnected_overrides['disconnected_operators'] = disconnected_operators
        result = config.plan(disconnected_plan, inputfile=f'{plandir}/disconnected.yml',
                             overrides=disconnected_overrides)
        if result['result'] != 'success':
            return result
        disconnected_ip, disconnected_vmport = _ssh_credentials(k, disconnected_vm)[1:]
        cacmd = "cat /opt/registry/certs/domain.crt"
        cacmd = ssh(disconnected_vm, ip=disconnected_ip, user='root', tunnel=config.tunnel,
                    tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                    insecure=True, cmd=cacmd, vmport=disconnected_vmport)
        disconnected_ca = os.popen(cacmd).read().strip()
        if data['ca'] is not None:
            data['ca'] += f"\n{disconnected_ca}"
        else:
            data['ca'] = disconnected_ca
        urlcmd = "cat /root/url.txt"
        urlcmd = ssh(disconnected_vm, ip=disconnected_ip, user='root', tunnel=config.tunnel,
                     tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                     insecure=True, cmd=urlcmd, vmport=disconnected_vmport)
        disconnected_url = os.popen(urlcmd).read().strip()
        overrides['disconnected_url'] = disconnected_url
        data['disconnected_url'] = disconnected_url
        versioncmd = "cat /root/version.txt"
        versioncmd = ssh(disconnected_vm, ip=disconnected_ip, user='root', tunnel=config.tunnel,
                         tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                         insecure=True, cmd=versioncmd, vmport=disconnected_vmport)
        disconnected_version = os.popen(versioncmd).read().strip()
        for source in ["'cs-*.yaml'", "'i*oc-mirror.yaml'"]:
            scpcmd = scp(disconnected_vm, ip=disconnected_ip, user='root', source=source, destination=clusterdir,
                         tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                         tunneluser=config.tunneluser, download=True, insecure=True, vmport=disconnected_vmport)
            os.system(scpcmd)
        patch_oc_mirror(clusterdir)
        os.environ['OPENSHIFT_INSTALL_RELEASE_IMAGE_OVERRIDE'] = disconnected_version
    data['pull_secret_path'] = pull_secret
    data['pull_secret'] = re.sub(r"\s", "", open(pull_secret).read())
    if disconnected_url is not None:
        if disconnected_update and disconnected_url != 'quay.io':
            data['release_tag'] = f'v4.{get_installer_minor(INSTALLER_VERSION)}'
            update_registry(config, plandir, cluster, data)
        key = f"{disconnected_user}:{disconnected_password}"
        key = str(b64encode(key.encode('utf-8')), 'utf-8')
        auths = json.loads(data['pull_secret'])['auths']
        if disconnected_url not in auths or auths[disconnected_url]['auth'] != key:
            auths[disconnected_url] = {'auth': key, 'email': 'jhendrix@karmalabs.corp'}
            data['pull_secret'] = json.dumps({"auths": auths})
    if provider == 'aws':
        aws_credentials(config)
    elif provider == 'gcp':
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser(config.options.get('credentials'))
    elif provider == 'azure':
        azure_credentials(config)
        if '-' in network:
            vnet = network.split('-')[0]
            data['machine_cidr'] = k.info_network(vnet)['cidr']
    elif provider == 'vsphere' and get_installer_minor(INSTALLER_VERSION) < 13:
        data['vsphere_legacy'] = True
    installconfig = config.process_inputfile(cluster, f"{plandir}/install-config.yaml", overrides=data)
    with open(f"{clusterdir}/install-config.yaml", 'w') as f:
        f.write(installconfig)
    with open(f"{clusterdir}/install-config.yaml.bck", 'w') as f:
        f.write(installconfig)
    run = call(f'openshift-install --dir={clusterdir} --log-level={log_level} create manifests', shell=True)
    if run != 0:
        msg = "Leaving environment for debugging purposes. "
        msg += f"Delete it with kcli delete kube --yes {cluster}"
        return {'result': 'failure', 'reason': msg}
    if provider == 'azure':
        prefix = safe_load(open(f'{clusterdir}/openshift/99_cloud-creds-secret.yaml'))['data']['azure_resource_prefix']
        new_prefix = b64encode(bytes(cluster, 'utf-8')).decode('utf-8')
        sedcmd = f'sed -i "s@{prefix}@{new_prefix}@" {clusterdir}/openshift/99_cloud-creds-secret.yaml'
        call(sedcmd, shell=True)
        old_prefix = b64decode(bytes(prefix, 'utf-8')).decode('utf-8')
        sedcmd = f'sed -i "s@{old_prefix}@{cluster}@" {clusterdir}/openshift/* {clusterdir}/manifests/*'
        call(sedcmd, shell=True)
    for f in glob(f"{clusterdir}/openshift/99_openshift-cluster-api_master-machines-*.yaml"):
        os.remove(f)
    for f in glob(f"{clusterdir}/openshift/99_openshift-cluster-api_worker-machineset-*"):
        os.remove(f)
    for f in glob(f"{clusterdir}/openshift/99_openshift-machine-api_master-control-plane-machine-set.yaml"):
        os.remove(f)
    ntp_server = data['ntp_server']
    if ntp_server is not None:
        ntp_data = config.process_inputfile(cluster, f"{plandir}/chrony.conf", overrides={'ntp_server': ntp_server})
        for role in ['master', 'worker']:
            ntp = config.process_inputfile(cluster, f"{plandir}/99-chrony.yaml",
                                           overrides={'role': role, 'ntp_data': ntp_data})
            with open(f"{clusterdir}/manifests/99-chrony-{role}.yaml", 'w') as f:
                f.write(ntp)
    baremetal_cidr = data['baremetal_cidr']
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
    for manifest in glob(f"{clusterdir}/*.yaml"):
        if os.stat(manifest).st_size == 0:
            warning(f"Skipping empty manifest {manifest}")
        elif manifest.startswith(f'{clusterdir}/cs-') or 'oc-mirror' in manifest:
            pprint(f"Injecting manifest {manifest}")
            copy2(manifest, f"{clusterdir}/openshift")
    if disconnected_operators:
        copy2(f'{plandir}/99-operatorhub.yaml', f"{clusterdir}/openshift")
    network_type = data['network_type']
    if network_type == 'Calico':
        calico_version = data['calico_version']
        with TemporaryDirectory() as tmpdir:
            calico_data = {'tmpdir': tmpdir, 'clusterdir': clusterdir, 'calico_version': calico_version}
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
    if ipsec or ipsec_mode is not None or ovn_hostrouting or mtu != 1400:
        valid_modes = ['Full', 'Disabled', 'External']
        if ipsec_mode is not None and ipsec_mode not in valid_modes:
            warning(f"Incorrect ipsec_mode. Choose between {','.join(valid_modes)}")
            warning("Setting ipsec_mode to Full")
            ipsec_mode = 'Full'
        ovn_data = config.process_inputfile(cluster, f"{plandir}/99-ovn.yaml",
                                            overrides={'ipsec': ipsec, 'ovn_hostrouting': ovn_hostrouting,
                                                       'mtu': mtu, 'mode': ipsec_mode})
        with open(f"{clusterdir}/openshift/99-ovn.yaml", 'w') as f:
            f.write(ovn_data)
    if workers == 0 or not mdns or kubevirt_api_service:
        copy2(f'{plandir}/cluster-scheduler-02-config.yml', f"{clusterdir}/manifests")
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
            default_replicas = 1 if workers == 1 else 2
            replicas = 1 if sno or (ctlplanes == 1 and workers == 0) or len(baremetal_hosts) == 1 else default_replicas
            bm_workers = len(baremetal_hosts) > 0 and workers > 0
            if provider in virt_providers and (worker_localhost_fix or bm_workers):
                replicas = ctlplanes
                ingressrole = 'master'
                warning("Forcing router pods on ctlplanes")
                copy2(f'{plandir}/cluster-scheduler-02-config.yml', f"{clusterdir}/manifests")
            ingressconfig = config.process_inputfile(cluster, f, overrides={'replicas': replicas, 'role': ingressrole,
                                                                            'cluster': cluster, 'domain': domain})
            with open(f"{clusterdir}/openshift/99-ingress-controller.yaml", 'w') as _f:
                _f.write(ingressconfig)
            continue
        if '99-iptables.yaml' in f:
            if provider not in cloud_providers and not sno:
                ip = ingress_ip or api_ip
                iptables = 'ip6tables' if ':' in ip else 'iptables'
                iptables_overrides = {'ip': ip, 'iptables': iptables}
                iptablesdata = config.process_inputfile(cluster, f, overrides=iptables_overrides)
                with open(f"{clusterdir}/openshift/99-iptables.yaml", 'w') as _f:
                    _f.write(iptablesdata)
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
    if virtualization_nightly:
        pprint("Adding custom catalog for OpenShift Virtualization Nightly")
        copy2(f'{plandir}/99-openshift-virtualization-catalog.yaml', f"{clusterdir}/openshift")
    if prega and not disconnected_vm and disconnected_url is None:
        pprint("Adding custom catalog for Prega")
        pregafile = config.process_inputfile(cluster, f'{plandir}/99-prega-catalog.yaml',
                                             overrides={'version': version})
        with open(f"{clusterdir}/openshift/99-prega-catalog.yaml", 'w') as _f:
            _f.write(pregafile)
    registry = disconnected_url or 'quay.io'
    if async_install or autoscale:
        config.import_in_kube(network=network, dest=f"{clusterdir}/openshift", secure=True)
        deletionfile = f"{plandir}/99-bootstrap-deletion.yaml"
        deletionfile = config.process_inputfile(cluster, deletionfile, overrides={'cluster': cluster,
                                                                                  'registry': registry,
                                                                                  'client': config.client})
        with open(f"{clusterdir}/openshift/99-bootstrap-deletion.yaml", 'w') as _f:
            _f.write(deletionfile)
        if not autoscale:
            deletionfile2 = f"{plandir}/99-bootstrap-deletion-2.yaml"
            deletionfile2 = config.process_inputfile(cluster, deletionfile2, overrides={'registry': registry})
            with open(f"{clusterdir}/openshift/99-bootstrap-deletion-2.yaml", 'w') as _f:
                _f.write(deletionfile2)
    if notify and (async_install or (sno and not sno_wait)):
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
                                                                              'sno': sno,
                                                                              'cmds': notifycmds,
                                                                              'mailcontent': mailcontent})
        with open(f"{clusterdir}/openshift/99-notifications.yaml", 'w') as _f:
            _f.write(notifyfile)
    if apps and (async_install or (sno and not sno_wait)):
        registry = disconnected_url or 'quay.io'
        appsfile = f"{plandir}/99-apps.yaml"
        apps_data = {'registry': registry, 'overrides': overrides, 'overrides_string': safe_dump(overrides)}
        appsfile = config.process_inputfile(cluster, appsfile, overrides=apps_data)
        with open(f"{clusterdir}/openshift/99-apps.yaml", 'w') as _f:
            _f.write(appsfile)
    if ctlplane_localhost_fix:
        localctlplane = config.process_inputfile(cluster, f"{plandir}/20-localhost-fix.yaml",
                                                 overrides={'role': 'master'})
        with open(f"{clusterdir}/openshift/20-localhost-fix-ctlplane.yaml", 'w') as _f:
            _f.write(localctlplane)
    if worker_localhost_fix:
        localworker = config.process_inputfile(cluster, f"{plandir}/20-localhost-fix.yaml",
                                               overrides={'role': 'worker'})
        with open(f"{clusterdir}/openshift/99-localhost-fix-worker.yaml", 'w') as _f:
            _f.write(localworker)
    if metal3:
        copy2(f"{plandir}/99-metal3-provisioning.yaml", f"{clusterdir}/openshift")
        copy2(f"{plandir}/99-metal3-fake-machine.yaml", f"{clusterdir}/openshift")
    if autologin:
        for role in ['ctlplane', 'worker']:
            autologinfile = config.process_inputfile(cluster, f"{plandir}/99-autologin.yaml", overrides={'role': role})
            with open(f"{clusterdir}/openshift/99-autologin-{role}.yaml", 'w') as _f:
                _f.write(autologinfile)
    if dedicated_etcd:
        extra_disks = data['extra_ctlplane_disks'] or data['extra_disks']
        if not extra_disks:
            dedicated_etcd_size = data['dedicated_etcd_size']
            warning(f"Adding an additional {dedicated_etcd_size}gb disk for etcd")
            extra_disks = [dedicated_etcd_size]
            data['extra_ctlplane_disks'] = extra_disks
        extra_disk = extra_disks[0]
        if config.type == 'vsphere' or isinstance(extra_disk, dict) and extra_disk.get('interface', '') == 'scsi':
            disk = 'sdb'
        else:
            disk = 'vdb'
        etcdfile = config.process_inputfile(cluster, f"{plandir}/98-etcd.yaml", overrides={'disk': disk})
        with open(f"{clusterdir}/openshift/98-etcd.yaml", 'w') as _f:
            _f.write(etcdfile)
    if provider == 'kubevirt':
        kubevirtctlplane = config.process_inputfile(cluster, f"{plandir}/99-kubevirt-fix.yaml",
                                                    overrides={'role': 'master'})
        with open(f"{clusterdir}/openshift/99-kubevirt-fix-ctlplane.yaml", 'w') as _f:
            _f.write(kubevirtctlplane)
        kubevirtworker = config.process_inputfile(cluster, f"{plandir}/99-kubevirt-fix.yaml",
                                                  overrides={'role': 'worker'})
        with open(f"{clusterdir}/openshift/99-kubevirt-fix-worker.yaml", 'w') as _f:
            _f.write(kubevirtworker)
    if sno:
        sno_name = f"{cluster}-sno"
        sno_files = []
        sno_disable_nics = data['sno_disable_nics']
        if ipv6 or sno_disable_nics:
            nm_data = config.process_inputfile(cluster, f"{plandir}/kcli-ipv6.conf.j2", overrides=data)
            sno_files.append({'path': "/etc/NetworkManager/conf.d/kcli-ipv6.conf", 'data': nm_data})
        sno_dns = data['sno_dns']
        if sno_dns is None:
            sno_dns = False
            for entry in [f'api-int.{cluster}.{domain}', f'api.{cluster}.{domain}', f'xxx.apps.{cluster}.{domain}']:
                try:
                    gethostbyname(entry)
                except:
                    sno_dns = True
            data['sno_dns'] = sno_dns
        if sno_dns:
            warning("Injecting coredns static pod as some DNS records were missing")
            coredns_data = config.process_inputfile(cluster, f"{plandir}/staticpods/coredns.yml", overrides=data)
            corefile_data = config.process_inputfile(cluster, f"{plandir}/Corefile", overrides=data)
            forcedns_data = config.process_inputfile(cluster, f"{plandir}/99-kcli-forcedns", overrides=data)
            sno_files.extend([{'path': "/etc/kubernetes/manifests/coredns.yml", 'data': coredns_data},
                              {'path': "/etc/kubernetes/Corefile.template", 'data': corefile_data},
                              {"path": "/etc/NetworkManager/dispatcher.d/99-kcli-forcedns", "data": forcedns_data,
                               "mode": int('755', 8)}])
        if api_ip is not None:
            data['virtual_router_id'] = data['virtual_router_id'] or hash(cluster) % 254 + 1
            virtual_router_id = data['virtual_router_id']
            pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
            data['auth_pass'] = ''.join(choice(ascii_letters + digits) for i in range(5))
            vips = [api_ip, ingress_ip] if ingress_ip is not None else [api_ip]
            pprint(f"Injecting keepalived static pod with {','.join(vips)}")
            keepalived_data = config.process_inputfile(cluster, f"{plandir}/staticpods/keepalived.yml", overrides=data)
            keepalivedconf_data = config.process_inputfile(cluster, f"{plandir}/keepalived.conf", overrides=data)
            sno_files.extend([{"path": "/etc/kubernetes/manifests/keepalived.yml", "data": keepalived_data},
                              {"path": "/etc/kubernetes/keepalived.conf.template", "data": keepalivedconf_data}])
        if sno_cpuset is not None:
            pprint("Injecting workload partitioning files")
            partitioning_data = config.process_inputfile(cluster, f"{plandir}/01-workload-partitioning", overrides=data)
            pinning_data = config.process_inputfile(cluster, f"{plandir}/openshift-workload-pinning", overrides=data)
            sno_files.extend([{"path": "/etc/crio/crio.conf.d/01-workload-partitioning", "data": partitioning_data},
                              {"path": "/etc/kubernetes/openshift-workload-pinning", "data": pinning_data}])
        if sno_files:
            rendered = config.process_inputfile(cluster, f"{plandir}/99-sno.yaml", overrides={'files': sno_files})
            with open(f"{clusterdir}/openshift/99-sno.yaml", 'w') as f:
                f.write(rendered)
        if sno_ctlplanes:
            sno_ctlplanes_number = len(baremetal_hosts) if baremetal_hosts else 3
            ingress = config.process_inputfile(cluster, f"{plandir}/customisation/99-ingress-controller.yaml",
                                               overrides={'role': 'master', 'cluster': cluster, 'domain': domain,
                                                          'replicas': sno_ctlplanes_number})
            with open(f"{clusterdir}/openshift/99-ingress-controller.yaml", 'w') as _f:
                _f.write(ingress)
        pprint("Generating bootstrap-in-place ignition")
        run = call(f'openshift-install --dir={clusterdir} --log-level={log_level} create single-node-ignition-config',
                   shell=True)
        if run != 0:
            return {'result': 'failure', 'reason': "Hit issue when generating bootstrap-in-place ignition"}
        vmrules = overrides.get('vmrules') or config.vmrules
        process_baremetal_rules(config, cluster, baremetal_hosts, vmrules=vmrules, overrides=overrides)
        disable_ipv6 = 'ipv6' in overrides and not overrides['ipv6']
        data['disable_ipv6'] = disable_ipv6
        overrides['disable_ipv6'] = disable_ipv6
        move(f"{clusterdir}/bootstrap-in-place-for-live-iso.ign", f"./{sno_name}.ign")
        with open("iso.ign", 'w') as f:
            iso_overrides = data.copy()
            iso_overrides['image'] = 'rhcos4000'
            sno_extra_args = overrides.get('sno_extra_args')
            _files = [{"path": "/root/sno-finish.service", "origin": f"{plandir}/sno-finish.service"},
                      {"path": "/usr/local/bin/sno-finish.sh", "origin": f"{plandir}/sno-finish.sh", "mode": 700}]
            if notify:
                _files.append({"path": "/root/kubeconfig", "origin": f'{clusterdir}/auth/kubeconfig'})
            if ipv6 or sno_disable_nics:
                nm_data = config.process_inputfile(cluster, f"{plandir}/kcli-ipv6.conf.j2", overrides=data)
                _files.append({'path': "/etc/NetworkManager/conf.d/kcli-ipv6.conf", 'content': nm_data})
            iso_overrides['files'] = _files
            if os.path.exists(f'{clusterdir}/macs.txt'):
                bootstrap_data = open(f'{clusterdir}/macs.txt').readlines()[0].strip().split(';')[1:]
                hostname, ip, netmask, gateway, nameserver = bootstrap_data
                dev = overrides.get('sno_bootstrap_nic', 'enp1s0')
                bootstrap_data = f"ip={ip}::{gateway}:{netmask}:{hostname}:{dev}:none nameserver={nameserver}"
                if sno_extra_args is not None:
                    sno_extra_args += f" {bootstrap_data}"
                else:
                    sno_extra_args = bootstrap_data
                iso_overrides['sno_extra_args'] = sno_extra_args
            result = config.create_vm(sno_name, overrides=iso_overrides, onlyassets=True)
            pprint("Writing iso.ign to current dir")
            f.write(result['userdata'])
        live_url = os.environ.get('LIVEISO_URL') or overrides.get('liveiso_url')
        if provider == 'fake':
            pprint("Storing generated iso in current dir")
            generate_rhcos_iso(k, f"{cluster}-sno", 'default', installer=True, extra_args=sno_extra_args, url=live_url)
        else:
            iso_pool = data['pool'] or config.pool
            pprint(f"Storing generated iso in pool {iso_pool}")
            generate_rhcos_iso(k, f"{cluster}-sno", iso_pool, installer=True, extra_args=sno_extra_args, url=live_url)
        if sno_ctlplanes:
            if api_ip is None:
                warning("sno ctlplanes requires api vip to be defined. Skipping")
            else:
                ctlplane_overrides = overrides.copy()
                ctlplane_overrides['role'] = 'ctlplane'
                ctlplane_overrides['image'] = 'rhcos410'
                config.create_openshift_iso(cluster, overrides=ctlplane_overrides, installer=True)
        if sno_workers:
            worker_overrides = overrides.copy()
            worker_overrides['role'] = 'worker'
            worker_overrides['image'] = 'rhcos410'
            config.create_openshift_iso(cluster, overrides=worker_overrides, installer=True)
        sno_vm_ip = None
        sno_vm_port = None
        if sno_vm:
            result = config.plan(plan, inputfile=f'{plandir}/sno.yml', overrides=overrides)
            if result['result'] != 'success':
                return result
            if api_ip is None:
                while sno_vm_ip is None:
                    sno_info = k.info(f'{cluster}-sno')
                    sno_nets = sno_info.get('nets', [])
                    if provider == 'kubevirt' and len(sno_nets) == 1 and sno_nets[0]['net'] == 'default'\
                       and not os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
                        sno_vm_host = sno_info.get('host')
                        sno_vm_port = sno_info.get('apiport')
                        if sno_vm_host is not None and sno_vm_port is not None:
                            sno_vm_ip = gethostbyname(sno_vm_host)
                            break
                    else:
                        sno_vm_ip = sno_info.get('ip')
                    pprint(f"Waiting for VM {cluster}-sno to get an ip")
                    sleep(5)
        if sno_vm_port is not None:
            if os.path.exists('/i_am_a_container') and os.environ.get('KUBERNETES_SERVICE_HOST') is not None:
                sno_vm_ip = sno_info.get('ip')
                cmd = f'sed s/:6443/:{sno_vm_port}/ {clusterdir}/auth/kubeconfig > {clusterdir}/auth/kubeconfig.ext'
            else:
                cmd = f'sed -i s/:6443/:{sno_vm_port}/ {clusterdir}/auth/kubeconfig'
            call(cmd, shell=True)
        if ignore_hosts:
            warning("Not updating /etc/hosts as per your request")
        elif api_ip is not None or sno_vm_ip is not None:
            update_openshift_etc_hosts(cluster, domain, api_ip or sno_vm_ip, ingress_ip)
        elif sno_dns:
            warning("Add the following entry in /etc/hosts if needed")
            dnsentries = ['api', 'console-openshift-console.apps', 'oauth-openshift.apps',
                          'prometheus-k8s-openshift-monitoring.apps']
            dnsentry = ' '.join([f"{entry}.{cluster}.{domain}" for entry in dnsentries])
            warning(f"$your_node_ip {dnsentry}")
        if baremetal_hosts:
            iso_pool = data['pool'] or config.pool
            iso_url = handle_baremetal_iso_sno(config, plandir, cluster, data, iso_pool)
            if len(baremetal_hosts) > 0:
                overrides['role'] = 'ctlplane' if sno_ctlplanes else 'worker'
            if 'secureboot' in overrides or [h for h in baremetal_hosts if 'secureboot' in h or 'bmc_secureboot' in h]:
                result = update_baremetal_hosts(baremetal_hosts, overrides=overrides, debug=config.debug)
                if result['result'] != 'success':
                    return result
            result = start_baremetal_hosts_with_iso(baremetal_hosts, iso_url, overrides=overrides, debug=config.debug)
            if result['result'] != 'success':
                return result
        if sno_wait:
            installcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for install-complete'
            installcommand = ' || '.join([installcommand for x in range(retries)])
            pprint("Launching install-complete step. It will be retried extra times in case of timeouts")
            run = call(installcommand, shell=True)
            if run != 0:
                msg = "Leaving environment for debugging purposes. "
                msg += f"Delete it with kcli delete cluster --yes {cluster}"
                return {'result': 'failure', 'reason': msg}
        else:
            c = f"{clusterdir}/auth/kubeconfig"
            kubepassword = open(f"{clusterdir}/auth/kubeadmin-password").read()
            console = f"https://console-openshift-console.apps.{cluster}.{domain}"
            info2(f"To access the cluster as the system:admin user when running 'oc', run export KUBECONFIG={c}")
            info2(f"Access the Openshift web-console here: {console}")
            info2(f"Login to the console with user: kubeadmin, password: {kubepassword}")
            if not baremetal_hosts:
                pprint(f"Plug {cluster}-sno.iso to your SNO node to complete the installation")
            if sno_ctlplanes:
                pprint(f"Plug {cluster}-master.iso to get additional ctlplanes")
            if sno_workers:
                pprint(f"Plug {cluster}-worker.iso to get additional workers")
        backup_paramfile(config.client, installparam, clusterdir, cluster, plan, image, dnsconfig)
        os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
        if sno_wait:
            process_apps(config, clusterdir, apps, overrides)
        return {'result': 'success'}
    if autoscale:
        commondir = os.path.dirname(pprint.__code__.co_filename)
        autoscale_overrides = {'cluster': cluster, 'kubetype': 'openshift', 'workers': workers, 'replicas': 1}
        autoscale_data = config.process_inputfile(cluster, f"{commondir}/autoscale.yaml.j2",
                                                  overrides=autoscale_overrides)
        with open(f"{clusterdir}/openshift/99-autoscale.yaml", 'w') as f:
            f.write(autoscale_data)
    run = call(f'openshift-install --dir={clusterdir} --log-level={log_level} create ignition-configs', shell=True)
    if run != 0:
        msg = "Hit issues when generating ignition-config files"
        msg += ". Leaving environment for debugging purposes, "
        msg += f"Delete it with kcli delete kube --yes {cluster}"
        return {'result': 'failure', 'reason': msg}
    if provider in virt_providers and keepalived:
        overrides['virtual_router_id'] = data['virtual_router_id'] or hash(cluster) % 254 + 1
        virtual_router_id = overrides['virtual_router_id']
        pprint(f"Using keepalived virtual_router_id {virtual_router_id}")
        installparam['virtual_router_id'] = virtual_router_id
        auth_pass = ''.join(choice(ascii_letters + digits) for i in range(5))
        overrides['auth_pass'] = auth_pass
        installparam['auth_pass'] = auth_pass
        pprint(f"Using {api_ip} for api vip....")
        host_ip = api_ip if provider != "openstack" or provider_network else public_api_ip
        if ignore_hosts or (not kubevirt_ignore_node_port and kubevirt_api_service and kubevirt_api_service_node_port):
            warning("Ignoring /etc/hosts")
        else:
            update_openshift_etc_hosts(cluster, domain, host_ip, ingress_ip)
    bucket_url = None
    if provider in cloud_providers + ['openstack']:
        bucket = f"{cluster}-{domain.replace('.', '-')}"
        if bucket not in k.list_buckets():
            k.create_bucket(bucket)
        k.upload_to_bucket(bucket, f"{clusterdir}/bootstrap.ign", public=True)
        bucket_url = k.public_bucketfile_url(bucket, "bootstrap.ign")
    move(f"{clusterdir}/master.ign", f"{clusterdir}/master.ign.ori")
    move(f"{clusterdir}/worker.ign", f"{clusterdir}/worker.ign.ori")
    with open(f"{clusterdir}/worker.ign.ori") as f:
        ignition_version = json.load(f)['ignition']['version']
        installparam['ignition_version'] = ignition_version
    create_ignition_files(config, plandir, cluster, domain, api_ip=api_ip, bucket_url=bucket_url,
                          ignition_version=ignition_version)
    backup_paramfile(config.client, installparam, clusterdir, cluster, plan, image, dnsconfig)
    if provider in virt_providers:
        if provider == 'vsphere':
            basefolder = config.options.get('basefolder')
            restricted = config.options.get('restricted', False)
            vmfolder = '/vm'
            if basefolder is not None:
                vmfolder += f'/{basefolder}'
            if not restricted:
                vmfolder += f'/{cluster}'
                pprint(f"Creating vm folder {vmfolder}")
                k.create_vm_folder(cluster)
        pprint("Deploying bootstrap")
        result = config.plan(plan, inputfile=f'{plandir}/bootstrap.yml', overrides=overrides)
        if result['result'] != 'success':
            return result
        if static_networking_ctlplane:
            wait_for_ignition(cluster, domain, role='master')
        pprint("Deploying ctlplanes")
        threaded = data['threaded'] or data['ctlplanes_threaded']
        if baremetal_hosts:
            overrides['workers'] = overrides['workers'] - len(baremetal_hosts)
        result = config.plan(plan, inputfile=f'{plandir}/ctlplanes.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            return result
        if dnsconfig is not None and keepalived:
            dns_overrides = {'api_ip': api_ip, 'ingress_ip': ingress_ip, 'cluster': cluster, 'domain': domain}
            result = dnsconfig.plan(plan, inputfile=f'{plandir}/cloud_dns.yml', overrides=dns_overrides)
            if result['result'] != 'success':
                return result
    else:
        pprint("Deploying bootstrap")
        result = config.plan(plan, inputfile=f'{plandir}/cloud_bootstrap.yml', overrides=overrides)
        if result['result'] != 'success':
            return result
        if provider == 'ibm':
            while api_ip is None:
                api_ip = k.info(f"{cluster}-bootstrap").get('private_ip')
                pprint("Gathering bootstrap private ip")
                sleep(10)
            sedcmd = f'sed -i "s@api-int.{cluster}.{domain}@{api_ip}@" {clusterdir}/ctlplane.ign'
            call(sedcmd, shell=True)
        pprint("Deploying ctlplanes")
        threaded = data['threaded'] or data['ctlplanes_threaded']
        result = config.plan(plan, inputfile=f'{plandir}/cloud_ctlplanes.yml', overrides=overrides, threaded=threaded)
        if result['result'] != 'success':
            return result
        if provider == 'ibm':
            first_ctlplane_ip = None
            while first_ctlplane_ip is None:
                first_ctlplane_ip = k.info(f"{cluster}-ctlplane-0").get('private_ip')
                pprint("Gathering first ctlplane bootstrap ip")
                sleep(10)
            sedcmd = f'sed -i "s@api-int.{cluster}.{domain}@{first_ctlplane_ip}@" {clusterdir}/worker.ign'
            call(sedcmd, shell=True)
        result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_api.yml', overrides=overrides)
        if result['result'] != 'success':
            return result
        if workers == 0:
            result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_apps.yml', overrides=overrides)
            if result['result'] != 'success':
                return result
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
        if 'kubeconfig' in config.ini[config.client]:
            kubeconfig = config.ini[config.client].get('kubeconfig')
            hostip_cmd = f'KUBECONFIG={kubeconfig} oc get node {nodehost} -o yaml'
            hostip = safe_load(os.popen(hostip_cmd).read())['status']['addresses'][0]['address']
            update_openshift_etc_hosts(cluster, domain, hostip)
    if not async_install:
        bootstrapcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for bootstrap-complete'
        bootstrapcommand = ' || '.join([bootstrapcommand for x in range(retries)])
        run = call(bootstrapcommand, shell=True)
        if run != 0:
            msg = "Leaving environment for debugging purposes. "
            msg += f"Delete it with kcli delete cluster --yes {cluster}"
            return {'result': 'failure', 'reason': msg}
        if dnsconfig is not None:
            pprint(f"Deleting Dns entry for {cluster}-bootstrap in {domain}")
            z = dnsconfig.k
            z.delete_dns(f"{cluster}-bootstrap", domain)
        delete_lastvm(f"{cluster}-bootstrap", config.client)
    if workers > 0:
        if static_networking_worker:
            wait_for_ignition(cluster, domain, role='worker')
        pprint("Deploying workers")
        if 'name' in overrides:
            del overrides['name']
        if provider in virt_providers:
            if baremetal_hosts:
                iso_pool = data['pool'] or config.pool
                iso_url = handle_baremetal_iso(config, plandir, cluster, data, baremetal_hosts, iso_pool)
                result = start_baremetal_hosts_with_iso(baremetal_hosts, iso_url, overrides=overrides,
                                                        debug=config.debug)
                if result['result'] != 'success':
                    return result
            if overrides['workers'] > 0:
                threaded = data['threaded'] or data['workers_threaded']
                result = config.plan(plan, inputfile=f'{plandir}/workers.yml', overrides=overrides, threaded=threaded)
                if result['result'] != 'success':
                    return result
        elif provider in cloud_providers:
            result = config.plan(plan, inputfile=f'{plandir}/cloud_workers.yml', overrides=overrides)
            if result['result'] != 'success':
                return result
            result = config.plan(plan, inputfile=f'{plandir}/cloud_lb_apps.yml', overrides=overrides)
            if result['result'] != 'success':
                return result
    if async_install:
        kubeconf = f"{clusterdir}/auth/kubeconfig"
        kubepassword = open(f"{clusterdir}/auth/kubeadmin-password").read()
        if async_install:
            success("Async Cluster created")
            info2("You will need to wait before it is fully available")
        info2(f"To access the cluster as the system:admin user when running 'oc', run export KUBECONFIG={kubeconf}")
        info2(f"Access the Openshift web-console here: https://console-openshift-console.apps.{cluster}.{domain}")
        info2(f"Login to the console with user: kubeadmin, password: {kubepassword}")
        return {'result': 'success'}
    else:
        installcommand = f'openshift-install --dir={clusterdir} --log-level={log_level} wait-for install-complete'
        installcommand += f" || {installcommand} || {installcommand}"
        pprint("Launching install-complete step. It will be retried twice in case of timeout")
        run = call(installcommand, shell=True)
        if run != 0:
            msg = "Leaving environment for debugging purposes. "
            msg += f"Delete it with kcli delete cluster --yes {cluster}"
            return {'result': 'failure', 'reason': msg}
    pprint(f"Deleting {cluster}-bootstrap")
    k.delete(f"{cluster}-bootstrap")
    if provider in cloud_providers:
        bucket = f"{cluster}-{domain.replace('.', '-')}"
        k.delete_bucket(bucket)
        if provider == 'aws':
            k.spread_cluster_tag(cluster, network)
            pprint("Creating secret for aws-load-balancer-operator")
            lbcmd = "oc create secret generic aws-load-balancer-operator -n openshift-operators "
            lbcmd += f"--from-file=credentials={os.path.expanduser('~/.aws/credentials')}"
            call(lbcmd, shell=True)
            if 'aws-load-balancer-operator' not in apps:
                apps.append('aws-load-balancer-operator')
    if original_domain is not None:
        overrides['domain'] = original_domain
    if provider in cloud_providers:
        wait_cloud_dns(cluster, domain)
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    process_apps(config, clusterdir, apps, overrides)
    process_postscripts(clusterdir, postscripts)
    if provider in cloud_providers and ctlplanes == 1 and workers == 0 and data['sno_cloud_remove_lb']:
        pprint("Removing loadbalancers as there is a single ctlplane")
        k.delete_loadbalancer(f"api.{cluster}")
        k.delete_loadbalancer(f"apps.{cluster}")
        api_ip = k.info(f"{cluster}-ctlplane-0").get('ip')
        k.delete_dns(f'api.{cluster}', domain=domain)
        k.reserve_dns(f'api.{cluster}', domain=domain, ip=api_ip)
        k.delete_dns(f'apps.{cluster}', domain=domain)
        k.reserve_dns(f'apps.{cluster}', domain=domain, ip=api_ip, alias=['*'])
        if provider == 'ibm':
            k._add_sno_security_group(cluster)
    if post_dualstack:
        with TemporaryDirectory() as tmpdir:
            patch_ipv6 = config.process_inputfile('xxx', f'{plandir}/patch_ipv6.json', overrides=data)
            with open(f"{tmpdir}/patch_ipv6.json", 'w') as f:
                f.write(patch_ipv6)
            call(f"oc patch network.config.openshift.io cluster --type=json --patch-file {tmpdir}/patch_ipv6.json",
                 shell=True)
    return {'result': 'success'}
