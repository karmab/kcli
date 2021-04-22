#!/usr/bin/env python
# coding=utf-8

from ast import literal_eval
from kvirt.jinjafilters import jinjafilters
from kvirt.defaults import UBUNTUS
from random import randint
import base64
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined as undefined
from jinja2.exceptions import TemplateSyntaxError, TemplateError
from distutils.spawn import find_executable
from netaddr import IPAddress
import random
import re
import socket
import ssl
from urllib.parse import quote
from urllib.request import urlretrieve, urlopen, Request
import json
import os
from subprocess import call
from shutil import copy2, move
from tempfile import TemporaryDirectory
import yaml

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip', 'ks']
static_nic = """#!/usr/bin/env bash
if [ ! -f /etc/sysconfig/network-scripts/ifcfg-{nicname} ] ; then
echo -e \"\"\"{data}\"\"\" > /etc/sysconfig/network-scripts/ifcfg-{nicname}
systemctl restart NetworkManager
fi"""
static_nic_fcos = "{data}"

ceo_yaml = """apiVersion: operator.openshift.io/v1
kind: Etcd
metadata:
  name: cluster
  annotations:
    release.openshift.io/create-only: "true"
spec:
  managementState: Managed
  unsupportedConfigOverrides:
    useUnsupportedUnsafeNonHANonProductionUnstableEtcd: true\n"""


def url_exists(url):
    try:
        urlopen(url)
        return True
    except:
        return False


def fetch(url, path):
    if 'raw.githubusercontent.com' not in url:
        url = url.replace('github.com', 'raw.githubusercontent.com').replace('blob/master', 'master')
    elif 'master' not in url:
        if url.endswith('kcli_plan.yml'):
            url = url.replace('/kcli_plan.yml', '/master/kcli_plan.yml')
        if url.endswith('kcli_default.yml'):
            url = url.replace('/kcli_default.yml', '/master/kcli_default.yml')
    shortname = os.path.basename(url)
    if not os.path.exists(path):
        os.mkdir(path)
    urlretrieve(url, "%s/%s" % (path, shortname))


def cloudinit(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False,
              files=[], enableroot=True, overrides={}, fqdn=False, storemetadata=True, image=None, ipv6=[],
              machine='pc'):
    """

    :param name:
    :param keys:
    :param cmds:
    :param nets:
    :param gateway:
    :param dns:
    :param domain:
    :param reserveip:
    :param files:
    :param enableroot:
    :param overrides:
    :param iso:
    :param fqdn:
    """
    userdata, metadata, netdata = None, None, None
    default_gateway = gateway
    legacy = True if image is not None and (is_7(image) or is_debian9(image)) else False
    prefix = 'eth'
    if image is not None and (is_ubuntu(image) or is_debian10(image)):
        if machine == 'pc':
            prefix = 'ens'
        else:
            prefix = 'enp1s'
    dns_hack = True if image is not None and is_debian10(image) else False
    netdata = {} if not legacy else ''
    if nets:
        bridges = {}
        for index, netinfo in enumerate(nets):
            if isinstance(netinfo, str):
                net = {'name': netinfo}
            elif isinstance(netinfo, dict):
                net = netinfo.copy()
            else:
                error("Wrong net entry %s" % index)
                os._exit(1)
            if 'name' not in net:
                error("Missing name in net %s" % index)
                os._exit(1)
            netname = net['name']
            if index == 0 and 'type' in net and net.get('type') != 'virtio':
                prefix = 'ens'
            nicname = net.get('nic')
            if nicname is None:
                if prefix.startswith('ens'):
                    nicname = "%s%d" % (prefix, 3 + index)
                else:
                    nicname = "%s%d" % (prefix, index)
            ip = net.get('ip')
            netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
            noconf = net.get('noconf')
            vips = net.get('vips', [])
            enableipv6 = net.get('ipv6', False)
            bridge = net.get('bridge', False)
            bridgename = net.get('bridgename', netname)
            if bridge:
                if legacy:
                    netdata += "  auto %s\n" % nicname
                    netdata += "  iface %s inet manual\n" % nicname
                    netdata += "  auto %s\n" % bridgename
                    netdata += "  iface %s inet dhcp\n" % bridgename
                    netdata += "     bridge_ports %s\n" % nicname
                else:
                    bridges[bridgename] = {'interfaces': [nicname]}
                realnicname = nicname
                nicname = bridgename
            if legacy:
                netdata += "  auto %s\n" % nicname
            if noconf is not None:
                if legacy:
                    netdata += "  iface %s inet manual\n" % nicname
                else:
                    netdata[nicname] = {'dhcp4': False}
            elif ip is not None and netmask is not None and not reserveip:
                if legacy:
                    netdata += "  iface %s inet static\n" % nicname
                    netdata += "  address %s\n" % ip
                    netdata += "  netmask %s\n" % netmask
                else:
                    cidr = IPAddress(netmask).netmask_bits()
                    netdata[nicname] = {'dhcp4': False, 'addresses': ["%s/%s" % (ip, cidr)]}
                gateway = net.get('gateway')
                if index == 0 and default_gateway is not None:
                    if legacy:
                        netdata += "  gateway %s\n" % default_gateway
                    else:
                        netdata[nicname]['gateway4'] = default_gateway
                elif gateway is not None:
                    if legacy:
                        netdata += "  gateway %s\n" % gateway
                    else:
                        netdata[nicname]['gateway4'] = gateway
                dns = net.get('dns')
                if not legacy:
                    netdata[nicname]['nameservers'] = {}
                if dns is not None:
                    if legacy:
                        netdata += "  dns-nameservers %s\n" % dns
                    else:
                        netdata[nicname]['nameservers']['addresses'] = [dns]
                    if dns_hack:
                        dnscontent = "nameserver %s\n" % dns
                        dnsdata = {'path': 'etc/resolvconf/resolv.conf.d/base', 'content': dnscontent}
                        if files:
                            files.append(dnsdata)
                        else:
                            files = [dnsdata]
                        cmds.append('systemctl restart resolvconf')
                domain = net.get('domain')
                if domain is not None:
                    if legacy:
                        netdata += "  dns-search %s\n" % domain
                    else:
                        netdata[nicname]['addresses']['search'] = [domain]
                if not legacy and not netdata[nicname]['nameservers']:
                    del netdata[nicname]['nameservers']
                if isinstance(vips, list) and vips:
                    for index, vip in enumerate(vips):
                        if legacy:
                            netdata += "  auto %s:%s\n  iface %s:%s inet static\n  address %s\n  netmask %s\n"\
                                % (nicname, index, nicname, index, vip, netmask)
                        else:
                            netdata[nicname]['addresses'].append("%s/%s" % (vip, netmask))
            else:
                if legacy:
                    if not bridge:
                        netdata += "  iface %s inet dhcp\n" % nicname
                else:
                    targetfamily = 'dhcp6' if enableipv6 or netname in ipv6 else 'dhcp4'
                    netdata[nicname] = {targetfamily: True}
                    if 'dualstack' in overrides and index == 0:
                        dualfamily = 'dhcp6' if targetfamily == 'dhcp4' else 'dhcp4'
                        netdata[nicname][dualfamily] = True
            if bridge and not legacy:
                bridges[bridgename].update(netdata[nicname])
                del netdata[nicname]
                netdata[realnicname] = {'match': {'name': realnicname}}
    if domain is not None:
        localhostname = "%s.%s" % (name, domain)
    else:
        localhostname = name
    metadata = {"instance-id": localhostname, "local-hostname": localhostname}
    if legacy and netdata != '':
        metadata["network-interfaces"] = netdata
    metadata = json.dumps(metadata)
    if not legacy:
        if netdata or bridges:
            final_netdata = {'version': 2}
            if netdata:
                final_netdata['ethernets'] = netdata
            if bridges:
                final_netdata['bridges'] = bridges
            netdata = yaml.safe_dump(final_netdata, default_flow_style=False, encoding='utf-8').decode("utf-8")
        else:
            netdata = ''
    else:
        netdata = None
    existing = "%s.cloudinit" % name if not os.path.exists('/i_am_a_container') else "/workdir/%s.cloudinit" % name
    if os.path.exists(existing):
        pprint("using cloudinit from existing %s for %s" % (existing, name))
        userdata = open(existing).read()
    else:
        userdata = '#cloud-config\nhostname: %s\n' % name
        userdata += 'final_message: kcli boot finished, up $UPTIME seconds\n'
        if fqdn:
            fqdn = "%s.%s" % (name, domain) if domain is not None else name
            userdata += "fqdn: %s\n" % fqdn
        if enableroot:
            userdata += "ssh_pwauth: True\ndisable_root: false\n"
        if domain is not None:
            userdata += "fqdn: %s.%s\n" % (name, domain)
        if keys or os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub"))\
                or os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub"))\
                or os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub"))\
                or os.path.exists(os.path.expanduser("~/.kcli/id_dsa.pub")):
            userdata += "ssh_authorized_keys:\n"
        else:
            warning("neither id_rsa or id_dsa public keys found in your .ssh or .kcli directory, you might have "
                    "trouble accessing the vm")
        if keys:
            for key in list(set(keys)):
                userdata += "- %s\n" % key
        for path in ["~/.kcli/id_rsa.pub", "~/.kcli/id_dsa.pub", "~/.ssh/id_rsa.pub", "~/.ssh/id_dsa.pub"]:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path) and os.path.exists(expanded_path.replace('.pub', '')):
                publickeyfile = expanded_path
                with open(publickeyfile, 'r') as ssh:
                    key = ssh.read().rstrip()
                    userdata += "- %s\n" % key
                break
        if cmds:
            data = process_cmds(cmds, overrides)
            if data != '':
                userdata += "runcmd:\n"
                userdata += data
        userdata += 'ssh_pwauth: True\n'
        if storemetadata and overrides:
            storeoverrides = {k: overrides[k] for k in overrides if k not in ['password', 'rhnpassword', 'rhnak']}
            storedata = {'path': '/root/.metadata', 'content': yaml.dump(storeoverrides, default_flow_style=False,
                                                                         indent=2)}
            if files:
                files.append(storedata)
            else:
                files = [storedata]
        if files:
            data = process_files(files=files, overrides=overrides)
            if data != '':
                userdata += "write_files:\n"
                userdata += data
    return userdata.strip(), metadata, netdata


