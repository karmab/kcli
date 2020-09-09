#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import info, pprint, get_kubectl, scp
import os
import sys
import yaml

cloudplatforms = ['aws', 'gcp']


def scale(config, plandir, cluster, overrides):
    plan = cluster
    data = {'cluster': cluster, 'kube': cluster, 'kubetype': 'k3s'}
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
    image = k.info("%s-ctlplane-0" % cluster).get('image')
    if image is None:
        pprint("Missing image...", color='red')
        sys.exit(1)
    else:
        pprint("Using image %s" % image, color='blue')
    data['image'] = image
    os.chdir(os.path.expanduser("~/.kcli"))
    config.plan(plan, inputfile='%s/workers.yml' % plandir, overrides=data)


def create(config, plandir, cluster, overrides):
    platform = config.type
    data = {'kubetype': 'k3s'}
    data.update(overrides)
    data['cluster'] = overrides.get('cluster', cluster if cluster is not None else 'testk')
    plan = cluster if cluster is not None else data['cluster']
    data['kube'] = data['cluster']
    ctlplanes = data.get('ctlplanes', 1)
    network = data.get('network', 'default')
    api_ip = data.get('api_ip')
    if ctlplanes > 1:
        if platform in cloudplatforms:
            domain = data.get('domain', 'karmalabs.com')
            api_ip = "%s-ctlplane.%s" % (cluster, domain)
        elif api_ip is None:
            if network == 'default' and platform == 'kvm':
                pprint("Using 192.168.122.253 as api_ip", color='yellow')
                data['api_ip'] = "192.168.122.253"
            else:
                pprint("You need to define api_ip in your parameters file", color='red')
                os._exit(1)
    version = data.get('version')
    if version is not None and not version.startswith('1.'):
        pprint("Invalid version %s" % version, color='red')
        os._exit(1)
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    firstctlplane = "%s-ctlplane-0" % cluster
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
    if ctlplanes > 1:
        datastore_endpoint = data.get('datastore_endpoint')
        if datastore_endpoint is None:
            result = config.plan(plan, inputfile='%s/datastore.yml' % plandir, overrides=data, wait=True)
            if result['result'] != "success":
                os._exit(1)
            datastore_type = data['datastore_type']
            datastore_user = data['datastore_user']
            datastore_password = data['datastore_password']
            datastore_ip = config.k.info("%s-datastore" % cluster).get('ip')
            datastore_name = data['datastore_name']
            if datastore_type == 'mysql':
                datastore_name = "tcp(%s)" % datastore_name
            datastore_endpoint = "%s://%s:%s@%s/%s" % (datastore_type, datastore_user, datastore_password,
                                                       datastore_ip, datastore_name)
        data['datastore_endpoint'] = datastore_endpoint
    k = config.k
    result = config.plan(cluster, inputfile='%s/ctlplanes.yml' % plandir, overrides=data, wait=True)
    if result['result'] != "success":
        os._exit(1)
    source, destination = "/root/join.sh", "%s/join.sh" % clusterdir
    firstctlplaneip = k.info(firstctlplane)['ip']
    scpcmd = scp(firstctlplane, ip=firstctlplaneip, user='root', source=source, destination=destination,
                 tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                 tunneluser=config.tunneluser, download=True, insecure=True)
    os.system(scpcmd)
    source, destination = "/root/kubeconfig", "%s/auth/kubeconfig" % clusterdir
    scpcmd = scp(firstctlplane, ip=firstctlplaneip, user='root', source=source, destination=destination,
                 tunnel=config.tunnel, tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                 tunneluser=config.tunneluser, download=True, insecure=True)
    os.system(scpcmd)
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers", color='blue')
        if 'name' in data:
            del data['name']
        os.chdir(os.path.expanduser("~/.kcli"))
        config.plan(cluster, inputfile='%s/workers.yml' % plandir, overrides=data)
    pprint("K3s cluster %s deployed!!!" % cluster)
    info("export KUBECONFIG=clusters/%s/auth/kubeconfig" % cluster)
    info("export PATH=$PWD:$PATH")
