from base64 import b64encode
from glob import glob
from ipaddress import ip_address, ip_network
import json
import os
import re
import sys
from urllib.request import urlopen
from time import sleep
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


def ocpnodes(cluster, platform, ctlplanes, workers):
    ctlplanes = ['%s-ctlplane-%d' % (cluster, num) for num in range(ctlplanes)]
    workers = ['%s-worker-%d' % (cluster, num) for num in range(workers)]
    if platform in ['kubevirt', 'openstack', 'vsphere', 'packet']:
        return ["%s-bootstrap-helper" % cluster] + ["%s-bootstrap" % cluster] + ctlplanes + workers
    else:
        return ["%s-bootstrap" % cluster] + ctlplanes + workers


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
        data = json.loads(urlopen(f"https://api.github.com/repos/{repo}/{obj}", timeout=5).read())
        if 'message' in data and data['message'] == 'Not Found':
            return ''
        tags = sorted([x[tag_name] for x in data if stable_release(x, tag_mode)],
                      key=lambda string: list(map(int, re.findall(r'\d+', string)))[0], reverse=True)
        if tags:
            tag = tags[0]
        else:
            tag = data[0][tag_name]
        print('\033[0;36mUsing version %s %s\033[0;0m' % (os.path.basename(repo), tag))
        return tag


def defaultnodes(replicas, cluster, domain, ctlplanes, workers):
    nodes = []
    for num in range(workers):
        if len(nodes) < replicas:
            nodes.append(f'{cluster}-worker-{num}.{domain}')
    for num in range(ctlplanes):
        if len(nodes) < replicas:
            nodes.append(f'{cluster}-ctlplane-{num}.{domain}')
    return nodes


def wait_crd(crd, timeout=120):
    result = """timeout=0
ready=false
while [ "$timeout" -lt "%s" ] ; do
  oc get crd | grep -q %s && ready=true && break;
  echo "Waiting for CRD %s to be created"
  sleep 5
  timeout=$(($timeout + 5))
done
if [ "$ready" == "false" ] ; then
 echo Timeout waiting for CRD %s
 exit 1
fi """ % (timeout, crd.lower(), crd, crd)
    return result


def wait_csv(csv, namespace, timeout=360):
    result = """timeout=0
ready=false
while [ "$timeout" -lt "%s" ] ; do
  [ "$(oc get csv -n %s %s -o jsonpath='{.status.phase}')" == "Succeeded" ] && ready=true && break;
  echo "Waiting for CSV %s to be created"
  sleep 5
  timeout=$(($timeout + 5))
done
if [ "$ready" == "false" ] ; then
 echo Timeout waiting for CSV %s
 exit 1
fi """ % (timeout, namespace, csv, csv, csv)
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


def kcli_info(name, key=None, client=None, wait=False):
    client_header = f'-C {client}' if client is not None else ''
    if key is not None:
        c = f"kcli {client_header} info vm -vf {key} {name}"
        result = os.popen(c).read().strip()
    else:
        c = f"kcli {client_header} info vm -o yaml {name}"
        result = yaml.load(os.popen(c).read())
    if result == '' and wait:
        sleep(10)
        print(f"Waiting 10s for info to be available on {name}")
        return kcli_info(name, key=key, client=client, wait=wait)
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


def has_ctlplane(_list):
    for entry in _list:
        if 'ctlplane' in entry or 'master' in entry:
            return True
    return False


def count(string, char):
    return string.count(char)


def pwd_path(path):
    if path is not None and not os.path.isabs(path) and os.path.exists("/i_am_a_container")\
       and os.path.exists('/workdir'):
        return f'/workdir/{path}'
    else:
        return path


jinjafilters = {'basename': basename, 'dirname': dirname, 'ocpnodes': ocpnodes, 'none': none, 'type': _type,
                'certificate': certificate, 'base64': base64, 'github_version': github_version,
                'defaultnodes': defaultnodes, 'wait_crd': wait_crd, 'local_ip': local_ip, 'network_ip': network_ip,
                'kcli_info': kcli_info, 'find_manifests': find_manifests, 'exists': exists, 'ipv6_wrap': ipv6_wrap,
                'has_ctlplane': has_ctlplane, 'wait_csv': wait_csv, 'count': count, 'pwd_path': pwd_path}


class FilterModule(object):
    def filters(self):
        return jinjafilters