def process_files(files=[], overrides={}):
    """

    :param files:
    :param overrides:
    :return:
    """
    data = ''
    todelete = []
    for directory in files:
        if not isinstance(directory, dict) or 'origin' not in directory\
                or not os.path.isdir(os.path.expanduser(directory['origin'])):
            continue
        else:
            todelete.append(directory)
            origin_unexpanded = directory.get('origin')
            origin = os.path.expanduser(origin_unexpanded)
            path = directory.get('path')
            entries = os.listdir(origin)
            if not entries:
                files.append({'path': '%s/.k' % path, 'content': ''})
            else:
                for entry in entries:
                    if os.path.isdir(entry):
                        subentries = os.listdir(entry)
                        if not subentries:
                            files.append({'path': '%s/%s/.k' % (path, entry), 'content': ''})
                        else:
                            for subentry in subentries:
                                if os.path.isdir(subentry):
                                    continue
                                else:
                                    subpath = "%s/%s/%s" % (path, entry, subentry)
                                    subpath = subpath.replace('//', '/')
                                    files.append({'path': subpath, 'origin': "%s/%s/%s" % (origin, entry, subentry)})
                    else:
                        subpath = "%s/%s" % (path, entry)
                        subpath = subpath.replace('//', '/')
                        files.append({'path': subpath, 'origin': "%s/%s" % (origin, entry)})
    for directory in todelete:
        files.remove(directory)
    for fil in files:
        if not isinstance(fil, dict):
            continue
        origin = fil.get('origin')
        content = fil.get('content')
        path = fil.get('path')
        owner = fil.get('owner', 'root')
        mode = fil.get('mode', '0600' if not path.endswith('sh') and not path.endswith('py') else '0700')
        permissions = fil.get('permissions', mode)
        render = fil.get('render', True)
        binary = False
        if origin is not None:
            origin = os.path.expanduser(origin)
            binary = True if '.' in origin and origin.split('.')[-1].lower() in binary_types else False
            if binary:
                with open(origin, "rb") as f:
                    # content = f.read().encode("base64")
                    content = base64.b64encode(f.read())
            elif overrides and render:
                basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                env = Environment(loader=FileSystemLoader(basedir), undefined=undefined, extensions=['jinja2.ext.do'],
                                  trim_blocks=True, lstrip_blocks=True)
                for jinjafilter in jinjafilters.jinjafilters:
                    env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
                try:
                    templ = env.get_template(os.path.basename(origin))
                    fileentries = templ.render(overrides)
                except TemplateSyntaxError as e:
                    error("Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message))
                    os._exit(1)
                except TemplateError as e:
                    error("Error rendering file %s. Got: %s" % (origin, e.message))
                    os._exit(1)
                except UnicodeDecodeError as e:
                    error("Error rendering file %s. Got: %s" % (origin, e))
                    os._exit(1)
                content = [line.rstrip() for line in fileentries.split('\n')]
                # with open("/tmp/%s" % os.path.basename(path), 'w') as f:
                #     for line in fileentries.split('\n'):
                #         if line.rstrip() == '':
                #             f.write("\n")
                #         else:
                #             f.write("%s\n" % line.rstrip())
            else:
                content = [line.rstrip() for line in open(origin, 'r').readlines()]
        data += "- owner: %s:%s\n" % (owner, owner)
        data += "  path: %s\n" % path
        data += "  permissions: '%s'\n" % permissions
        if binary:
            data += "  content: !!binary | \n     %s\n" % str(content, "utf-8")
        else:
            data += "  content: | \n"
            if isinstance(content, str):
                content = content.split('\n')
            for line in content:
                # data += "     %s\n" % line.strip()
                data += "     %s\n" % line
    return data


def process_ignition_files(files=[], overrides={}):
    """

    :param files:
    :param overrides:
    :return:
    """
    filesdata = []
    unitsdata = []
    for directory in files:
        if not isinstance(directory, dict) or 'origin' not in directory\
                or not os.path.isdir(os.path.expanduser(directory['origin'])):
            continue
        else:
            origin = os.path.expanduser(directory.get('origin'))
            path = directory.get('path')
            for subfil in os.listdir(origin):
                if os.path.isfile("%s/%s" % (origin, subfil)):
                    files.append({'path': '%s/%s' % (path, subfil), 'origin': "%s/%s" % (origin, subfil)})
            files.remove(directory)
    for fil in files:
        if not isinstance(fil, dict):
            continue
        origin = fil.get('origin')
        content = fil.get('content')
        path = fil.get('path')
        mode = int(str(fil.get('mode', '644')), 8)
        permissions = fil.get('permissions', mode)
        if origin is not None:
            origin = os.path.expanduser(origin)
            if not os.path.exists(origin):
                print("Skipping file %s as not found" % origin)
                continue
            binary = True if '.' in origin and origin.split('.')[-1].lower() in binary_types else False
            if binary:
                with open(origin, "rb") as f:
                    content = f.read().encode("base64")
            elif overrides:
                basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                env = Environment(loader=FileSystemLoader(basedir), undefined=undefined, extensions=['jinja2.ext.do'])
                for jinjafilter in jinjafilters.jinjafilters:
                    env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
                try:
                    templ = env.get_template(os.path.basename(origin))
                    fileentries = templ.render(overrides)
                except TemplateSyntaxError as e:
                    error("Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message))
                    os._exit(1)
                except TemplateError as e:
                    error("Error rendering file %s. Got: %s" % (origin, e.message))
                    os._exit(1)
                except UnicodeDecodeError as e:
                    error("Error rendering file %s. Got: %s" % (origin, e))
                    os._exit(1)
                # content = [line.rstrip() for line in fileentries.split('\n') if line.rstrip() != '']
                content = [line for line in fileentries.split('\n')]
            else:
                content = open(origin, 'r').readlines()
        elif content is None:
            continue
        if not isinstance(content, str):
            content = '\n'.join(content) + '\n'
        if path.endswith('.service'):
            unitsdata.append({"contents": content, "name": os.path.basename(path), "enabled": True})
        else:
            content = base64.b64encode(content.encode()).decode("UTF-8")
            filesdata.append({'filesystem': 'root', 'path': path, 'mode': permissions, 'overwrite': True,
                              "contents": {"source": "data:text/plain;charset=utf-8;base64,%s" % content,
                                           "verification": {}}})
    return filesdata, unitsdata


def process_cmds(cmds, overrides):
    """

    :param cmds:
    :param overrides:
    :return:
    """
    data = ''
    for cmd in cmds:
        if cmd.startswith('#'):
            continue
        else:
            try:
                newcmd = Environment(undefined=undefined).from_string(cmd).render(overrides)
                data += "- %s\n" % newcmd.replace(": ", "':' ")
            except TemplateError as e:
                error("Error rendering cmd %s. Got: %s" % (cmd, e.message))
                os._exit(1)
    return data


def process_ignition_cmds(cmds, overrides):
    """

    :param cmds:
    :param overrides:
    :return:
    """
    path = '/usr/local/bin/first.sh'
    permissions = '700'
    content = ''
    for cmd in cmds:
        try:
            newcmd = Environment(undefined=undefined).from_string(cmd).render(overrides)
            content += "%s\n" % newcmd
        except TemplateError as e:
            error("Error rendering cmd %s. Got: %s" % (cmd, e.message))
            os._exit(1)
    if content == '':
        return content
    else:
        if not content.startswith('#!'):
            content = "#!/bin/sh\n%s" % content
        content = base64.b64encode(content.encode()).decode("UTF-8")
        data = {'filesystem': 'root', 'path': path, 'mode': int(permissions, 8),
                "contents": {"source": "data:text/plain;charset=utf-8;base64,%s" % content, "verification": {}}}
        return data


def get_free_port():
    """

    :return:
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def get_free_nodeport():
    """
    :return:
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        port = random.randint(30000, 32767)
        try:
            s.bind(('', port))
            s.close()
            return port
        except Exception:
            continue


def pprint(text):
    # colors = {'blue': '36', 'red': '31', 'green': '32', 'yellow': '33', 'pink': '35', 'white': '37'}
    # color = colors[color]
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


def info2(text):
    color = '36'
    print('\033[%smINFO\033[0m %s' % (color, text))


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
        os._exit(1)
    return


def get_lastvm(client):
    """

    :param client:
    :return:
    """
    if 'HOME' not in os.environ:
        error("HOME variable not set")
        os._exit(1)
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
        for line in open(lastvm).readlines():
            line = line.split(' ')
            if len(line) != 2:
                continue
            cli = line[0].strip()
            vm = line[1].strip()
            if cli == client:
                pprint("Using %s from %s as vm" % (vm, cli))
                return vm
    error("Missing Vm's name")
    os._exit(1)


def set_lastvm(name, client, delete=False):
    """

    :param name:
    :param client:
    :param delete:
    :return:
    """
    if 'HOME' not in os.environ:
        return
    configdir = "%s/.kcli" % os.environ.get('HOME')
    vmfile = "%s/vm" % configdir
    if not os.path.exists(configdir):
        os.mkdir(configdir)
    if delete:
        if not os.path.exists(vmfile):
            return
        else:
            deletecmd = "sed -i ''" if os.path.exists('/Users') and 'gnu' not in find_executable('sed') else "sed -i"
            deletecmd += " '/%s %s/d' %s/vm" % (client, name, configdir)
            os.system(deletecmd)
        return
    if not os.path.exists(vmfile) or os.stat(vmfile).st_size == 0:
        with open(vmfile, 'w') as f:
            f.write("%s %s" % (client, name))
        return
    with open(vmfile, 'r') as original:
        data = original.read()
    with open(vmfile, 'w') as modified:
        modified.write("%s %s\n%s" % (client, name, data))


def remove_duplicates(oldlist):
    """

    :param oldlist:
    :return:
    """
    newlist = []
    for item in oldlist:
        if item not in newlist:
            newlist.append(item)
    return newlist


def get_overrides(paramfile=None, param=[]):
    """

    :param paramfile:
    :param param:
    :return:
    """
    overrides = {}
    if paramfile is not None:
        if os.path.exists(os.path.expanduser(paramfile)):
            with open(os.path.expanduser(paramfile)) as f:
                try:
                    overrides = yaml.safe_load(f)
                except:
                    error("Couldn't parse your parameters file %s. Leaving" % paramfile)
                    os._exit(1)
        else:
            error("Parameter file %s not found. Leaving" % paramfile)
            os._exit(1)
    if not isinstance(overrides, dict):
        error("Couldn't parse your parameters file %s. Leaving" % paramfile)
        os._exit(1)
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
                elif value == 'None':
                    value = None
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


def get_parameters(inputfile, raw=False):
    """

    :param inputfile:
    :param raw:
    :return:
    """
    if raw:
        with open(inputfile, 'r') as entries:
            try:
                return yaml.safe_load(entries)
            except:
                return None
    else:
        parameters = ""
        found = False
        for line in open(inputfile).readlines():
            if found and not line.startswith(' '):
                break
            elif found:
                parameters += line
            elif line != 'parameters:\n' and not found:
                continue
            else:
                parameters += line
                found = True
        results = parameters if parameters != '' else None
        return results


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


def ssh(name, ip='', user=None, local=None, remote=None, tunnel=False, tunnelhost=None, tunnelport=22,
        tunneluser='root', insecure=False, cmd=None, X=False, Y=False, debug=False, D=None, vmport=None,
        identityfile=None):
    """

    :param name:
    :param ip:
    :param host:
    :param port:
    :param user:
    :param local:
    :param remote:
    :param tunnel:
    :param tunnelhost:
    :param tunnelport:
    :param tunneluser:
    :param insecure:
    :param cmd:
    :param X:
    :param Y:
    :param debug:
    :param D:
    :param vmport:
    :return:
    """
    if ip == '':
        return None
    else:
        sshcommand = "%s@%s" % (user, ip)
        if identityfile is None:
            if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                identityfile = os.path.expanduser("~/.kcli/id_rsa")
            elif os.path.exists(os.path.expanduser("~/.kcli/id_dsa")):
                identityfile = os.path.expanduser("~/.kcli/id_dsa")
        if identityfile is not None:
            sshcommand = "-i %s %s" % (identityfile, sshcommand)
        if D:
            sshcommand = "-D %s %s" % (D, sshcommand)
        if X:
            sshcommand = "-X %s" % sshcommand
        if Y:
            sshcommand = "-Y %s" % sshcommand
        if cmd:
            sshcommand = "%s '%s'" % (sshcommand, cmd)
        if tunnelhost is not None and tunnelhost not in ['localhost', '127.0.0.1'] and tunnel and\
                tunneluser is not None:
            if insecure:
                tunnelcommand = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=ERROR "
            else:
                tunnelcommand = ""
            tunnelcommand += "-qp %s -W %%h:%%p %s@%s" % (tunnelport, tunneluser, tunnelhost)
            if identityfile is not None:
                tunnelcommand = "-i %s %s" % (identityfile, tunnelcommand)
            sshcommand = "-o ProxyCommand='ssh %s' %s" % (tunnelcommand, sshcommand)
            if ':' in ip:
                sshcommand = sshcommand.replace(ip, '[%s]' % ip)
        if local is not None:
            sshcommand = "-L %s %s" % (local, sshcommand)
        if remote is not None:
            sshcommand = "-R %s %s" % (remote, sshcommand)
        if vmport is not None:
            sshcommand = "-p %s %s" % (vmport, sshcommand)
        if insecure:
            sshcommand = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=ERROR %s"\
                % sshcommand
        else:
            sshcommand = "ssh %s" % sshcommand
        if debug:
            pprint(sshcommand)
        return sshcommand


def scp(name, ip='', user=None, source=None, destination=None, recursive=None, tunnel=False, tunnelhost=None,
        tunnelport=22, tunneluser='root', debug=False, download=False, vmport=None, insecure=False, identityfile=None):
    """

    :param name:
    :param ip:
    :param user:
    :param source:
    :param destination:
    :param recursive:
    :param tunnel:
    :param tunnelhost:
    :param tunnelport:
    :param tunneluser:
    :param debug:
    :param download:
    :param vmport:
    :return:
    """
    if ip == '':
        print("No ip found. Cannot scp...")
    else:
        arguments = ''
        if tunnelhost is not None and tunnelhost not in ['localhost', '127.0.0.1'] and\
                tunnel and tunneluser is not None:
            arguments += "-o ProxyCommand='ssh -qp %s -W %%h:%%p %s@%s'" % (tunnelport, tunneluser, tunnelhost)
        if insecure:
            arguments += " -o LogLevel=quiet -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        scpcommand = 'scp -q'
        if identityfile is None:
            if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                identityfile = os.path.expanduser("~/.kcli/id_rsa")
            elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                identityfile = os.path.expanduser("~/.kcli/id_rsa")
        if identityfile is not None:
            scpcommand = "%s -i %s" % (scpcommand, identityfile)
        if recursive:
            scpcommand = "%s -r" % scpcommand
        if vmport is not None:
            scpcommand = "%s -P %s" % (scpcommand, vmport)
        if download:
            scpcommand = "%s %s %s@%s:%s %s" % (scpcommand, arguments, user, ip, source, destination)
        else:
            scpcommand = "%s %s %s %s@%s:%s" % (scpcommand, arguments, source, user, ip, destination)
        if debug:
            pprint(scpcommand)
        return scpcommand


def get_user(image):
    """

    :param image:
    :return:
    """
    if 'centos' in image.lower():
        user = 'centos'
    elif 'coreos' in image.lower() or 'rhcos' in image.lower() or 'fcos' in image.lower():
        user = 'core'
    elif 'cirros' in image.lower():
        user = 'cirros'
    elif [x for x in UBUNTUS if x in image.lower()] or 'ubuntu' in image.lower():
        user = 'ubuntu'
    elif 'fedora' in image.lower():
        user = 'fedora'
    elif 'rhel' in image.lower():
        user = 'cloud-user'
    elif 'debian' in image.lower():
        user = 'debian'
    elif 'arch' in image.lower():
        user = 'arch'
    elif 'freebsd' in image.lower():
        user = 'freebsd'
    elif 'netbsd' in image.lower():
        user = 'netbsd'
    elif 'openbsd' in image.lower():
        user = 'openbsd'
    else:
        user = 'root'
    return user


def get_cloudinitfile(image):
    """

    :param image:
    :return:
    """
    lower = image.lower()
    cloudinitfile = '/var/log/cloud-init-output.log'
    if 'centos-7' in lower or 'centos7' in lower:
        cloudinitfile = '/var/log/messages'
    return cloudinitfile


def ignition(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[],
             enableroot=True, overrides={}, iso=True, fqdn=False, version='3.1.0', plan=None, compact=False,
             removetls=False, ipv6=[], image=None, nokeys=False, noname=False):
    """

    :param name:
    :param keys:
    :param cmds:
    :param nets:
    :param gateway:
    :param dns:
    :param domain:
    :param reserveip:
    :param files:
    :param enableroot:
    :param overrides:
    :param iso:
    :param fqdn:
    :return:
    """
    separators = (',', ':') if compact else (',', ': ')
    indent = 0 if compact else 4
    default_gateway = gateway
    publickeys = []
    storage = {"files": []}
    systemd = {"units": []}
    if domain is not None:
        localhostname = "%s.%s" % (name, domain)
    else:
        localhostname = name
    if not nokeys:
        for path in ["~/.kcli/id_rsa.pub", "~/.kcli/id_dsa.pub", "~/.ssh/id_rsa.pub", "~/.ssh/id_dsa.pub"]:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path) and os.path.exists(expanded_path.replace('.pub', '')):
                publickeyfile = expanded_path
                with open(publickeyfile, 'r') as ssh:
                    publickeys.append(ssh.read().strip())
                break
        if keys:
            for key in list(set(keys)):
                publickeys.append(key)
        if not publickeys:
            error("neither id_rsa or id_dsa public keys found in your .ssh or .kcli directory, you might have trouble "
                  "accessing the vm")
    if not noname:
        hostnameline = quote("%s\n" % localhostname)
        storage["files"].append({"filesystem": "root", "path": "/etc/hostname", "overwrite": True,
                                 "contents": {"source": "data:,%s" % hostnameline, "verification": {}}, "mode": 420})
    if dns is not None:
        nmline = quote("[main]\ndhcp=dhclient\n")
        storage["files"].append({"filesystem": "root", "path": "/etc/NetworkManager/conf.d/dhcp-client.conf",
                                 "overwrite": True,
                                 "contents": {"source": "data:,%s" % nmline, "verification": {}}, "mode": 420})
        dnsline = quote("prepend domain-name-servers %s;\nsend dhcp-client-identifier = hardware;\n" % dns)
        storage["files"].append({"filesystem": "root", "path": "/etc/dhcp/dhclient.conf",
                                 "overwrite": True,
                                 "contents": {"source": "data:,%s" % dnsline, "verification": {}}, "mode": 420})
    if nets:
        enpindex = 255
        for index, net in enumerate(nets):
            static_nic_file = static_nic
            static_nic_file_mode = '755'
            netdata = ''
            if isinstance(net, str):
                if index == 0:
                    continue
                if image is not None and ('fcos' in image or 'fedora-coreos' in image):
                    nicname = "eth%d" % index
                else:
                    nicname = "ens%d" % (index + 3)
                ip = None
                netmask = None
                noconf = None
                vips = []
            elif isinstance(net, dict):
                if image is not None and ('fcos' in image or 'fedora-coreos' in image):
                    default_nicname = "eth%s" % index
                elif net.get('numa') is not None:
                    default_nicname = "enp%ds0" % enpindex
                    enpindex -= 2
                else:
                    default_nicname = "ens%d" % (index + 3)
                if image == 'custom_ipxe':
                    default_nicname = "ens3f1"
                nicname = net.get('nic', default_nicname)
                ip = net.get('ip')
                gateway = net.get('gateway')
                netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
                noconf = net.get('noconf')
                vips = net.get('vips')
            nicpath = "/etc/NetworkManager/dispatcher.d/static_%s" % nicname
            if noconf is not None:
                netdata = "DEVICE=%s\nNAME=%s\nONBOOT=no" % (nicname, nicname)
            elif ip is not None and netmask is not None and not reserveip and gateway is not None:
                if index == 0 and default_gateway is not None:
                    gateway = default_gateway
                netdata = "DEVICE=%s\nNAME=%s\nONBOOT=yes\nNM_CONTROLLED=yes\n" % (nicname, nicname)
                netdata += "BOOTPROTO=static\nIPADDR=%s\nNETMASK=%s\nGATEWAY=%s" % (ip, netmask, gateway)
                dns = net.get('dns')
                if dns is not None:
                    netdata += "\nDNS1=%s\n" % dns
                if isinstance(vips, list) and vips:
                    for vip in vips:
                        netdata += "[Network]\nAddress=%s/%s\nGateway=%s\n" % (vip, netmask, gateway)
                if image is not None and ('fcos' in image or 'fedora-coreos' in image):
                    netdata = "[connection]\ntype=ethernet\ninterface-name=%s\n" % nicname
                    netdata += "match-device=interface-name:%s\n\n" % nicname
                    netdata += "[ipv4]\nmethod=manual\naddresses=%s/%s\ngateway=%s\n" % (ip, netmask, gateway)
                    nicpath = "/etc/NetworkManager/system-connections/%s.nmconnection" % nicname
                    static_nic_file = static_nic_fcos
                    static_nic_file_mode = '0600'
            if netdata != '':
                static = quote(static_nic_file.format(nicname=nicname, data=netdata))
                storage["files"].append({"filesystem": "root",
                                         "path": nicpath,
                                         "contents": {"source": "data:,%s" % static, "verification": {}},
                                         "mode": int(static_nic_file_mode, 8)})
    if files:
        filesdata, unitsdata = process_ignition_files(files=files, overrides=overrides)
        if filesdata:
            storage["files"].extend(filesdata)
        if unitsdata:
            systemd["units"].extend(unitsdata)
    cmdunit = None
    if cmds:
        cmdsdata = process_ignition_cmds(cmds, overrides)
        storage["files"].append(cmdsdata)
        firstpath = "/usr/local/bin/first.sh"
        content = "[Service]\nType=oneshot\nExecStart=%s\n[Install]\nWantedBy=multi-user.target\n" % firstpath
        if 'need_network' in overrides:
            content += "[Unit]\nAfter=network-online.target\nWants=network-online.target\n"
        cmdunit = {"contents": content, "name": "first-boot.service", "enabled": True}
    if cmdunit is not None:
        systemd["units"].append(cmdunit)
    data = {'ignition': {'version': version, 'config': {}}, 'storage': storage, 'systemd': systemd,
            'passwd': {'users': []}}
    if publickeys:
        data['passwd']['users'] = [{'name': 'core', 'sshAuthorizedKeys': publickeys}]
    role = None
    if len(name.split('-')) >= 3 and name.split('-')[-2] in ['master', 'worker']:
        role = name.split('-')[-2]
    elif len(name.split('-')) >= 2 and name.split('-')[-1] == 'bootstrap':
        role = name.split('-')[-1]
    if role is not None:
        cluster = overrides.get('cluster', plan)
        ignitionclusterpath = find_ignition_files(role, cluster=cluster)
        if ignitionclusterpath is not None:
            data = mergeignition(name, ignitionclusterpath, data)
        rolepath = "/workdir/%s-%s.ign" % (plan, role) if os.path.exists('/i_am_a_container') else "%s-%s.ign" % (plan,
                                                                                                                  role)
        if os.path.exists(rolepath):
            ignitionextrapath = rolepath
            data = mergeignition(name, ignitionextrapath, data)
    planpath = "/workdir/%s.ign" % plan if os.path.exists('/i_am_a_container') else "%s.ign" % plan
    if os.path.exists(planpath):
        ignitionextrapath = planpath
        data = mergeignition(name, ignitionextrapath, data)
    namepath = "/workdir/%s.ign" % name if os.path.exists('/i_am_a_container') else "%s.ign" % name
    if os.path.exists(namepath):
        ignitionextrapath = namepath
        data = mergeignition(name, ignitionextrapath, data)
    if removetls and 'append' in data['ignition']['config'] and\
            data['ignition']['config']['append'][0]['source'].startswith("http://"):
        del data['ignition']['security']['tls']['certificateAuthorities']
    # remove duplicate files to please ignition v3
    paths = []
    storagefinal = []
    for fileentry in data['storage']['files']:
        if fileentry['path'] not in paths:
            storagefinal.append(fileentry)
            paths.append(fileentry['path'])
    data['storage']['files'] = storagefinal
    try:
        result = json.dumps(data, sort_keys=True, indent=indent, separators=separators)
    except:
        result = json.dumps(data, indent=indent, separators=separators)
    return result


def get_latest_fcos(url, _type='kvm'):
    keys = {'ovirt': 'openstack', 'kubevirt': 'openstack', 'kvm': 'qemu', 'vsphere': 'vmware'}
    key = keys.get(_type, _type)
    _format = 'ova' if _type == 'vsphere' else 'qcow2.xz'
    with urlopen(url) as u:
        data = json.loads(u.read().decode())
        return data['architectures']['x86_64']['artifacts'][key]["formats"][_format]['disk']['location']


def get_latest_fcos_metal(url):
    with urlopen(url) as u:
        data = json.loads(u.read().decode())
        formats = data['architectures']['x86_64']['artifacts']['metal']['formats']
        kernel = formats['pxe']['kernel']['location']
        initrd = formats['pxe']['initramfs']['location']
        metal = formats['raw.xz']['disk']['location']
        return kernel, initrd, metal


def get_latest_rhcos(url, _type='kvm'):
    keys = {'ovirt': 'openstack', 'kubevirt': 'openstack', 'kvm': 'qemu', 'vsphere': 'vmware'}
    key = keys.get(_type, _type)
    buildurl = '%s/builds.json' % url
    with urlopen(buildurl) as b:
        data = json.loads(b.read().decode())
        for build in data['builds']:
            if isinstance(build, dict):
                build = build['id']
                if _type in ['openstack', 'ovirt', 'kubevirt']:
                    return "%s/%s/x86_64/rhcos-%s-openstack.x86_64.qcow2.gz" % (url, build, build)
                elif _type == 'vsphere':
                    return "%s/%s/x86_64/rhcos-%s-vmware.x86_64.ova" % (url, build, build)
                elif _type == 'gcp':
                    return "https://storage.googleapis.com/rhcos/rhcos/%s.tar.gz" % build
                else:
                    return "%s/%s/x86_64/rhcos-%s-qemu.x86_64.qcow2.gz" % (url, build, build)
            else:
                metaurl = '%s/%s/meta.json' % (url, build)
                with urlopen(metaurl) as m:
                    data = json.loads(m.read().decode())
                    if key in data['images']:
                        return "%s/%s/%s" % (url, build, data['images'][key]['path'])


def get_commit_rhcos(commitid, _type='kvm'):
    keys = {'ovirt': 'openstack', 'kubevirt': 'openstack', 'kvm': 'qemu', 'vsphere': 'vmware'}
    key = keys.get(_type, _type)
    buildurl = "https://raw.githubusercontent.com/openshift/installer/%s/data/data/rhcos.json" % commitid
    with urlopen(buildurl) as b:
        data = json.loads(b.read().decode())
        baseuri = data['baseURI']
        path = "%s%s" % (baseuri, data['images'][key]['path'])
        return path


def get_installer_rhcos(_type='kvm'):
    keys = {'ovirt': 'openstack', 'kubevirt': 'openstack', 'kvm': 'qemu', 'vsphere': 'vmware'}
    key = keys.get(_type, _type)
    INSTALLER_COREOS = os.popen('openshift-install coreos print-stream-json 2>/dev/null').read()
    data = json.loads(INSTALLER_COREOS)
    return data['architectures']['x86_64']['artifacts'][key]['formats']['qcow2.gz']['disk']['location']


def get_commit_rhcos_metal(commitid):
    buildurl = "https://raw.githubusercontent.com/openshift/installer/%s/data/data/rhcos.json" % commitid
    with urlopen(buildurl) as b:
        data = json.loads(b.read().decode())
        baseuri = data['baseURI']
        kernel = "%s%s" % (baseuri, data['images']['kernel']['path'])
        initrd = "%s%s" % (baseuri, data['images']['initramfs']['path'])
        metal = "%s%s" % (baseuri, data['images']['metal']['path'])
        return kernel, initrd, metal


def get_installer_rhcos_metal():
    INSTALLER_COREOS = os.popen('openshift-install coreos print-stream-json 2>/dev/null').read()
    data = json.loads(INSTALLER_COREOS)
    base = data['architectures']['x86_64']['artifacts']['metal']['formats']['pxe']
    kernel = base['kernel']['location']
    initrd = base['initramfs']['location']
    metal = base['rootfs']['location']
    return kernel, initrd, metal


def get_installer_iso():
    INSTALLER_COREOS = os.popen('openshift-install coreos print-stream-json 2>/dev/null').read()
    data = json.loads(INSTALLER_COREOS)
    return data['architectures']['x86_64']['artifacts']['metal']['formats']['iso']['disk']['location']


def get_latest_rhcos_metal(url):
    buildurl = '%s/builds.json' % url
    with urlopen(buildurl) as b:
        data = json.loads(b.read().decode())
        for build in data['builds']:
            build = build['id']
            kernel = "%s/%s/x86_64/rhcos-%s-installer-kernel-x86_64" % (url, build, build)
            initrd = "%s/%s/x86_64/rhcos-%s-installer-initramfs.x86_64.img" % (url, build, build)
            metal = "%s/%s/x86_64/rhcos-%s-metal.x86_64.raw.gz" % (url, build, build)
            return kernel, initrd, metal


def find_ignition_files(role, cluster):
    clusterpath = os.path.expanduser("~/.kcli/clusters/%s/%s.ign" % (cluster, role))
    if os.path.exists('/i_am_a_container'):
        oldclusterpath = "/workdir/clusters/%s/%s.ign" % (cluster, role)
        rolepath = "/workdir/%s/%s.ign" % (cluster, role)
    else:
        oldclusterpath = "clusters/%s/%s.ign" % (cluster, role)
        rolepath = "%s/%s.ign" % (cluster, role)
    if os.path.exists(clusterpath):
        return clusterpath
    elif os.path.exists(oldclusterpath):
        return oldclusterpath
    elif os.path.exists(rolepath):
        return rolepath
    else:
        return None


def pretty_print(o, value=False):
    """

    :param o:
    """
    data = yaml.dump(o, default_flow_style=False, indent=2, allow_unicode=True)
    data = data.replace("'", '').replace('\n\n', '\n').replace('#cloud-config', '|\n            #cloud-config')
    if not value:
        print(data)
    else:
        return data


def need_guest_agent(image):
    if image.lower().startswith('centos'):
        return True
    if image.lower().startswith('fedora'):
        return True
    if 'fedora-cloud' in image.lower():
        return True
    if image.lower().startswith('rhel'):
        return True
    return False


def create_host(data):
    """

    :param data:
    """
    if data['name'] is None:
        if data['_type'] in ['kvm', 'ovirt']:
            name = data['host'] if 'host' not in ['localhost', '127.0.0.1'] else 'local'
    else:
        name = data['name']
        del data['name']
    data['type'] = data['_type']
    del data['_type']
    ini = {}
    path = os.path.expanduser('~/.kcli/config.yml')
    rootdir = os.path.expanduser('~/.kcli')
    if not os.path.exists(rootdir):
        os.makedirs(rootdir)
    if os.path.exists(path):
        with open(path, 'r') as entries:
            try:
                oldini = yaml.safe_load(entries)
            except yaml.scanner.ScannerError as err:
                error("Couldn't parse yaml in .kcli/config.yml. Got %s" % err)
                os._exit(1)
        if name in oldini:
            pprint("Skipping existing Host %s" % name)
            return
        ini = oldini
    ini[name] = {k: data[k] for k in data if data[k] is not None}
    with open(path, 'w') as conf_file:
        try:
            yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                           sort_keys=False)
        except:
            yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    pprint("Using %s as hostname" % name)
    pprint("Host %s created" % name)


