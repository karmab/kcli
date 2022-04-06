from base64 import b64encode
from glob import glob
from ipaddress import ip_address, ip_network
import os
from distutils.version import LooseVersion
import requests
import sys
import yaml


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


def stable_release(release, tag_mode=False):
    name = 'name' if tag_mode else 'tag_name'
    tag = release[name]
    if 'rc' in tag or 'alpha' in tag or 'beta' in tag:
        return False
    if 'prerelease' in release and release['prerelease']:
        return False
    return True


def github_version(repo, version=None, tag_mode=False):
    if version is None or version == 'latest':
        obj = 'tags' if tag_mode else 'releases'
        tag_name = 'name' if tag_mode else 'tag_name'
        data = requests.get("https://api.github.com/repos/%s/%s" % (repo, obj)).json()
        if 'message' in data and data['message'] == 'Not Found':
            return ''
        tags = sorted([x[tag_name] for x in data if stable_release(x, tag_mode)], key=LooseVersion, reverse=True)
        if tags:
            tag = tags[0]
        else:
            tag = data[0][tag_name]
        print('\033[0;36mUsing version %s %s\033[0;0m' % (os.path.basename(repo), tag))
        return tag


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


def local_ip(net, wrap=False):
    c = "ip a s %s 2>/dev/null | egrep 'inet6?[[:space:]][^fe]' | head -1 | awk '{print $2}' | cut -d '/' -f 1" % net
    result = os.popen(c).read().strip()
    if result == '' and net == 'default':
        c = "ip a s virbr0 2>/dev/null | egrep 'inet6?[[:space:]][^fe]' | head -1 | awk '{print $2}' | cut -d '/' -f 1"
        result = os.popen(c).read().strip()
    if wrap and ':' in result:
        result = '[%s]' % result
    return result


def network_ip(network, num=0, version=False):
    try:
        ip = str(ip_network(network)[num])
        if version and ':' in network:
            return "[%s]" % ip
        else:
            return ip
    except Exception as e:
        print("Error processing filter network_ip with %s and %s. Got %s" % (network, num, e))
        sys.exit(1)


def kcli_info(name, key=None):
    if key is not None:
        c = "kcli info vm -vf %s %s" % (key, name)
        result = os.popen(c).read().strip()
    else:
        c = "kcli info vm -o yaml %s" % name
        result = yaml.load(os.popen(c).read())
    return result


def find_manifests(directory, suffix='yaml'):
    results = []
    for f in glob("%s/*.y*ml" % directory):
        results.append(os.path.basename(f))
    return results


def exists(name):
    if name is None:
        return False
    return True if os.path.exists(name) else False


def ipv6_wrap(name):
    try:
        if ip_address(name).version == 6:
            return f'[{name}]'
        else:
            return name
    except:
        return name


jinjafilters = {'basename': basename, 'dirname': dirname, 'ocpnodes': ocpnodes, 'none': none, 'type': _type,
                'certificate': certificate, 'base64': base64, 'github_version': github_version,
                'defaultnodes': defaultnodes, 'waitcrd': waitcrd, 'local_ip': local_ip, 'network_ip': network_ip,
                'kcli_info': kcli_info, 'find_manifests': find_manifests, 'exists': exists, 'ipv6_wrap': ipv6_wrap}


class FilterModule(object):
    def filters(self):
        return jinjafilters
