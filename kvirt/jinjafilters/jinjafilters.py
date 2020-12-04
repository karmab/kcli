from base64 import b64encode
import os
from distutils.version import LooseVersion
from netaddr import IPNetwork
import requests


def basename(path):
    return os.path.basename(path)


def dirname(path):
    return os.path.dirname(path)


def none(value):
    return value if value is not None else ''


def base64(value):
    if value is None:
        return None
    return str(b64encode(value.encode('utf-8')), 'utf-8')


def _type(value):
    if value is None:
        return None
    elif isinstance(value, str):
        return 'string'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, dict):
        return 'dict'
    elif isinstance(value, list):
        return 'list'


def ocpnodes(cluster, platform, masters, workers):
    masters = ['%s-master-%d' % (cluster, num) for num in range(masters)]
    workers = ['%s-worker-%d' % (cluster, num) for num in range(workers)]
    if platform in ['kubevirt', 'openstack', 'vsphere', 'packet']:
        return ["%s-bootstrap-helper" % cluster] + ["%s-bootstrap" % cluster] + masters + workers
    else:
        return ["%s-bootstrap" % cluster] + masters + workers


def certificate(value):
    if 'BEGIN CERTIFICATE' in value:
        return value
    else:
        return "-----BEGIN CERTIFICATE-----\n%s\n-----END CERTIFICATE-----" % value


def githubversion(repo, version=None):
    if version is None or version == 'latest':
        data = requests.get("https://api.github.com/repos/%s/releases" % repo).json()
        if 'message' in data and data['message'] == 'Not Found':
            return ''
        tags = sorted([x['tag_name'] for x in data], key=LooseVersion, reverse=True)
        for tag in tags:
            if 'rc' not in tag and 'alpha' not in tag and 'beta' not in tag:
                print('\033[0;36mUsing version %s\033[0;0m' % tag)
                return tag
        return tags[0]


def defaultnodes(replicas, cluster, domain, masters, workers):
    nodes = []
    for num in range(workers):
        if len(nodes) < replicas:
            nodes.append('%s-worker-%d.%s' % (cluster, num, domain))
    for num in range(masters):
        if len(nodes) < replicas:
            nodes.append('%s-master-%d.%s' % (cluster, num, domain))
    return nodes


def waitcrd(crd, timeout=60):
    result = """timeout=0
ready=false
while [ "$timeout" -lt "%s" ] ; do
  oc get crd | grep -q %s && ready=true && break;
  echo "Waiting for CRD %s to be created"
  sleep 5
  timeout=$(($timeout + 5))
done
if [ "$ready" == "false" ] ; then
 echo timeout waiting for CRD %s
 exit 1
fi """ % (timeout, crd, crd, crd)
    return result


def local_ip(network):
    cmd = """ip a s %s 2>/dev/null | grep 'inet[[:space:]]' | tail -1 | awk '{print $2}' | cut -d "/" -f 1""" % network
    return os.popen(cmd).read().strip()


def network_ip(network, num=0, version=False):
    try:
        ip = IPNetwork(network)[num]
        if version and ':' in network:
            return "[%s]" % ip
        else:
            return ip
    except Exception as e:
        print("Error processing filter network_ip with %s and %s. Got %s" % (network, num, e))
        os._exit(1)


jinjafilters = {'basename': basename, 'dirname': dirname, 'ocpnodes': ocpnodes, 'none': none, 'type': _type,
                'certificate': certificate, 'base64': base64, 'githubversion': githubversion,
                'defaultnodes': defaultnodes, 'waitcrd': waitcrd, 'local_ip': local_ip, 'network_ip': network_ip}


class FilterModule(object):
    def filters(self):
        return jinjafilters
