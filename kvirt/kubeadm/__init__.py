#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import success, error, pprint, warning, info2, container_mode
from kvirt.common import get_kubectl, kube_create_app, get_ssh_pub_key
from kvirt.defaults import UBUNTUS
import os
import sys
import yaml

# virtplatforms = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere']
cloudplatforms = ['aws', 'gcp']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'nip': False, 'kube': cluster, 'kubetype': 'generic', 'image': 'centos8stream'}
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    with open("%s/kcli_parameters.yml" % clusterdir, 'w') as paramfile:
        yaml.safe_dump(data, paramfile)
    client = config.client
    pprint("Scaling on client %s" % client)
    image = data.get('image')
    data['ubuntu'] = True if 'ubuntu' in image.lower() or [entry for entry in UBUNTUS if entry in image] else False
    os.chdir(os.path.expanduser("~/.kcli"))
    for role in ['masters', 'workers']:
        overrides = data.copy()
        if overrides.get(role, 0) == 0:
            continue
        threaded = data.get('threaded', False) or data.get(f'{role}_threaded', False)
        config.plan(plan, inputfile='%s/%s.yml' % (plandir, role), overrides=overrides, threaded=threaded)


def create(config, plandir, cluster, overrides):
    platform = config.type
    k = config.k
    data = {'kubetype': 'generic', 'nip': False, 'domain': 'karmalabs.com'}
    data.update(overrides)
    if 'keys' not in overrides and get_ssh_pub_key() is None:
        error("No usable public key found, which is required for the deployment")
        sys.exit(1)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    masters = data.get('masters', 1)
    if masters == 0:
        error("Invalid number of masters")
        sys.exit(1)
    network = data.get('network', 'default')
    nip = data['nip']
    api_ip = data.get('api_ip')
    if platform in cloudplatforms:
        domain = data.get('domain', 'karmalabs.com')
        api_ip = "%s-master.%s" % (cluster, domain)
    elif api_ip is None:
        if network == 'default' and platform == 'kvm':
            warning("Using 192.168.122.253 as api_ip")
            data['api_ip'] = "192.168.122.253"
            api_ip = "192.168.122.253"
        elif platform == 'kubevirt':
            selector = {'kcli/plan': plan, 'kcli/role': 'master'}
            service_type = "LoadBalancer" if k.access_mode == 'LoadBalancer' else 'ClusterIP'
            api_ip = config.k.create_service("%s-api" % cluster, config.k.namespace, selector, _type=service_type,
                                             ports=[6443])
            if api_ip is None:
                sys.exit(1)
            else:
                pprint("Using api_ip %s" % api_ip)
                data['api_ip'] = api_ip
        else:
            error("You need to define api_ip in your parameters file")
            sys.exit(1)
    if nip and platform not in cloudplatforms:
        data['domain'] = "%s.nip.io" % api_ip
    if data.get('virtual_router_id') is None:
        data['virtual_router_id'] = hash(data['cluster']) % 254 + 1
    pprint("Using keepalived virtual_router_id %s" % data['virtual_router_id'])
    version = data.get('version')
    if version is not None and not str(version).startswith('1.'):
        error("Invalid version %s" % version)
        sys.exit(1)
    if data.get('eksd', False) and data.get('engine', 'containerd') != 'docker':
        warning("Forcing engine to docker for eksd")
        data['engine'] = 'docker'
    data['basedir'] = '/workdir' if container_mode() else '.'
    cluster = data.get('cluster')
    image = data.get('image', 'centos8stream')
    data['ubuntu'] = True if 'ubuntu' in image.lower() or [entry for entry in UBUNTUS if entry in image] else False
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if os.path.exists(clusterdir):
        error("Please remove existing directory %s first..." % clusterdir)
        sys.exit(1)
    if find_executable('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir("%s/auth" % clusterdir)
        with open("%s/kcli_parameters.yml" % clusterdir, 'w') as p:
            installparam = overrides.copy()
            installparam['api_ip'] = api_ip
            installparam['virtual_router_id'] = data['virtual_router_id']
            installparam['plan'] = plan
            installparam['kubetype'] = 'generic'
            installparam['image'] = image
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    master_threaded = data.get('threaded', False) or data.get('masters_threaded', False)
    result = config.plan(plan, inputfile='%s/masters.yml' % plandir, overrides=data, threaded=master_threaded)
    if result['result'] != "success":
        sys.exit(1)
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers")
        if 'name' in data:
            del data['name']
        os.chdir(os.path.expanduser("~/.kcli"))
        worker_threaded = data.get('threaded', False) or data.get('workers_threaded', False)
        config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=data, threaded=worker_threaded)
    success("Kubernetes cluster %s deployed!!!" % cluster)
    masters = data.get('masters', 1)
    info2("export KUBECONFIG=$HOME/.kcli/clusters/%s/auth/kubeconfig" % cluster)
    info2("export PATH=$PWD:$PATH")
    prefile = 'pre_ubuntu.sh' if data['ubuntu'] else 'pre_el.sh'
    predata = config.process_inputfile(plan, "%s/%s" % (plandir, prefile), overrides=data)
    with open("%s/pre.sh" % clusterdir, 'w') as f:
        f.write(predata)
    os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
    apps = data.get('apps', [])
    if apps:
        os.environ["PATH"] += ":%s" % os.getcwd()
        for app in apps:
            appdir = "%s/apps/%s" % (plandir, app)
            if not os.path.exists(appdir):
                warning("Skipping unsupported app %s" % app)
            else:
                pprint("Adding app %s" % app)
                if '%s_version' % app not in overrides:
                    data['%s_version' % app] = 'latest'
                kube_create_app(config, appdir, overrides=data)