def delete_host(name):
    """

    :param name:
    """
    path = os.path.expanduser('~/.kcli/config.yml')
    if not os.path.exists(path):
        pprint("Skipping non existing Host %s" % name)
        return
    else:
        with open(path, 'r') as entries:
            try:
                ini = yaml.safe_load(entries)
            except yaml.scanner.ScannerError as err:
                error("Couldn't parse yaml in .kcli/config.yml. Got %s" % err)
                os._exit(1)
        if name not in ini:
            pprint("Skipping non existing Host %s" % name)
            return
        del ini[name]
        clients = [c for c in ini if c != 'default']
        if not clients:
            os.remove(path)
        else:
            with open(path, 'w') as conf_file:
                try:
                    yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                                   sort_keys=False)
                except:
                    yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
        success("Host %s deleted" % name)


def get_binary(name, linuxurl, macosurl, compressed=False):
    if find_executable(name) is not None:
        return find_executable(name)
    binary = '/var/tmp/%s' % name
    if os.path.exists(binary):
        pprint("Using %s from /var/tmp" % name)
    else:
        pprint("Downloading %s in /var/tmp" % name)
        url = macosurl if os.path.exists('/Users') else linuxurl
        if compressed:
            downloadcmd = "curl -L '%s' | gunzip > %s" % (url, binary)
        else:
            downloadcmd = "curl -L '%s' > %s" % (url, binary)
        downloadcmd += "; chmod u+x %s" % binary
        os.system(downloadcmd)
    return binary


