#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import info, pprint, pwd_path, get_kubectl
import os
import sys


def scale(config, plandir, cluster, overrides):
    data = {'cluster': cluster}
    data.update(overrides)
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
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
    config.plan(cluster, inputfile='%s/workers.yml' % plandir, overrides=data)


def create(config, plandir, cluster, overrides):
    data = {'kubetype': 'k3s'}
    data.update(overrides)
    data['cluster'] = overrides['cluster'] if 'cluster' in overrides else cluster
    data['kube'] = data['cluster']
    masters = data.get('masters', 1)
    if masters != 1:
        pprint("Invalid number of masters", color='red')
        os._exit(1)
    version = data.get('version')
    if version is not None and not version.startswith('1.'):
        pprint("Invalid version %s" % version, color='red')
        os._exit(1)
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    clusterdir = pwd_path("clusters/%s" % cluster)
    firstmaster = "%s-master-0" % cluster
    if os.path.exists(clusterdir):
        pprint("Please remove existing directory %s first..." % clusterdir, color='red')
        sys.exit(1)
    if find_executable('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir("%s/auth" % clusterdir)
    k = config.k
    result = config.plan(cluster, inputfile='%s/masters.yml' % plandir, overrides=data, wait=True)
    if result['result'] != "success":
        os._exit(1)
    source, destination = "/root/join.sh", "%s/join.sh" % clusterdir
    scpcmd = k.scp(firstmaster, user='root', source=source, destination=destination, tunnel=config.tunnel,
                   tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                   download=True, insecure=True)
    os.system(scpcmd)
    source, destination = "/root/kubeconfig", "%s/auth/kubeconfig" % clusterdir
    scpcmd = k.scp(firstmaster, user='root', source=source, destination=destination, tunnel=config.tunnel,
                   tunnelhost=config.tunnelhost, tunnelport=config.tunnelport, tunneluser=config.tunneluser,
                   download=True, insecure=True)
    os.system(scpcmd)
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers", color='blue')
        if 'name' in data:
            del data['name']
        config.plan(cluster, inputfile='%s/workers.yml' % plandir, overrides=data)
    pprint("K3s cluster %s deployed!!!" % cluster)
    info("export KUBECONFIG=clusters/%s/auth/kubeconfig" % cluster)
    info("export PATH=$PWD:$PATH")
