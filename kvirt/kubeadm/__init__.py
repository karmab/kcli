#!/usr/bin/env python

from distutils.spawn import find_executable
from kvirt.common import info, pprint, pwd_path, get_kubectl, kube_create_app, scp
from kvirt.defaults import UBUNTUS
import os
import sys

# virtplatforms = ['kvm', 'kubevirt', 'ovirt', 'openstack', 'vsphere', 'packet']
cloudplatforms = ['aws', 'gcp']


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
    platform = config.type
    data = {'kubetype': 'generic', 'xip': False}
    data.update(overrides)
    xip = data['xip']
    data['cluster'] = overrides['cluster'] if 'cluster' in overrides else cluster
    data['kube'] = data['cluster']
    masters = data.get('masters', 1)
    if masters == 0:
        pprint("Invalid number of masters", color='red')
        os._exit(1)
    network = data.get('network', 'default')
    api_ip = data.get('api_ip')
    if masters > 1:
        if platform in cloudplatforms:
            domain = data.get('domain', 'karmalabs.com')
            api_ip = "%s-master.%s" % (cluster, domain)
        elif api_ip is None:
            if network == 'default' and platform == 'kvm':
                pprint("Using 192.168.122.253 as api_ip", color='yellow')
                data['api_ip'] = "192.168.122.253"
            else:
                pprint("You need to define api_ip in your parameters file", color='red')
                os._exit(1)
    if xip:
        data['domain'] = "%s.xip.io" % api_ip
    version = data.get('version')
    if version is not None and not version.startswith('1.'):
        pprint("Invalid version %s" % version, color='red')
        os._exit(1)
    data['basedir'] = '/workdir' if os.path.exists("/i_am_a_container") else '.'
    cluster = data.get('cluster')
    image = data.get('image', 'centos7')
    data['ubuntu'] = True if image in UBUNTUS or 'ubuntu' in image.lower() else False
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
        config.plan(cluster, inputfile='%s/workers.yml' % plandir, overrides=data)
    pprint("Kubernetes cluster %s deployed!!!" % cluster)
    masters = data.get('masters', 1)
    info("export KUBECONFIG=clusters/%s/auth/kubeconfig" % cluster)
    info("export PATH=$PWD:$PATH")
    prefile = 'pre_ubuntu.sh' if data['ubuntu'] else 'pre_el.sh'
    predata = config.process_inputfile(cluster, "%s/%s" % (plandir, prefile), overrides=data)
    with open("%s/pre.sh" % clusterdir, 'w') as f:
        f.write(predata)
    os.environ['KUBECONFIG'] = "%s/%s/auth/kubeconfig" % (os.getcwd(), clusterdir)
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
