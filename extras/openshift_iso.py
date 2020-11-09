#!/usr/bin/env python3
import argparse
from distutils.spawn import find_executable
from kvirt.config import Kconfig
from kvirt.common import pprint, insecure_fetch
from kvirt import openshift
import os
import socket
from subprocess import call
from time import sleep


curl_header = "Accept: application/vnd.coreos.ignition+json; version=3.1.0"
liveiso = "https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/latest/latest/rhcos-live.x86_64.iso"


def process(args):
    api_ip = args.api_ip
    iso = args.iso
    cluster = args.cluster
    domain = args.domain
    if api_ip is None:
        try:
            api_ip = socket.gethostbyname('api.%s.%s' % (cluster, domain))
        except:
            pprint("Couldn't figure out api_ip, indicate it explicitely", color='red')
            os._exit(1)
    role = args.role
    ignitionfile = "%s.ign" % role
    path = args.path
    config = Kconfig()
    plandir = os.path.dirname(openshift.create.__code__.co_filename)
    if os.path.exists(ignitionfile):
        pprint("Using existing %s" % ignitionfile, color='yellow')
        os.remove(ignitionfile)
    while not os.path.exists(ignitionfile) or os.stat(ignitionfile).st_size == 0:
        try:
            with open(ignitionfile, 'w') as w:
                ignitiondata = insecure_fetch("https://api.%s.%s:22623/config/master" % (cluster, domain),
                                              headers=[curl_header])
                w.write(ignitiondata)
                pprint("Downloaded %s ignition data" % role, color='green')
        except:
            pprint("Waiting 5s before retrieving %s ignition data" % role, color='blue')
            sleep(5)
    iso_overrides = {'scripts': ['%s/iso.sh' % plandir]}
    hostscontent = "127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n"
    hostscontent += "::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n"
    hostscontent += "%s api-int.%s.%s" % (api_ip, cluster, domain)
    with open("iso.ign", 'w') as f:
        pprint("Writing file iso.ign for %s in %s.%s" % (role, cluster, domain), color='green')
        iso_overrides['files'] = [{"path": "/root/config.ign", "origin": "%s/%s.ign" % (path, role)},
                                  {"path": "/etc/hosts", "content": hostscontent}]
        f.write(config.create_vm('autoinstaller', 'rhcos46', overrides=iso_overrides, onlyassets=True))
    if iso:
        if not os.path.exists('rhcos-live.x86_64.iso'):
            pprint("Downloading rhcos-live.x86_64.iso", color='blue')
            download = "curl %s > rhcos-live.x86_64.iso" % liveiso
            call(download, shell=True)
        engine = 'podman' if find_executable('podman') else 'docker'
        coreosinstaller = "%s run --privileged --rm -w /data -v $PWD:/data -v /dev:/dev" % engine
        if not os.path.exists('/Users'):
            coreosinstaller += " -v /run/udev:/run/udev"
        coreosinstaller += " quay.io/coreos/coreos-installer:release"
        embedcmd = "%s iso ignition embed -fi iso.ign rhcos-live.x86_64.iso" % coreosinstaller
        os.popen(embedcmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an openshift ignition iso for baremetal install")
    parser.add_argument('-a', '--api_ip', metavar='API_IP', help='Api vip from where to get assets')
    parser.add_argument('-d', '--domain', metavar='DOMAIN', default='karmalabs.com', required=True,
                        help='Domain. Defaults to karmalabs.com')
    parser.add_argument('-i', '--iso', action='store_true', help='Create iso')
    parser.add_argument('-p', '--path', metavar='PATH', default='.', help='Where to download asset')
    parser.add_argument('-r', '--role', metavar='ROLE', default='master', choices=['master', 'worker'],
                        help='Role. Defaults to master')
    parser.add_argument('cluster', metavar='CLUSTER', help='Cluster')
    args = parser.parse_args()
    process(args)
