#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import pprint, pwd_path
import os
import sys
from subprocess import call
from urllib.request import urlopen


def get_kubectl():
    SYSTEM = 'darwin' if os.path.exists('/Users') else 'linux'
    r = urlopen("https://storage.googleapis.com/kubernetes-release/release/stable.txt")
    version = str(r.read(), 'utf-8').strip()
    kubecmd = "curl -LO https://storage.googleapis.com/kubernetes-release/release/%s/bin/%s/amd64/kubectl" % (version,
                                                                                                              SYSTEM)
    kubecmd += "| tar zxf - kubectl"
    kubecmd += "; chmod 700 kubectl"
    call(kubecmd, shell=True)


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
        pprint("Missing image...", color='blue')
        sys.exit(1)
    else:
        pprint("Using image %s" % image, color='blue')
    data['image'] = image
    config.plan(cluster, inputfile='%s/workers.yml' % plandir, overrides=data)


def create(config, plandir, cluster, overrides):
    data = {'cluster': cluster}
    data.update(overrides)
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    clusterdir = pwd_path("clusters/%s" % cluster)
    firstmaster = "%s-master-0" % cluster
    if os.path.exists(clusterdir):
        pprint("Please Remove existing %s first..." % clusterdir, color='red')
        sys.exit(1)
    if find_executable('kubectl') is None:
        get_kubectl()
    if not os.path.exists(clusterdir):
        os.makedirs(clusterdir)
        os.mkdir("%s/auth" % clusterdir)
    k = config.k
    config.plan(cluster, inputfile='%s/masters.yml' % plandir, overrides=data, wait=True)
    source, destination = "/root/join.sh", "%s/join.sh" % clusterdir
    scpcmd = k.scp(firstmaster, user='root', source=source, destination=destination, tunnel=config.tunnel,
                   download=True, insecure=True)
    os.system(scpcmd)
    source, destination = "/etc/kubernetes/admin.conf", "%s/auth/kubeconfig" % clusterdir
    scpcmd = k.scp(firstmaster, user='root', source=source, destination=destination, tunnel=config.tunnel,
                   download=True, insecure=True)
    os.system(scpcmd)
    workers = data.get('workers', 0)
    if workers > 0:
        pprint("Deploying workers", color='blue')
        if 'name' in data:
            del data['name']
        config.plan(cluster, inputfile='%s/workers.yml' % plandir, overrides=data)
    pprint("Kubernetes cluster %s deployed!!!" % cluster,)
    pprint("Use The following command to interact with this cluster")
    pprint("export KUBECONFIG=clusters/%s/auth/kubeconfig" % cluster)
