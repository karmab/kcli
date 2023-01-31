#!/usr/bin/env python
# coding=utf-8

from ast import literal_eval
import socket
from urllib.request import urlretrieve, urlopen
import os
from subprocess import call
from shutil import move
import sys
import yaml

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip', 'ks']


def url_exists(url):
    try:
        urlopen(url)
        return True
    except:
        return False


def fetch(url, path):
    if 'raw.githubusercontent.com' not in url:
        url = url.replace('github.com', 'raw.githubusercontent.com').replace('blob/main', 'main')
    shortname = os.path.basename(url)
    if not os.path.exists(path):
        os.mkdir(path)
    urlretrieve(url, "%s/%s" % (path, shortname))


def get_free_port():
    """

    :return:
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def pprint(text):
    color = '36'
    print('\033[%sm%s\033[0m' % (color, text))


def error(text):
    color = '31'
    print('\033[%sm%s\033[0m' % (color, text))


def success(text):
    color = '32'
    print('\033[%sm%s\033[0m' % (color, text))


def warning(text):
    color = '33'
    print('\033[%sm%s\033[0m' % (color, text))


def handle_response(result, name, quiet=False, element='', action='deployed', client=None):
    """

    :param result:
    :param name:
    :param quiet:
    :param element:
    :param action:
    :param client:
    :return:
    """
    code = 0
    if not isinstance(result, dict):
        result = {'result': result.result, 'reason': result.reason}
    if result['result'] == 'success':
        if not quiet:
            response = "%s %s %s" % (element, name, action)
            if client is not None:
                response += " on %s" % client
            success(response.lstrip())
    elif result['result'] == 'failure':
        if not quiet:
            response = "%s %s not %s because %s" % (element, name, action, result['reason'])
            error(response.lstrip())
        code = 1
    return code


def confirm(message):
    """

    :param message:
    :return:
    """
    message = "%s [y/N]: " % message
    _input = input(message)
    if _input.lower() not in ['y', 'yes']:
        error("Leaving...")
        sys.exit(1)
    return


def get_overrides(paramfile=None, param=[]):
    """

    :param paramfile:
    :param param:
    :return:
    """
    overrides = {}
    if paramfile is not None and os.path.exists(os.path.expanduser(paramfile)):
        with open(os.path.expanduser(paramfile)) as f:
            try:
                overrides = yaml.safe_load(f)
            except:
                error("Couldn't parse your parameters file %s. Not using it" % paramfile)
                sys.exit(1)
    if param is not None:
        for x in param:
            if len(x.split('=')) < 2:
                continue
            else:
                if len(x.split('=')) == 2:
                    key, value = x.split('=')
                else:
                    split = x.split('=')
                    key = split[0]
                    value = x.replace("%s=" % key, '')
                if value.isdigit():
                    value = int(value)
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value == '[]':
                    value = []
                elif value.startswith('[') and value.endswith(']'):
                    if '{' in value:
                        value = literal_eval(value)
                    else:
                        value = value[1:-1].split(',')
                        for index, v in enumerate(value):
                            v = v.strip()
                            value[index] = v
                overrides[key] = value
    return overrides


def print_info(yamlinfo, output='plain', fields=[], values=False, pretty=True):
    """

    :param yamlinfo:
    :param output:
    :param fields:
    :param values:
    """
    if fields:
        for key in list(yamlinfo):
            if key not in fields:
                del yamlinfo[key]
    if output == 'yaml':
        if pretty:
            return yaml.dump(yamlinfo, default_flow_style=False, indent=2, allow_unicode=True,
                             encoding=None).replace("'", '')[:-1]
        else:
            return yamlinfo
    else:
        result = ''
        orderedfields = ['debug', 'name', 'project', 'namespace', 'id', 'instanceid', 'creationdate', 'owner', 'host',
                         'status', 'description', 'autostart', 'image', 'user', 'plan', 'profile', 'flavor', 'cpus',
                         'memory', 'nets', 'ip', 'disks', 'snapshots']
        otherfields = [key for key in yamlinfo if key not in orderedfields]
        for key in orderedfields + sorted(otherfields):
            if key not in yamlinfo or (fields and key not in fields):
                continue
            else:
                value = yamlinfo[key]
                if key == 'nets':
                    nets = ''
                    for net in value:
                        device = net['device']
                        mac = net['mac']
                        network = net['net']
                        network_type = net['type']
                        nets += "net interface: %s mac: %s net: %s type: %s\n" % (device, mac, network,
                                                                                  network_type)
                    value = nets.rstrip()
                elif key == 'disks':
                    disks = ''
                    for disk in value:
                        device = disk['device']
                        disksize = disk['size']
                        unit = 'GB' if str(disksize).isdigit() else ''
                        diskformat = disk['format']
                        drivertype = disk['type']
                        path = disk['path']
                        disks += "diskname: %s disksize: %s%s diskformat: %s type: %s path: %s\n" % (device,
                                                                                                     disksize,
                                                                                                     unit,
                                                                                                     diskformat,
                                                                                                     drivertype,
                                                                                                     path)
                    value = disks.rstrip()
                elif key == 'snapshots':
                    snaps = ''
                    for snap in value:
                        snapshot = snap['snapshot']
                        current = snap['current']
                        snaps += "snapshot: %s current: %s\n" % (snapshot, current)
                    value = snaps.rstrip()
                if values or key in ['disks', 'nets']:
                    result += "%s\n" % value
                else:
                    result += "%s: %s\n" % (key, value)
        return result.rstrip()


def get_kubectl():
    SYSTEM = 'darwin' if os.path.exists('/Users') else 'linux'
    r = urlopen("https://storage.googleapis.com/kubernetes-release/release/stable.txt")
    version = str(r.read(), 'utf-8').strip()
    kubecmd = "curl -LO https://storage.googleapis.com/kubernetes-release/release/%s/bin/%s/amd64/kubectl" % (version,
                                                                                                              SYSTEM)
    kubecmd += "; chmod 700 kubectl"
    call(kubecmd, shell=True)


def get_oc(macosx=False):
    SYSTEM = 'macosx' if os.path.exists('/Users') else 'linux'
    pprint("Downloading oc in current directory")
    occmd = "curl -s https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/%s/oc.tar.gz" % SYSTEM
    occmd += "| tar zxf - oc"
    occmd += "; chmod 700 oc"
    call(occmd, shell=True)
    if os.path.exists('/i_am_a_container'):
        if macosx:
            occmd = "curl -s https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/macosx/oc.tar.gz"
            occmd += "| tar zxf -C /workdir - oc"
            occmd += "; chmod 700 /workdir/oc"
            call(occmd, shell=True)
        else:
            move('oc', '/workdir/oc')


def container_mode():
    return True if os.path.exists("/i_am_a_container") and os.path.exists('/workdir') else False
