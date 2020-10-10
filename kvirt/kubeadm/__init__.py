#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import info, pprint, get_kubectl, kube_create_app, scp, word2number
from kvirt.defaults import UBUNTUS
import os
import sys
import yaml

# virtplatforms = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere', 'packet']
cloudplatforms = ['aws', 'gcp']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'xip': False, 'kube': cluster, 'kubetype': 'generic'}
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if not os.path.exists(clusterdir):
        pprint("Cluster directory %s not found..." % clusterdir, color='red')
        sys.exit(1)
    if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    client = config.client
    k = config.k
    pprint("Scaling on client %s" % client, color='blue')
    image = k.info("%s-master-0" % cluster).get('image')
    if image is None:
        pprint("Missing image...", color='red')
        sys.exit(1)
    else:
        pprint("Using image %s" % image, color='blue')
    data['image'] = image
    data['ubuntu'] = True if 'ubuntu' in image.lower() or [entry for entry in UBUNTUS if entry in image] else False
    os.chdir(os.path.expanduser("~/.kcli"))
    for role in ['masters', 'workers']:
        overrides = data.copy()
        if overrides.get(role, 0) == 0:
            continue
        config.plan(plan, inputfile='%s/%s.yml' % (plandir, role), overrides=overrides)


def create(config, plandir, cluster, overrides):
    platform = config.type
    k = config.k
    data = {'kubetype': 'generic', 'xip': False, 'domain': 'karmalabs.com'}
    data.update(overrides)
    if 'keys' not in overrides and not os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub"))\
            and not os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub"))\
            and not os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub"))\
            and not os.path.exists(os.path.expanduser("~/.kcli/id_dsa.pub")):
        pprint("No usable public key found, which is required for the deployment", color='red')
        os._exit(1)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    masters = data.get('masters', 1)
    if masters == 0:
        pprint("Invalid number of masters", color='red')
        os._exit(1)
    network = data.get('network', 'default')
    xip = data['xip']
    api_ip = data.get('api_ip')
    if platform in cloudplatforms:
        domain = data.get('domain', 'karmalabs.com')
        api_ip = "%s-master.%s" % (cluster, domain)
    elif api_ip is None:
        if network == 'default' and platform == 'kvm':
            pprint("Using 192.168.122.253 as api_ip", color='yellow')
            data['api_ip'] = "192.168.122.253"
            api_ip = "192.168.122.253"
        else:
            pprint("You need to define api_ip in your parameters file", color='red')
            os._exit(1)
    if xip and platform not in cloudplatforms:
        data['domain'] = "%s.xip.io" % api_ip
    if data.get('virtual_router_id') is None:
        data['virtual_router_id'] = word2number(data['cluster'])
    pprint("Using keepalived virtual_router_id %s" % data['virtual_router_id'], color='blue')
    version = data.get('version')
    if version is not None and not version.startswith('1.'):
        pprint("Invalid version %s" % version, color='red')
        os._exit(1)
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    image = data.get('image', 'centos7')
    data['ubuntu'] = True if 'ubuntu' in image.lower() or [entry for entry in UBUNTUS if entry in image] else False
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    firstmaster = "%s-master-0" % cluster
    if os.path.exists(clusterdir):
        pprint("Please remove existing directory %s first..." % clusterdir, color='red')
        sys.exit(1)
    if find_executable('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir("%s/auth" % clusterdir)
        with open("%s/kcli_parameters.yml" % clusterdir, 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    result = config.plan(plan, inputfile='%s/masters.yml' % plandir, overrides=data, wait=True)
    if result['result'] != "success":
        os._exit(1)
    source, destination = "/root/join.sh", "%s/join.sh" % clusterdir
    firstmasterip = k.info(firstmaster)['ip']
    scpcmd = scp(firstmaster, ip=firstmasterip, user='root', source=source, destination=destination,
                 tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                 tunneluser=config.tunneluser, download=True, insecure=True)
    os.system(scpcmd)
    source, destination = "/etc/kubernetes/admin.conf", "%s/auth/kubeconfig" % clusterdir
    scpcmd = scp(firstmaster, ip=firstmasterip, user='root', source=source, destination=destination,
                 tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                 tunneluser=config.tunneluser, download=True, insecure=True)
    os.system(scpcmd)
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers", color='blue')
        if 'name' in data:
            del data['name']
        os.chdir(os.path.expanduser("~/.kcli"))
        config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=data)
    pprint("Kubernetes cluster %s deployed!!!" % cluster)
    masters = data.get('masters', 1)
    info("export KUBECONFIG=$HOME/.kcli/clusters/%s/auth/kubeconfig" % cluster)
    info("export PATH=$PWD:$PATH")
    prefile = 'pre_ubuntu.sh' if data['ubuntu'] else 'pre_el.sh'
    predata = config.process_inputfile(plan, "%s/%s" % (plandir, prefile), overrides=data)
    with open("%s/pre.sh" % clusterdir, 'w') as f:
        f.write(predata)
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    apps = data.get('apps', [])
    if apps:
        for app in apps:
            appdir = "%s/apps/%s" % (plandir, app)
            if not os.path.exists(appdir):
                pprint("Skipping unsupported app %s" % app, color='yellow')
            else:
                pprint("Adding app %s" % app, color='blue')
                if '%s_version' % app not in overrides:
                    data['%s_version' % app] = 'latest'
                kube_create_app(config, appdir, overrides=data)