def _ssh_credentials(k, name):
    vmport = None
    info = k.info(name, debug=False)
    if not info:
        return None, None, None
    user, ip, status = info.get('user', 'root'), info.get('ip'), info.get('status')
    if status in ['down', 'suspended', 'unknown']:
        error("%s down" % name)
    if 'nodeport' in info:
        vmport = info['nodeport']
        ip = k.node_host(name=info.get('host'))
        if ip is None:
            error("No valid node ip found" % name)
    elif 'loadbalancerip' in info:
        ip = info['loadbalancerip']
    if ip is None:
        error("No ip found for %s" % name)
    return user, ip, vmport


def mergeignition(name, ignitionextrapath, data):
    pprint("Merging ignition data from existing %s for %s" % (ignitionextrapath, name))
    with open(ignitionextrapath, 'r') as extra:
        try:
            ignitionextra = json.load(extra)
        except Exception as e:
            error("Couldn't process %s. Ignoring" % (ignitionextrapath))
            error(e)
            os._exit(1)
        children = {'storage': 'files', 'passwd': 'users', 'systemd': 'units'}
        for key in children:
            childrenkey2 = 'path' if key == 'storage' else 'name'
            if key in data and key in ignitionextra:
                if children[key] in data[key] and children[key] in ignitionextra[key]:
                    for entry in data[key][children[key]]:
                        if entry[childrenkey2] not in [x[childrenkey2] for x in ignitionextra[key][children[key]]]:
                            ignitionextra[key][children[key]].append(entry)
                        elif children[key] == 'users':
                            newdata = []
                            users = [x['name'] for x in data[key][children[key]] + ignitionextra[key][children[key]]]
                            users = list(dict.fromkeys(users))
                            for user in users:
                                newuser = {'name': user}
                                sshkey1, sshkey2 = [], []
                                password = None
                                for y in data[key][children[key]]:
                                    if y['name'] == user:
                                        sshkey1 = y['sshAuthorizedKeys'] if 'sshAuthorizedKeys' in y else []
                                        password = y.get('passwordHash')
                                for x in ignitionextra[key][children[key]]:
                                    if x['name'] == user:
                                        sshkey2 = x['sshAuthorizedKeys'] if 'sshAuthorizedKeys' in x else []
                                        password = x.get('passwordHash')
                                sshkeys = sshkey1
                                if sshkey2:
                                    sshkeys.extend(sshkey2)
                                if sshkeys:
                                    sshkeys = list(dict.fromkeys([sshkey.strip() for sshkey in sshkeys]))
                                    newuser['sshAuthorizedKeys'] = sshkeys
                                if password is not None:
                                    newuser['passwordHash'] = password
                                newdata.append(newuser)
                            ignitionextra[key][children[key]] = newdata
                elif children[key] in data[key] and children[key] not in ignitionextra[key]:
                    ignitionextra[key][children[key]] = data[key][children[key]]
            elif key in data and key not in ignitionextra:
                ignitionextra[key] = data[key]
        if data['ignition']['config']:
            ignitionextra['ignition']['config'] = data['ignition']['config']
    return ignitionextra


def valid_tag(tag):
    if '/' in tag:
        tag = tag.split('/')[1]
    if len(tag) != 3 or not tag.startswith('4.'):
        msg = "Tag should have a format of 4.X"
        raise Exception(msg)
    return tag


def gen_mac():
    mac = [0x00, 0x16, 0x3e, randint(0x00, 0x7f), randint(0x00, 0xff), randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def pwd_path(x):
    if x is None:
        return None
    result = '/workdir/%s' % x if os.path.exists('/i_am_a_container') else x
    return result


def real_path(x):
    return x.replace('/workdir/', '')


def insecure_fetch(url, headers=[]):
    context = ssl._create_unverified_context()
    req = Request(url)
    if headers:
        for header in headers:
            header_split = header.split(' ')
            key = header_split[0].replace(':', '')
            value = ' '.join(header_split[1:])
            req.add_header(key, value)
    response = urlopen(req, timeout=5, context=context)
    data = response.read()
    return data.decode('utf-8')


def get_values(data, element, field):
    results = []
    if '%s_%s' % (element, field) in data:
        new = data['%s_%s' % (element, field)]
        results.extend(new)
    return results


def is_debian9(image):
    if 'debian-9' in image.lower():
        return True
    else:
        return False


def is_debian10(image):
    if 'debian-10' in image.lower():
        return True
    else:
        return False


def is_ubuntu(image):
    if [x for x in UBUNTUS if x in image.lower()] or 'ubuntu' in image.lower():
        return True
    else:
        return False


def is_7(image):
    lower = image.lower()
    if lower.startswith('centos-7') or lower.startswith('rhel-server-7'):
        return True
    return False


def needs_ignition(image):
    if 'coreos' in image or 'rhcos' in image or 'fcos' in image or 'fedora-coreos' in image:
        return True
    else:
        return False


def ignition_version(image):
    version = '3.1.0'
    ignition_versions = {"4%d" % i: '2.2.0' for i in range(6)}
    ignition_versions.update({46: '3.1.0', 47: '3.1.0', 48: '3.2.0'})
    image = os.path.basename(image)
    version_match = re.match('rhcos-*(..).*', image)
    if version_match is not None and isinstance(version_match.group(1), int):
        openshift_version = int(version_match.group(1))
        version = ignition_versions[openshift_version]
    return version


def get_kubectl(version='latest'):
    SYSTEM = 'darwin' if os.path.exists('/Users') else 'linux'
    if version == 'latest':
        r = urlopen("https://storage.googleapis.com/kubernetes-release/release/stable.txt")
        version = str(r.read(), 'utf-8').strip()
    kubecmd = "curl -LO https://storage.googleapis.com/kubernetes-release/release/%s/bin/%s/amd64/kubectl" % (version,
                                                                                                              SYSTEM)
    kubecmd += "; chmod 700 kubectl"
    call(kubecmd, shell=True)


def get_oc(version='latest', macosx=False):
    SYSTEM = 'mac' if os.path.exists('/Users') else 'linux'
    pprint("Downloading oc in current directory")
    occmd = "curl -s "
    occmd += "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/%s/openshift-client-%s.tar.gz" % (version,
                                                                                                          SYSTEM)
    occmd += "| tar zxf - oc"
    occmd += "; chmod 700 oc"
    call(occmd, shell=True)
    if os.path.exists('/i_am_a_container'):
        if macosx:
            occmd += "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/%s/" % version
            occmd += "openshift-client-%s.tar.gz" % SYSTEM
            occmd += "| tar zxf -C /workdir - oc"
            occmd += "; chmod 700 /workdir/oc"
            call(occmd, shell=True)
        else:
            move('oc', '/workdir/oc')


def get_helm(version='latest'):
    SYSTEM = 'darwin' if os.path.exists('/Users') else 'linux'
    if version == 'latest':
        version = jinjafilters.githubversion('helm/helm')
    elif not version.startswith('v'):
        version = "v%s" % version
    helmcmd = "curl -s https://get.helm.sh/helm-%s-%s-amd64.tar.gz |" % (version, SYSTEM)
    helmcmd += "tar zxf - --strip-components 1 %s-amd64/helm;" % SYSTEM
    helmcmd += "chmod 700 helm"
    call(helmcmd, shell=True)


def kube_create_app(config, appdir, overrides={}, outputdir=None):
    appdata = {'cluster': 'testk', 'domain': 'karmalabs.com', 'masters': 1, 'workers': 0}
    cluster = appdata['cluster']
    cwd = os.getcwd()
    os.environ["PATH"] += ":%s" % cwd
    overrides['cwd'] = cwd
    default_parameter_file = "%s/kcli_default.yml" % appdir
    if os.path.exists(default_parameter_file):
        with open(default_parameter_file, 'r') as entries:
            appdefault = yaml.safe_load(entries)
            appdata.update(appdefault)
    appdata.update(overrides)
    with TemporaryDirectory() as tmpdir:
        for root, dirs, files in os.walk(appdir):
            for name in files:
                rendered = config.process_inputfile(cluster, "%s/%s" % (appdir, name), overrides=appdata)
                destfile = "%s/%s" % (outputdir, name) if outputdir is not None else "%s/%s" % (tmpdir, name)
                with open(destfile, 'w') as f:
                    f.write(rendered)
        if outputdir is None:
            os.chdir(tmpdir)
            result = call('bash %s/install.sh' % tmpdir, shell=True)
        else:
            pprint("Copied artifacts to %s" % outputdir)
            result = 0
    os.chdir(cwd)
    return result


def kube_delete_app(config, appdir, overrides={}):
    found = False
    cluster = 'xxx'
    cwd = os.getcwd()
    os.environ["PATH"] += ":%s" % cwd
    overrides['cwd'] = cwd
    with TemporaryDirectory() as tmpdir:
        for root, dirs, files in os.walk(appdir):
            for name in files:
                if name == 'uninstall.sh':
                    found = True
                rendered = config.process_inputfile(cluster, "%s/%s" % (appdir, name), overrides=overrides)
                with open("%s/%s" % (tmpdir, name), 'w') as f:
                    f.write(rendered)
        os.chdir(tmpdir)
        if not found:
            warning("Uninstall not supported for this app")
            result = 1
        else:
            result = call('bash %s/uninstall.sh' % tmpdir, shell=True)
    os.chdir(cwd)
    return result


def openshift_create_app(config, appdir, overrides={}, outputdir=None):
    appname = overrides['name']
    appdata = {'cluster': 'testk', 'domain': 'karmalabs.com', 'masters': 1, 'workers': 0}
    cluster = appdata['cluster']
    cwd = os.getcwd()
    os.environ["PATH"] += ":%s" % cwd
    overrides['cwd'] = cwd
    default_parameter_file = "%s/%s/kcli_default.yml" % (appdir, appname)
    if os.path.exists(default_parameter_file):
        with open(default_parameter_file, 'r') as entries:
            appdefault = yaml.safe_load(entries)
            appdata.update(appdefault)
    appdata.update(overrides)
    with TemporaryDirectory() as tmpdir:
        env = Environment(loader=FileSystemLoader(appdir), extensions=['jinja2.ext.do'], trim_blocks=True,
                          lstrip_blocks=True)
        for jinjafilter in jinjafilters.jinjafilters:
            env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        try:
            templ = env.get_template(os.path.basename("install.yml.j2"))
        except TemplateSyntaxError as e:
            error("Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message))
            os._exit(1)
        except TemplateError as e:
            error("Error rendering file %s. Got: %s" % (e.filename, e.message))
            os._exit(1)
        destfile = "%s/install.yml" % outputdir if outputdir is not None else "%s/install.yml" % tmpdir
        with open(destfile, 'w') as f:
            olmfile = templ.render(overrides)
            f.write(olmfile)
        destfile = "%s/install.sh" % outputdir if outputdir is not None else "%s/install.sh" % tmpdir
        with open(destfile, 'w') as f:
            f.write("oc create -f install.yml\n")
            if os.path.exists("%s/%s/pre.sh" % (appdir, appname)):
                rendered = config.process_inputfile(cluster, "%s/%s/pre.sh" % (appdir, appname),
                                                    overrides=appdata)
                f.write("%s\n" % rendered)
            if os.path.exists("%s/%s/cr.yml" % (appdir, appname)):
                rendered = config.process_inputfile(cluster, "%s/%s/cr.yml" % (appdir, appname), overrides=appdata)
                destfile = "%s/cr.yml" % outputdir if outputdir is not None else "%s/cr.yml" % tmpdir
                with open(destfile, 'w') as g:
                    g.write(rendered)
                crd = overrides.get('crd')
                rendered = config.process_inputfile(cluster, "%s/cr.sh" % appdir, overrides={'crd': crd})
                f.write(rendered)
            if os.path.exists("%s/%s/post.sh" % (appdir, appname)):
                rendered = config.process_inputfile(cluster, "%s/%s/post.sh" % (appdir, appname),
                                                    overrides=appdata)
                f.write(rendered)
        if outputdir is None:
            os.chdir(tmpdir)
            result = call('bash %s/install.sh' % tmpdir, shell=True)
        else:
            pprint("Copied artifacts to %s" % outputdir)
            result = 0
    os.chdir(cwd)
    return result


def openshift_delete_app(config, appdir, overrides={}):
    appname = overrides['name']
    appdata = {'cluster': 'testk', 'domain': 'karmalabs.com', 'masters': 1, 'workers': 0}
    cluster = appdata['cluster']
    cwd = os.getcwd()
    os.environ["PATH"] += ":%s" % cwd
    overrides['cwd'] = cwd
    default_parameter_file = "%s/%s/kcli_default.yml" % (appdir, appname)
    if os.path.exists(default_parameter_file):
        with open(default_parameter_file, 'r') as entries:
            appdefault = yaml.safe_load(entries)
            appdata.update(appdefault)
    appdata.update(overrides)
    with TemporaryDirectory() as tmpdir:
        env = Environment(loader=FileSystemLoader(appdir), extensions=['jinja2.ext.do'], trim_blocks=True,
                          lstrip_blocks=True)
        for jinjafilter in jinjafilters.jinjafilters:
            env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
        try:
            templ = env.get_template(os.path.basename("install.yml.j2"))
        except TemplateSyntaxError as e:
            error("Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message))
            os._exit(1)
        except TemplateError as e:
            error("Error rendering file %s. Got: %s" % (e.filename, e.message))
            os._exit(1)
        destfile = "%s/install.yml" % tmpdir
        with open(destfile, 'w') as f:
            olmfile = templ.render(overrides)
            f.write(olmfile)
        destfile = "%s/uninstall.sh" % tmpdir
        with open(destfile, 'w') as f:
            if os.path.exists("%s/%s/cr.yml" % (appdir, appname)):
                rendered = config.process_inputfile(cluster, "%s/%s/cr.yml" % (appdir, appname), overrides=appdata)
                destfile = "%s/cr.yml" % tmpdir
                with open(destfile, 'w') as g:
                    g.write(rendered)
                f.write("oc delete -f cr.yml\n")
            f.write("oc delete -f install.yml")
        os.chdir(tmpdir)
        result = call('bash %s/uninstall.sh' % tmpdir, shell=True)
    os.chdir(cwd)
    return result


def make_iso(name, tmpdir, userdata, metadata, netdata):
    with open("%s/user-data" % tmpdir, 'w') as x:
        x.write(userdata)
    with open("%s/meta-data" % tmpdir, 'w') as y:
        y.write(metadata)
    isocmd = 'mkisofs'
    if find_executable('genisoimage') is not None:
        isocmd = 'genisoimage'
    isocmd += " --quiet -o %s/%s.ISO --volid cidata" % (tmpdir, name)
    isocmd += " --joliet --rock %s/user-data %s/meta-data" % (tmpdir, tmpdir)
    if netdata is not None:
        with open("%s/network-config" % tmpdir, 'w') as z:
            z.write(netdata)
        isocmd += " %s/network-config" % tmpdir
    os.system(isocmd)


def patch_bootstrap(path, patch, service):
    separators = (',', ':')
    indent = 0
    warning("Patching bootkube in bootstrap ignition to handle less than 3 masters")
    with open(path, 'r') as ignition:
        data = json.load(ignition)
    patch_base64 = base64.b64encode(patch.encode()).decode("UTF-8")
    patch_source = "data:text/plain;charset=utf-8;base64,%s" % patch_base64
    patch_entry = {"filesystem": "root", "path": "/usr/local/bin/kcli-patch.sh",
                   "contents": {"source": patch_source, "verification": {}}, "mode": 448}
    data['storage']['files'].append(patch_entry)
    data['systemd']['units'].append({"contents": service, "name": 'kcli-patch.service', "enabled": True})
    try:
        result = json.dumps(data, sort_keys=True, indent=indent, separators=separators)
    except:
        result = json.dumps(data, indent=indent, separators=separators)
    with open(path, 'w') as ignition:
        ignition.write(result)
    return data


def filter_compression_extension(name):
    return name.replace('.gz', '').replace('.xz', '').replace('.bz2', '')


def generate_rhcos_iso(k, cluster, pool, version='latest', force=False):
    if force:
        liveiso = get_installer_iso()
        baseiso = os.path.basename(liveiso)
    else:
        baseiso = 'rhcos-live.x86_64.iso'
        liveiso = "https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/%s/latest/%s" % (version, baseiso)
    if baseiso not in k.volumes(iso=True):
        pprint("Downloading %s" % baseiso)
        k.add_image(liveiso, pool)
    if '%s.iso' % cluster in [os.path.basename(iso) for iso in k.volumes(iso=True)]:
        warning("Deleting old iso %s.iso" % cluster)
        k.delete_image('%s.iso' % cluster)
    pprint("Creating iso %s.iso" % cluster)
    poolpath = k.get_pool_path(pool)
    coreosinstaller = "podman run --privileged --rm -w /data -v %s:/data -v /dev:/dev" % poolpath
    if not os.path.exists('/Users'):
        coreosinstaller += " -v /run/udev:/run/udev"
    coreosinstaller += " quay.io/coreos/coreos-installer:release"
    isocmd = "%s iso ignition embed -fi iso.ign -o %s.iso %s" % (coreosinstaller, cluster, baseiso)
    if k.host in ['localhost', '127.0.0.1']:
        if find_executable('podman') is None:
            error("podman is required in order to embed iso ignition")
            os._exit(1)
        copy2('iso.ign', poolpath)
        os.system(isocmd)
    elif k.protocol == 'ssh':
        scpcmd = 'scp %s -P %s iso.ign %s@%s:%s' % (k.identitycommand, k.port, k.user, k.host, poolpath)
        os.system(scpcmd)
        isocmd = 'ssh %s -p %s %s@%s "%s"' % (k.identitycommand, k.port, k.user, k.host, isocmd)
        os.system(isocmd)


def olm_app(package):
    os.environ["PATH"] += ":%s" % os.getcwd()
    name, source, defaultchannel, csv, description, installmodes, crd = None, None, None, None, None, None, None
    target_namespace = None
    manifestscmd = "oc get packagemanifest -n openshift-marketplace -o yaml"
    for data in yaml.safe_load(os.popen(manifestscmd).read())['items']:
        if package in data['metadata']['name']:
            name = data['metadata']['name']
            target_namespace = name.split('-operator')[0]
            status = data['status']
            source = status['catalogSource']
            defaultchannel = status['defaultChannel']
            for channel in status['channels']:
                if channel['name'] == defaultchannel:
                    csv = channel['currentCSV']
                    description = channel['currentCSVDesc']['description']
                    installmodes = channel['currentCSVDesc']['installModes']
                    for mode in installmodes:
                        if mode['type'] == 'OwnNamespace' and not mode['supported']:
                            target_namespace = 'openshift-operators'
                            break
                    csvdesc = channel['currentCSVDesc']
                    csvdescannotations = csvdesc['annotations']
                    if 'operatorframework.io/suggested-namespace' in csvdescannotations:
                        target_namespace = csvdescannotations['operatorframework.io/suggested-namespace']
                    if 'customresourcedefinitions' in csvdesc and csvdesc['customresourcedefinitions']:
                        crd = csvdesc['customresourcedefinitions']['owned'][0]['name']
                    break
            if name == package or data['metadata']['labels']['catalog'] != 'community-operators':
                break
    return name, source, defaultchannel, csv, description, target_namespace, crd
