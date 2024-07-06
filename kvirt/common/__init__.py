# coding=utf-8

from ast import literal_eval
from datetime import datetime
from getpass import getuser
from hashlib import sha256
from kvirt.jinjafilters import jinjafilters
from kvirt.defaults import UBUNTUS, SSH_PUB_LOCATIONS, OPENSHIFT_TAG
from kvirt.kfish import Redfish
from kvirt.nameutils import get_random_name
from kvirt import version
from ipaddress import ip_address
from random import randint
import base64
from glob import glob
from grp import getgrgid
from jinja2 import Environment, FileSystemLoader
from jinja2 import StrictUndefined as undefined
from jinja2.exceptions import TemplateSyntaxError, TemplateError, TemplateNotFound
import re
import socket
import ssl
from urllib.parse import quote
from urllib.request import urlretrieve, urlopen, Request
import json
import os
import sys
from subprocess import call
from shutil import copy2, move, which
from tempfile import TemporaryDirectory
from time import sleep
import yaml


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


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
        if url.startswith('https://github.com'):
            url = github_raw(url)
        urlopen(url)
        return True
    except:
        return False


def github_raw(url):
    decomposed_url = url.split('/')
    user = decomposed_url[3]
    repo = decomposed_url[4]
    if decomposed_url[5] == 'blob':
        branch = decomposed_url[6]
        relativepath = decomposed_url[7:]
    else:
        branch = 'main'
        relativepath = decomposed_url[5:]
    relativepath = '/'.join(relativepath)
    url = f'https://raw.githubusercontent.com/{user}/{repo}/{branch}/{relativepath}'
    return url


def fetch(url, path):
    if url.startswith('https://github.com'):
        url = github_raw(url)
    shortname = os.path.basename(url)
    pathcreated = False
    if not os.path.exists(path):
        os.mkdir(path)
        pathcreated = True
    try:
        urlretrieve(url, f"{path}/{shortname}")
    except:
        if not url.endswith('_default.yml'):
            error(f"Hit issue with url {url}")
            if pathcreated:
                os.rmdir(path)
        sys.exit(1)


def cloudinit(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, files=[], enableroot=True,
              overrides={}, fqdn=False, storemetadata=True, image=None, ipv6=[],
              machine='pc', vmuser=None):
    userdata, metadata, netdata = None, None, None
    default_gateway = gateway
    noname = overrides.get('noname', False)
    legacy = True if image is not None and (is_7(image) or is_debian9(image)) else False
    prefix = 'eth'
    if image is not None and (is_ubuntu(image) or is_debian_new(image)):
        if machine == 'pc':
            prefix = 'ens'
        elif machine == 's390-ccw-virtio':
            prefix = 'enc'
        elif machine == 'vsphere':
            prefix = 'ens19'
        else:
            prefix = 'enp1s'
    dns_hack = True if image is not None and is_debian_new(image) else False
    netdata = {} if not legacy else ''
    bridges = {}
    vlans = {}
    if nets:
        for index, netinfo in enumerate(nets):
            if isinstance(netinfo, str):
                net = {'name': netinfo}
            elif isinstance(netinfo, dict):
                net = netinfo.copy()
            else:
                error(f"Wrong net entry {index}")
                sys.exit(1)
            if 'name' not in net:
                error(f"Missing name in net {index}")
                sys.exit(1)
            netname = net['name']
            if index == 0 and 'type' in net and net.get('type') != 'virtio':
                prefix = 'ens'
            nicname = net.get('nic')
            if nicname is None:
                if prefix.startswith('ens19'):
                    nicname = f"ens{192 + 32 * index}"
                elif prefix.startswith('ens'):
                    nicname = f"{prefix}{index + 3}"
                elif prefix.startswith('enc'):
                    nicname = f"{prefix}{index + 1}"
                else:
                    nicname = f"{prefix}{index}"
            ip = net.get('ip')
            netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
            noconf = net.get('noconf')
            vips = net.get('vips', [])
            enableipv6 = net.get('ipv6', False)
            dualstack = index == 0 and (net.get('dualstack', False) or overrides.get('dualstack', False))
            vlan = net.get('vlan')
            bridge = net.get('bridge', False)
            bridgename = net.get('bridgename', netname)
            if bridge:
                if legacy:
                    netdata += f"  auto {nicname}\n"
                    netdata += f"  iface {nicname} inet manual\n"
                    netdata += f"  auto {bridgename}\n"
                    netdata += f"  iface {bridgename} inet dhcp\n"
                    netdata += f"     bridge_ports {nicname}\n"
                else:
                    bridges[bridgename] = {'interfaces': [nicname]}
                realnicname = nicname
                nicname = bridgename
            if legacy:
                if vlan is not None:
                    nicname += f'.{vlan}'
                netdata += f"  auto {nicname}\n"
            if noconf is not None:
                if legacy:
                    netdata += f"  iface {nicname} inet manual\n"
                else:
                    targetfamily = 'dhcp6' if netname in ipv6 else 'dhcp4'
                    netdata[nicname] = {targetfamily: False}
            elif ip is not None and netmask is not None:
                if legacy:
                    netdata += f"  iface {nicname} inet static\n"
                    netdata += f"  address {ip}\n"
                    netdata += f"  netmask {netmask}\n"
                else:
                    if str(netmask).isnumeric():
                        cidr = netmask
                    else:
                        cidr = netmask_to_prefix(netmask)
                    dhcp = 'dhcp6' if ':' in ip else 'dhcp4'
                    netdata[nicname] = {dhcp: False, 'addresses': [f"{ip}/{cidr}"]}
                gateway = net.get('gateway')
                if index == 0 and default_gateway is not None:
                    gateway_name = 'gateway6' if ':' in default_gateway else 'gateway4'
                    if legacy:
                        netdata += f"  gateway {default_gateway}\n"
                    else:
                        netdata[nicname][gateway_name] = default_gateway
                elif gateway is not None:
                    gateway_name = 'gateway6' if ':' in gateway else 'gateway4'
                    if legacy:
                        netdata += f"  gateway {gateway}\n"
                    else:
                        netdata[nicname][gateway_name] = gateway
                dns = net.get('dns', gateway)
                if not legacy:
                    netdata[nicname]['nameservers'] = {}
                if dns is not None:
                    if legacy:
                        if isinstance(dns, list):
                            dns = ' '.join(dns)
                        netdata += f"  dns-nameservers {dns}\n"
                    else:
                        if isinstance(dns, str):
                            dns = dns.split(',')
                        netdata[nicname]['nameservers']['addresses'] = dns
                    if dns_hack:
                        dnscontent = f"nameserver {dns}\n"
                        dnsdata = {'path': 'etc/resolvconf/resolv.conf.d/base', 'content': dnscontent}
                        if files:
                            files.append(dnsdata)
                        else:
                            files = [dnsdata]
                        cmds.append('systemctl restart resolvconf')
                netdomain = net.get('domain')
                if netdomain is not None:
                    if legacy:
                        netdata += f"  dns-search {netdomain}\n"
                    else:
                        netdata[nicname]['nameservers']['search'] = [netdomain]
                if not legacy and not netdata[nicname]['nameservers']:
                    del netdata[nicname]['nameservers']
                if isinstance(vips, list) and vips:
                    for index, vip in enumerate(vips):
                        if legacy:
                            netdata += "  auto %s:%s\n  iface %s:%s inet static\n  address %s\n  netmask %s\n"\
                                % (nicname, index, nicname, index, vip, netmask)
                        else:
                            netdata[nicname]['addresses'].append(f"{vip}/{netmask}")
            else:
                if legacy:
                    if not bridge:
                        netdata += f"  iface {nicname} inet dhcp\n"
                else:
                    if dualstack or enableipv6 or netname in ipv6:
                        targetfamily = 'dhcp6'
                        if net.get('ipv6_stateless', False):
                            nmcontent = "[main]\nrc-manager=file\n[connection]\nipv6.dhcp-duid=ll\nipv6.dhcp-iaid=mac"
                            files.append({'path': '/etc/NetworkManager/conf.d/ipv6.conf', 'content': nmcontent})
                            cmds.insert(0, "systemctl restart NetworkManager")
                    else:
                        targetfamily = 'dhcp4'
                    netdata[nicname] = {targetfamily: True}
                    if dualstack:
                        dualfamily = 'dhcp6' if targetfamily == 'dhcp4' else 'dhcp4'
                        netdata[nicname][dualfamily] = True
            if bridge and not legacy:
                bridges[bridgename].update(netdata[nicname])
                del netdata[nicname]
                netdata[realnicname] = {'match': {'name': realnicname}}
            if vlan is not None and not legacy:
                vlan_name = f'vlan{vlan}'
                vlans[vlan_name] = {'id': int(vlan), 'link': nicname}
                vlans[vlan_name].update(netdata[nicname])
                targetfamily = 'dhcp6' if netname in ipv6 else 'dhcp4'
                netdata[nicname] = {targetfamily: False}
    if domain is not None:
        localhostname = f"{name}.{domain}"
    else:
        localhostname = name
    metadata = {"instance-id": localhostname, "local-hostname": localhostname} if not noname else {}
    if legacy and netdata != '':
        metadata["network-interfaces"] = netdata
    metadata = json.dumps(metadata)
    if not legacy:
        if netdata or bridges or vlans:
            final_netdata = {'version': 2}
            if netdata:
                final_netdata['ethernets'] = netdata
            if bridges:
                final_netdata['bridges'] = bridges
            if vlans:
                final_netdata['vlans'] = vlans
            netdata = yaml.safe_dump(final_netdata, default_flow_style=False, encoding='utf-8').decode("utf-8")
        else:
            netdata = ''
    else:
        netdata = None
    existing = overrides.get('cloudinit_file', f"{name}.cloudinit")
    if container_mode():
        existing = f"/workdir/{existing}"
    if os.path.exists(existing):
        pprint(f"using cloudinit from existing {existing} for {name}")
        userdata = open(existing).read()
    else:
        publickeyfile = get_ssh_pub_key()
        publictempkeyfile = None
        tempkeydir = overrides.get('tempkeydir')
        if overrides.get('tempkey', False) and tempkeydir is not None:
            if not keys:
                warning("No extra keys specified along with tempkey one, you might have trouble accessing the vm")
            privatetempkeyfile = f"{tempkeydir.name}/id_rsa"
            publictempkeyfile = f"{privatetempkeyfile}.pub"
            if not os.path.exists(privatetempkeyfile):
                tempkeycmd = f"yes '' | ssh-keygen -q -t rsa -N '' -C 'temp-kcli-key' -f {privatetempkeyfile}"
                tempkeycmd += " >/dev/null 2>&1 || true"
                call(tempkeycmd, shell=True)
        userdata = '#cloud-config\n'
        userdata += 'final_message: kcli boot finished, up $UPTIME seconds\n'
        if not noname:
            userdata += f'hostname: {name}\n'
            userdata += 'create_hostname_file: true\n'
            if fqdn:
                fqdn = f"{name}.{domain}" if domain is not None else name
                userdata += f"fqdn: {fqdn}\n"
        userdata += "ssh_pwauth: true\n"
        if enableroot:
            userdata += "disable_root: false\n"
            rootpassword = [e for e in cmds if 'root' in e and 'chpasswd' in e]
            if rootpassword:
                userdata += "lock_passwd: false\n"
                cmds.append("sed -i 's/.*PermitRootLogin .*/PermitRootLogin yes/' /etc/ssh/sshd_config")
                cmds.append("systemctl restart sshd")
        validkeyfound = False
        if keys or publickeyfile is not None or publictempkeyfile is not None:
            userdata += "ssh_authorized_keys:\n"
            validkeyfound = True
        elif which('ssh-add') is not None:
            agent_keys = os.popen('ssh-add -L 2>/dev/null | grep ssh | head -1').readlines()
            if agent_keys:
                keys = agent_keys
                validkeyfound = True
        if not validkeyfound:
            warning("no valid public keys found in .ssh/.kcli directories, you might have trouble accessing the vm")
        good_keys = []
        if keys:
            for key in list(set(keys)):
                if os.path.exists(os.path.expanduser(key)):
                    keypath = os.path.expanduser(key)
                    newkey = open(keypath, 'r').read().rstrip()
                else:
                    newkey = key.rstrip()
                if not newkey.startswith('ssh-') and not newkey.startswith('ecdsa-'):
                    warning(f"Skipping invalid ssh key {key}")
                    continue
                else:
                    good_keys.append(newkey)
                userdata += f"- {newkey}\n"
        elif publickeyfile is not None:
            publickey = open(publickeyfile, 'r').read().rstrip()
            if publickey not in keys:
                good_keys.append(publickey)
                userdata += f"- {publickey}\n"
        if publictempkeyfile is not None:
            tempkey = open(publictempkeyfile, 'r').read()
            if tempkey not in keys:
                good_keys.append(tempkey)
                userdata += f"- {tempkey}\n"
        if vmuser is not None:
            userdata += """users:
- name: {vmuser}
  sudo: ALL=(ALL) NOPASSWD:ALL
  groups: users, admin
  home: /home/{vmuser}
  shell: /bin/bash
  lock_passwd: false\n""".format(vmuser=vmuser)
            if good_keys:
                userdata += "  ssh-authorized-keys:\n"
                for key in good_keys:
                    userdata += f"  - {key}\n"
        if cmds:
            data = process_cmds(cmds, overrides)
            if data != '':
                userdata += "runcmd:\n"
                userdata += data
                userdata += "package_update: false\npackage_upgrade: false\n"
        if storemetadata and overrides:
            storeoverrides = {key: overrides[key] for key in overrides if not key.startswith('config_')}
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
    if os.path.exists(os.path.expanduser('~/.kcli/cloudinit.yml')):
        with open(os.path.expanduser('~/.kcli/cloudinit.yml')) as f:
            oridata = yaml.safe_load(f)
            oridata.update(yaml.safe_load(userdata))
            userdata = "#cloud-config\n" + yaml.dump(oridata, default_flow_style=False, indent=2)
    return userdata.strip(), metadata, netdata


def process_files(files=[], overrides={}, remediate=False):
    data = [] if remediate else ''
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
                files.append({'path': f'{path}/.k', 'content': ''})
            else:
                for entry in entries:
                    if os.path.isdir(entry):
                        subentries = os.listdir(entry)
                        if not subentries:
                            files.append({'path': f'{path}/{entry}/.k', 'content': ''})
                        else:
                            for subentry in subentries:
                                if os.path.isdir(subentry):
                                    continue
                                else:
                                    subpath = f"{path}/{entry}/{subentry}"
                                    subpath = subpath.replace('//', '/')
                                    mode = oct(os.stat(f"{origin}/{entry}/{subentry}").st_mode)[-3:]
                                    files.append({'path': subpath, 'origin': f"{origin}/{entry}/{subentry}",
                                                  'mode': mode})
                    else:
                        subpath = f"{path}/{entry}"
                        subpath = subpath.replace('//', '/')
                        files.append({'path': subpath, 'origin': f"{origin}/{entry}"})
    for directory in todelete:
        files.remove(directory)
    processed_files = []
    for fil in files:
        if not isinstance(fil, dict):
            continue
        origin = fil.get('origin')
        content = fil.get('content')
        path = fil.get('path')
        binary = False
        if path in processed_files:
            continue
        else:
            processed_files.append(path)
        owner = fil.get('owner', 'root')
        mode = fil.get('mode', '0600' if not path.endswith('sh') and not path.endswith('py') else '0700')
        permissions = fil.get('permissions', mode)
        render = fil.get('render', True)
        if isinstance(render, str):
            render = True if render.lower() == 'true' else False
        file_overrides = overrides.copy()
        file_overrides.update(fil)
        file_overrides.update({'env': os.environ})
        if origin is not None:
            origin = os.path.expanduser(origin)
            if overrides and render:
                basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                env = Environment(loader=FileSystemLoader(basedir), undefined=undefined, extensions=['jinja2.ext.do'],
                                  trim_blocks=True, lstrip_blocks=True)
                for jinjafilter in jinjafilters.jinjafilters:
                    env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
                try:
                    templ = env.get_template(os.path.basename(origin))
                    fileentries = templ.render(file_overrides)
                    content = [line.rstrip() for line in fileentries.split('\n')]
                except TemplateNotFound:
                    error(f"Origin file {os.path.basename(origin)} not found")
                    sys.exit(1)
                except TemplateSyntaxError as e:
                    error(f"Error rendering line {e.lineno} of origin file {e.filename}. Got: {e.message}")
                    sys.exit(1)
                except TemplateError as e:
                    error(f"Error rendering origin file {origin}. Got: {e.message}")
                    sys.exit(1)
                except UnicodeDecodeError:
                    warning(f"Interpreting file {origin} as binary")
                    binary = True
                    content = base64.b64encode(open(origin, "rb").read())
            else:
                try:
                    content = [line.rstrip() for line in open(origin, 'r').readlines()]
                except UnicodeDecodeError:
                    warning(f"Interpreting file {origin} as binary")
                    binary = True
                    content = base64.b64encode(open(origin, "rb").read())
        if remediate:
            newcontent = "%s\n" % '\n'.join(content) if isinstance(content, list) else content
            data.append({'owner': owner, 'path': path, 'permissions': permissions, 'content': newcontent})
            continue
        data += f"- owner: {owner}:{owner}\n"
        data += f"  path: {path}\n"
        data += f"  permissions: '{permissions}'\n"
        if binary:
            data += "  content: !!binary | \n     %s\n" % str(content, "utf-8")
        else:
            data += "  content: | \n"
            if isinstance(content, str):
                content = content.split('\n')
            for line in content:
                data += f"     {line}\n"
    return data


def _unique_list_dict(a):
    b = []
    for e in a:
        if e not in b:
            b.append(e)
        else:
            continue
    return b


def process_ignition_files(files=[], overrides={}):
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
                if os.path.isfile(f"{origin}/{subfil}"):
                    mode = oct(os.stat(f"{origin}/{subfil}").st_mode)[-3:]
                    files.append({'path': f'{path}/{subfil}', 'origin': f"{origin}/{subfil}", 'mode': mode})
            files.remove(directory)
    for fil in files:
        if not isinstance(fil, dict):
            continue
        origin = fil.get('origin')
        content = fil.get('content')
        path = fil.get('path')
        mode = int(str(fil.get('mode', '644')), 8)
        permissions = fil.get('permissions', mode)
        render = fil.get('render', True)
        if isinstance(render, str):
            render = True if render.lower() == 'true' else False
        if origin is not None:
            origin = os.path.expanduser(origin)
            if not os.path.exists(origin):
                print(f"Skipping file {origin} as not found")
                continue
            elif overrides and render:
                file_overrides = overrides.copy()
                file_overrides.update({'env': os.environ})
                basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                env = Environment(loader=FileSystemLoader(basedir), undefined=undefined, extensions=['jinja2.ext.do'])
                for jinjafilter in jinjafilters.jinjafilters:
                    env.filters[jinjafilter] = jinjafilters.jinjafilters[jinjafilter]
                try:
                    templ = env.get_template(os.path.basename(origin))
                    fileentries = templ.render(file_overrides)
                    content = [line for line in fileentries.split('\n')]
                except TemplateNotFound:
                    error(f"Origin file {os.path.basename(origin)} not found")
                    sys.exit(1)
                except TemplateSyntaxError as e:
                    error(f"Error rendering line {e.lineno} of origin file {e.filename}. Got: {e.message}")
                    sys.exit(1)
                except TemplateError as e:
                    error(f"Error rendering origin file {origin}. Got: {e.message}")
                    sys.exit(1)
                except UnicodeDecodeError:
                    warning(f"Skipping file {origin} as binary")
                    continue
            else:
                try:
                    content = open(origin, 'r').readlines()
                except UnicodeDecodeError:
                    warning(f"SKipping file {origin} as binary")
                    continue
        elif content is None:
            continue
        if not isinstance(content, str):
            content = '\n'.join(content) + '\n'
        if path.endswith('.service'):
            unitsdata.append({"contents": content, "name": os.path.basename(path), "enabled": True})
        else:
            content = base64.b64encode(content.encode()).decode("UTF-8")
            filesdata.append({'path': path, 'mode': permissions, 'overwrite': True,
                              "contents": {"source": f"data:text/plain;charset=utf-8;base64,{content}",
                                           "verification": {}}})
    return _unique_list_dict(filesdata), _unique_list_dict(unitsdata)


def process_cmds(cmds, overrides):
    data = ''
    for cmd in cmds:
        if cmd.startswith('#'):
            continue
        else:
            try:
                newcmd = Environment(undefined=undefined).from_string(cmd).render(overrides)
                data += "- %s\n" % newcmd.replace(": ", "':' ")
            except TemplateError as e:
                error(f"Error rendering cmd {cmd}. Got: {e.message}")
                sys.exit(1)
    return data


def process_ignition_cmds(cmds, overrides):
    path = '/usr/local/bin/first.sh'
    permissions = '700'
    content = ''
    for cmd in cmds:
        try:
            newcmd = Environment(undefined=undefined).from_string(cmd).render(overrides)
            content += f"{newcmd}\n"
        except TemplateError as e:
            error(f"Error rendering cmd {cmd}. Got: {e.message}")
            sys.exit(1)
    if content == '':
        return content
    else:
        if not content.startswith('#!'):
            content = f"#!/bin/sh\n{content}"
        content = base64.b64encode(content.encode()).decode("UTF-8")
        data = {'path': path, 'mode': int(permissions, 8),
                "contents": {"source": f"data:text/plain;charset=utf-8;base64,{content}", "verification": {}}}
        return data


def process_combustion_cmds(cmds, overrides):
    content = '#!/bin/bash\n' if cmds else ''
    for cmd in cmds:
        try:
            newcmd = Environment(undefined=undefined).from_string(cmd).render(overrides)
            content += f"{newcmd}\n"
        except TemplateError as e:
            error(f"Error rendering cmd {cmd}. Got: {e.message}")
            sys.exit(1)
    return content


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def pprint(text):
    color = '36'
    print(f'\033[{color}m{text}\033[0m')


def error(text):
    color = '31'
    print(f'\033[{color}m{text}\033[0m', file=sys.stderr)


def success(text):
    color = '32'
    print(f'\033[{color}m{text}\033[0m')


def warning(text):
    color = '33'
    print(f'\033[{color}m{text}\033[0m')


def info2(text):
    color = '36'
    print(f'\033[{color}mINFO\033[0m {text}')


def handle_response(result, name, quiet=False, element='', action='deployed', client=None):
    code = 0
    if not isinstance(result, dict):
        result = {'result': result.result, 'reason': result.reason}
    if result['result'] == 'success':
        if not quiet:
            response = f"{element} {name} {action}"
            if client is not None:
                response += f" on {client}"
            success(response.lstrip())
    elif result['result'] == 'failure':
        if not quiet:
            response = f"{element} {name} not {action} because {result['reason']}"
            error(response.lstrip())
        code = 1
    return code


def confirm(message):
    message = f"{message} [y/N]: "
    try:
        _input = input(message)
        if _input.lower() not in ['y', 'yes']:
            error("Leaving...")
            sys.exit(1)
    except:
        sys.exit(1)
    return


def get_lastvm(client, quiet=False):
    if 'HOME' not in os.environ:
        error("HOME variable not set")
        sys.exit(1)
    lastvm = f"{os.environ.get('HOME')}/.kcli/vm"
    if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
        for line in open(lastvm).readlines():
            line = line.split(' ')
            if len(line) != 2:
                continue
            cli = line[0].strip()
            vm = line[1].strip()
            if cli == client:
                if not quiet:
                    pprint(f"Using {vm} from {cli} as vm")
                return vm
    error("Missing Vm's name")
    sys.exit(1)


def set_lastvm(name, client):
    if 'HOME' not in os.environ:
        return
    configdir = f"{os.environ.get('HOME')}/.kcli"
    vmfile = f"{configdir}/vm"
    if not os.path.exists(configdir):
        os.mkdir(configdir)
    if not os.path.exists(vmfile) or os.stat(vmfile).st_size == 0:
        with open(vmfile, 'w') as f:
            f.write(f"{client} {name}")
        return
    with open(vmfile, 'r') as original:
        data = original.read()
    with open(vmfile, 'w') as modified:
        modified.write(f"{client} {name}\n{data}")


def delete_lastvm(name, client):
    if 'HOME' not in os.environ:
        return
    configdir = f"{os.environ.get('HOME')}/.kcli"
    vmfile = f"{configdir}/vm"
    if os.path.exists(configdir) and os.path.exists(vmfile):
        deletecmd = "sed -i ''" if os.path.exists('/Users') and 'gnu' not in which('sed') else "sed -i"
        deletecmd += f" '/{client} {name}/d' {configdir}/vm"
        os.system(deletecmd)


def remove_duplicates(oldlist):
    newlist = []
    for item in oldlist:
        if item not in newlist:
            newlist.append(item)
    return newlist


def get_overrides(paramfile=None, param=[]):
    overrides = {}
    if paramfile is not None:
        if os.path.exists(os.path.expanduser(paramfile)):
            with open(os.path.expanduser(paramfile)) as f:
                try:
                    overrides = yaml.safe_load(f)
                except:
                    error(f"Couldn't parse your parameters file {paramfile}. Leaving")
                    sys.exit(1)
        else:
            error(f"Parameter file {paramfile} not found. Leaving")
            sys.exit(1)
    if not isinstance(overrides, dict):
        error(f"Couldn't parse your parameters file {paramfile}. Leaving")
        sys.exit(1)
    if param is not None:
        processed_keys = []
        for x in param:
            if len(x.split('=')) < 2:
                error(f"Wrong parameter {x}. Should be key=value")
                sys.exit(1)
            else:
                if len(x.split('=')) == 2:
                    key, value = x.split('=')
                else:
                    split = x.split('=')
                    key = split[0]
                    value = x.replace(f"{key}=", '')
                if key in processed_keys:
                    error(f"Repeated parameter {key}")
                    sys.exit(1)
                else:
                    processed_keys.append(key)
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
    required = [key for key in overrides if isinstance(overrides[key], str) and overrides[key] == '?required']
    if required:
        error("A value needs to be set for the following parameters: %s" % ' '.join(required))
        sys.exit(1)
    return overrides


def get_parameters(inputfile, planfile=False):
    results = {}
    with open(inputfile, 'r') as entries:
        try:
            data = yaml.safe_load(entries)
            if not planfile:
                results = data
            elif 'parameters' in data:
                results = results['parameters']
        except Exception as e:
            if not planfile:
                error(f"Error rendering parameters from file {inputfile}. Got {e}")
                sys.exit(1)
            parameters = ""
            found = False
            with open(inputfile, 'r') as fic:
                lines = fic.readlines()
            for line in lines:
                if found and not line.startswith(' '):
                    break
                elif found:
                    parameters += line
                elif line != 'parameters:\n' and not found:
                    continue
                else:
                    parameters += line
                    found = True
            if parameters != '':
                try:
                    results = yaml.safe_load(parameters)['parameters']
                except:
                    pass
        if not isinstance(results, dict):
            error(f"Error rendering parameters from file {inputfile}")
            sys.exit(1)
        required = [key for key in results if isinstance(results[key], str) and results[key] == '?required']
        if required:
            error("A value needs to be set for the following parameters: %s" % ' '.join(required))
            sys.exit(1)
        return results


def print_info(yamlinfo, output='plain', fields=[], values=False, pretty=True):
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
    elif output == 'json':
        return json.dumps(yamlinfo)
    else:
        result = ''
        orderedfields = ['debug', 'name', 'project', 'namespace', 'id', 'instanceid', 'creationdate', 'owner', 'host',
                         'status', 'description', 'autostart', 'image', 'user', 'plan', 'profile', 'flavor', 'cpus',
                         'memory', 'nets', 'ip', 'ips', 'disks', 'snapshots']
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
                        nets += f"net interface: {device} mac: {mac} net: {network} type: {network_type}\n"
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
                        snaps += f"snapshot: {snapshot} current: {current}\n"
                    value = snaps.rstrip()
                if values or key in ['disks', 'nets']:
                    result += f"{value}\n"
                else:
                    result += f"{key}: {value}\n"
        return result.rstrip()


def ssh(name, ip='', user=None, local=None, remote=None, tunnel=False, tunnelhost=None, tunnelport=22,
        tunneluser='root', insecure=False, cmd=None, X=False, Y=False, debug=False, D=None, vmport=None,
        identityfile=None, password=True):
    if ip == '':
        return None
    else:
        sshcommand = f"{user}@{ip}"
        if identityfile is None:
            publickeyfile = get_ssh_pub_key()
            if publickeyfile is not None:
                identityfile = publickeyfile.replace('.pub', '')
        if not password:
            sshcommand = f"-o PasswordAuthentication=no {sshcommand}"
        if identityfile is not None:
            sshcommand = f"-i {identityfile} {sshcommand}"
        if D:
            sshcommand = f"-D {D} {sshcommand}"
        if X:
            sshcommand = f"-X {sshcommand}"
        if Y:
            sshcommand = f"-Y {sshcommand}"
        if cmd:
            sshcommand = f'{sshcommand} "{cmd}"'
        if tunnelhost is not None and tunnelhost not in ['localhost', '127.0.0.1'] and tunnel and\
                tunneluser is not None:
            if insecure:
                tunnelcommand = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=ERROR "
            else:
                tunnelcommand = ""
            tunnelcommand += f"-qp {tunnelport} -W %h:%p {tunneluser}@{tunnelhost}"
            if identityfile is not None:
                tunnelcommand = f"-i {identityfile} {tunnelcommand}"
            sshcommand = f"-o ProxyCommand='ssh {tunnelcommand}' {sshcommand}"
            if ':' in ip:
                sshcommand = sshcommand.replace(ip, f'[{ip}]')
        if local is not None:
            sshcommand = f"-L {local} {sshcommand}"
        if remote is not None:
            sshcommand = f"-R {remote} {sshcommand}"
        if vmport is not None:
            sshcommand = f"-p {vmport} {sshcommand}"
        if insecure:
            sshcommand = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=ERROR %s"\
                % sshcommand
        else:
            sshcommand = f"ssh {sshcommand}"
        if debug:
            pprint(sshcommand)
        return sshcommand


def scp(name, ip='', user=None, source=None, destination=None, recursive=None, tunnel=False, tunnelhost=None,
        tunnelport=22, tunneluser='root', debug=False, download=False, vmport=None, insecure=False, identityfile=None):
    if ip == '':
        print("No ip found. Cannot scp...")
    else:
        if ':' in ip:
            ip = f'[{ip}]'
        arguments = ''
        if tunnelhost is not None and tunnelhost not in ['localhost', '127.0.0.1'] and\
                tunnel and tunneluser is not None:
            h = "[%h]" if ':' in ip else "%h"
            arguments += f"-o ProxyCommand='ssh -qp {tunnelport} -W {h}:%p {tunneluser}@{tunnelhost}'"
        if insecure:
            arguments += " -o LogLevel=quiet -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        scpcommand = 'scp -q'
        if identityfile is None:
            publickeyfile = get_ssh_pub_key()
            if publickeyfile is not None:
                identityfile = publickeyfile.replace('.pub', '')
        if identityfile is not None:
            scpcommand += f" -i {identityfile}"
        if recursive:
            scpcommand = f"{scpcommand} -r"
        if vmport is not None:
            scpcommand = f"{scpcommand} -P {vmport}"
        if download:
            scpcommand += f" {arguments} {user}@{ip}:{source} {destination}"
        else:
            if os.path.isdir(source):
                arguments += ' -r'
            scpcommand += f" {arguments} {source} {user}@{ip}:{destination}"
        if debug:
            pprint(scpcommand)
        return scpcommand


def get_user(image):
    if 'gke' in image.lower():
        user = getuser()
    elif 'rhel' in image.lower() and not image.startswith('RHEL-'):
        user = 'cloud-user'
    elif 'centos9stream' in image.lower():
        user = 'cloud-user'
    elif 'centos' in image.lower() and not image.startswith('ibm'):
        user = 'centos'
    elif 'centos8stream' in image.lower():
        user = 'centos'
    elif 'coreos' in image.lower() or 'rhcos' in image.lower() or 'fcos' in image.lower() or 'ocp-v4' in image:
        user = 'core'
    elif 'debian' in image.lower():
        user = 'debian'
    elif [x for x in UBUNTUS if x in image.lower()] or 'ubuntu' in image.lower():
        user = 'ubuntu'
    elif 'fedora' in image.lower():
        user = 'fedora'
    elif 'arch' in image.lower():
        user = 'arch'
    elif 'freebsd' in image.lower():
        user = 'freebsd'
    elif 'netbsd' in image.lower():
        user = 'netbsd'
    elif 'openbsd' in image.lower():
        user = 'openbsd'
    elif 'cirros' in image.lower():
        user = 'cirros'
    else:
        user = 'root'
    return user


def get_cloudinitfile(image):
    lower = image.lower()
    cloudinitfile = '/var/log/cloud-init-output.log'
    if 'centos-7' in lower or 'centos7' in lower:
        cloudinitfile = '/var/log/messages'
    return cloudinitfile


def ignition(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, files=[], enableroot=True,
             overrides={}, iso=True, fqdn=False, version='3.1.0', plan=None, compact=False, removetls=False, ipv6=[],
             image=None, vmuser=None):
    noname = overrides.get('noname', False)
    nokeys = overrides.get('nokeys', False)
    separators = (',', ':') if compact else (',', ': ')
    indent = 0 if compact else 4
    default_gateway = gateway
    publickeys = []
    storage = {"files": []}
    systemd = {"units": []}
    if domain is not None:
        localhostname = f"{name}.{domain}"
    else:
        localhostname = name
    if not nokeys:
        if keys:
            for key in list(set(keys)):
                newkey = key
                if os.path.exists(os.path.expanduser(key)):
                    keypath = os.path.expanduser(key)
                    newkey = open(keypath, 'r').read().rstrip()
                if not newkey.startswith('ssh-'):
                    warning(f"Skipping invalid key {key}")
                    continue
                if newkey not in publickeys:
                    publickeys.append(newkey)
        else:
            publickeyfile = get_ssh_pub_key()
            if publickeyfile is not None:
                with open(publickeyfile, 'r') as ssh:
                    publickeys.append(ssh.read().strip())
        if not publickeys and which('ssh-add') is not None:
            agent_keys = os.popen('ssh-add -L 2>/dev/null | head -1').readlines()
            if agent_keys:
                publickeys = agent_keys
        if not publickeys:
            warning("no valid public keys found in .ssh/.kcli directories, you might have trouble accessing the vm")
    if not noname:
        hostnameline = quote(f"{localhostname}\n")
        storage["files"].append({"path": "/etc/hostname", "overwrite": True,
                                 "contents": {"source": f"data:,{hostnameline}", "verification": {}}, "mode": 420})
    if dns is not None:
        nmline = quote("[main]\ndhcp=dhclient\n")
        storage["files"].append({"path": "/etc/NetworkManager/conf.d/dhcp-client.conf", "overwrite": True,
                                 "contents": {"source": f"data:,{nmline}", "verification": {}}, "mode": 420})
        dnsline = quote(f"prepend domain-name-servers {dns};\nsend dhcp-client-identifier = hardware;\n")
        storage["files"].append({"path": "/etc/dhcp/dhclient.conf", "overwrite": True,
                                 "contents": {"source": f"data:,{dnsline}", "verification": {}}, "mode": 420})
    if nets:
        enpindex = 255
        for index, net in enumerate(nets):
            static_nic_file_mode = '755'
            netdata = ''
            if isinstance(net, str):
                if index == 0:
                    continue
                if image is not None and ('fcos' in image or 'fedora-coreos' in image):
                    nicname = f"eth{index}"
                else:
                    nicname = f"ens{index + 3}"
                ip = None
                netmask = None
                noconf = None
                vips = []
            elif isinstance(net, dict):
                if image is not None and ('fcos' in image or 'fedora-coreos' in image):
                    default_nicname = f"eth{index}"
                elif net.get('numa') is not None:
                    default_nicname = f"enp{enpindex}s0"
                    enpindex -= 2
                else:
                    default_nicname = f"ens{index + 3}"
                if image == 'custom_ipxe':
                    default_nicname = "ens3f1"
                nicname = net.get('nic', default_nicname)
                ip = net.get('ip')
                gateway = net.get('gateway')
                netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
                noconf = net.get('noconf')
                vlan = net.get('vlan')
                vips = net.get('vips')
            if vlan is not None:
                nicpath = f"/etc/sysconfig/network-scripts/ifcfg-{nicname}"
                netdata = f"DEVICE={nicname}\nNAME={nicname}\nONBOOT=no"
                static = quote(netdata)
                storage["files"].append({"path": nicpath, "contents": {"source": f"data:,{static}", "verification": {}},
                                         "mode": int(static_nic_file_mode, 8)})
                nicname += f'.{vlan}'
            nicpath = f"/etc/sysconfig/network-scripts/ifcfg-{nicname}"
            if noconf is not None:
                netdata = f"DEVICE={nicname}\nNAME={nicname}\nONBOOT=no"
            elif ip is not None and netmask is not None:
                if index == 0 and default_gateway is not None:
                    gateway = default_gateway
                if str(netmask).isnumeric():
                    cidr = netmask
                else:
                    cidr = netmask_to_prefix(netmask)
                netdata = f"DEVICE={nicname}\nNAME={nicname}\nONBOOT=yes\nNM_CONTROLLED=yes\n"
                netdata += f"BOOTPROTO=static\nIPADDR={ip}\nPREFIX={cidr}\n"
                if gateway is not None:
                    netdata += f"GATEWAY={gateway}\n"
                dns = net.get('dns', gateway)
                if dns is not None:
                    if isinstance(dns, str):
                        dns = dns.split(',')
                    for index, dnsentry in enumerate(dns):
                        netdata += f"DNS{index +1 }={dnsentry}\n"
                if vlan is not None:
                    netdata += "VLAN=yes\n"
                if isinstance(vips, list) and vips:
                    for vip in vips:
                        netdata += f"[Network]\nAddress={vip}/{netmask}\n"
                        if gateway is not None:
                            netdata += f"GATEWAY={gateway}\n"
                if image is not None and ('fcos' in image or 'fedora-coreos' in image):
                    netdata = f"[connection]\ntype=ethernet\ninterface-name={nicname}\n"
                    netdata += f"match-device=interface-name:{nicname}\n\n"
                    netdata += f"[ipv4]\nmethod=manual\naddresses={ip}/{netmask}\n"
                    if gateway is not None:
                        netdata += f"gateway={gateway}\n"
                    nicpath = f"/etc/NetworkManager/system-connections/{nicname}.nmconnection"
                    static_nic_file_mode = '0600'
            if netdata != '':
                static = quote(netdata)
                storage["files"].append({"path": nicpath, "contents": {"source": f"data:,{static}", "verification": {}},
                                         "mode": int(static_nic_file_mode, 8)})
    if files:
        filesdata, unitsdata = process_ignition_files(files=files, overrides=overrides)
        if filesdata:
            storage["files"].extend(filesdata)
        if unitsdata:
            systemd["units"].extend(unitsdata)
    cmdunit = None
    if cmds and not needs_combustion(image):
        cmdsdata = process_ignition_cmds(cmds, overrides)
        storage["files"].append(cmdsdata)
        firstpath = "/usr/local/bin/first.sh"
        content = f"[Service]\nType=oneshot\nExecStart={firstpath}\n[Install]\nWantedBy=multi-user.target\n"
        if 'need_network' in overrides:
            content += "[Unit]\nAfter=network-online.target\nWants=network-online.target\n"
        cmdunit = {"contents": content, "name": "first-boot.service", "enabled": True}
    if cmdunit is not None:
        systemd["units"].append(cmdunit)
    data = {'ignition': {'version': version, 'config': {}}, 'storage': storage, 'systemd': systemd,
            'passwd': {'users': []}}
    if publickeys:
        user = 'root' if 'susemicro' in image else 'fedora' if 'fedora' in image else 'core'
        data['passwd']['users'] = [{'name': user, 'sshAuthorizedKeys': publickeys}]
        if vmuser is not None:
            data['passwd']['users'].append({'name': vmuser, 'sshAuthorizedKeys': publickeys,
                                            'groups': ['sudo', 'wheel']})
    role = overrides.get('role')
    if len(name.split('-')) >= 3 and name.split('-')[-2] in ['ctlplane', 'worker']:
        role = name.split('-')[-2]
    elif len(name.split('-')) >= 2 and name.split('-')[-1] == 'bootstrap':
        role = name.split('-')[-1]
    if role is not None:
        cluster = overrides.get('cluster', plan)
        ignitionclusterpath = find_ignition_files(role, cluster=cluster)
        if ignitionclusterpath is not None:
            data = mergeignition(name, ignitionclusterpath, data)
        rolepath = f"/workdir/{plan}-{role}.ign" if container_mode() else f"{plan}-{role}.ign"
        if os.path.exists(rolepath):
            ignitionextrapath = rolepath
            data = mergeignition(name, ignitionextrapath, data)
    planpath = f"/workdir/{plan}.ign" if container_mode() else f"{plan}.ign"
    if os.path.exists(planpath):
        ignitionextrapath = planpath
        data = mergeignition(name, ignitionextrapath, data)
    namepath = overrides.get('ignition_file', f"{name}.ign")
    if container_mode():
        namepath = f"/workdir/{namepath}"
    if os.path.exists(namepath):
        ignitionextrapath = namepath
        data = mergeignition(name, ignitionextrapath, data)
    if removetls and 'config' in data['ignition'] and 'append' in data['ignition']['config'] and\
            data['ignition']['config']['append'][0]['source'].startswith("http://"):
        del data['ignition']['security']['tls']['certificateAuthorities']
    # remove duplicate files to please ignition v3
    paths = []
    storagefinal = []
    damned_paths = ['/etc/NetworkManager/dispatcher.d/30-local-dns-prepender']
    for fileentry in data['storage']['files']:
        path = fileentry['path']
        if 'metal3' in overrides and overrides['metal3'] and path in damned_paths:
            continue
        if path not in paths:
            storagefinal.append(fileentry)
            paths.append(path)
    data['storage']['files'] = storagefinal
    try:
        result = json.dumps(data, indent=indent, separators=separators, sort_keys=True)
    except:
        result = json.dumps(data, indent=indent, separators=separators)
    if compact:
        result = result.replace('\n', '')
    return result


def get_latest_fcos(url, _type='kvm', region=None):
    keys = {'ovirt': 'openstack', 'kubevirt': 'openstack', 'kvm': 'qemu', 'vsphere': 'vmware'}
    key = keys.get(_type, _type)
    _format = 'ova' if _type == 'vsphere' else 'qcow2.xz'
    with urlopen(url) as u:
        data = json.loads(u.read().decode())
        if _type == 'aws':
            return data['architectures']['x86_64']['images']['aws']['regions'][region]['image']
        elif _type == 'gcp':
            return data['architectures']['x86_64']['images']['gcp']['name']
        else:
            return data['architectures']['x86_64']['artifacts'][key]["formats"][_format]['disk']['location']


def get_latest_fcos_metal(url):
    with urlopen(url) as u:
        data = json.loads(u.read().decode())
        formats = data['architectures']['x86_64']['artifacts']['metal']['formats']
        kernel = formats['pxe']['kernel']['location']
        initrd = formats['pxe']['initramfs']['location']
        metal = formats['raw.xz']['disk']['location']
        return kernel, initrd, metal


def get_latest_rhcos(url, _type='kvm', arch='x86_64'):
    if _type in ['openstack', 'ovirt', 'kubevirt']:
        return f"{url}/latest/rhcos-openstack.{arch}.qcow2.gz"
    elif _type == 'vsphere':
        return f"{url}/latest/rhcos-vmware.{arch}.ova"
    elif _type == 'aws':
        return f"{url}/latest/rhcos-aws.{arch}.vmdk.gz"
    elif _type == 'gcp':
        return f"{url}/latest/rhcos-gcp.{arch}.qcow2.gz"
    elif _type == 'ibm':
        return f"{url}/latest/rhcos-ibmcloud.{arch}.qcow2.gz"
    else:
        return f"{url}/latest/rhcos-qemu.{arch}.qcow2.gz"


def get_commit_rhcos(commitid, _type='kvm', region=None):
    keys = {'ovirt': 'openstack', 'kubevirt': 'openstack', 'kvm': 'qemu', 'vsphere': 'vmware', 'ibm': 'ibmcloud'}
    key = keys.get(_type, _type)
    buildurl = f"https://raw.githubusercontent.com/openshift/installer/{commitid}/data/data/rhcos.json"
    with urlopen(buildurl) as b:
        data = json.loads(b.read().decode())
        if _type == 'aws':
            return data['amis'][region]['hvm']
        elif _type == 'gcp':
            return data['gcp']['image']
        else:
            baseuri = data['baseURI']
            path = f"{baseuri}{data['images'][key]['path']}"
            return path


def get_installer_rhcos(_type='kvm', region=None, arch='x86_64'):
    keys = {'ovirt': 'openstack', 'kubevirt': 'openstack', 'kvm': 'qemu', 'vsphere': 'vmware', 'ibm': 'ibmcloud'}
    key = keys.get(_type, _type)
    INSTALLER_COREOS = os.popen('openshift-install coreos print-stream-json 2>/dev/null').read()
    data = json.loads(INSTALLER_COREOS)
    if _type == 'aws':
        return data['architectures'][arch]['images']['aws']['regions'][region]['image']
    elif _type == 'azure':
        return data['architectures'][arch]['rhel-coreos-extensions']['azure-disk']['url']
    elif _type == 'gcp':
        return data['architectures'][arch]['images']['gcp']['name']
    else:
        _format = 'ova' if _type == 'vsphere' else 'qcow2.gz'
        return data['architectures'][arch]['artifacts'][key]['formats'][_format]['disk']['location']


def get_commit_rhcos_metal(commitid):
    buildurl = f"https://raw.githubusercontent.com/openshift/installer/{commitid}/data/data/rhcos.json"
    with urlopen(buildurl) as b:
        data = json.loads(b.read().decode())
        baseuri = data['baseURI']
        kernel = f"{baseuri}{data['images']['kernel']['path']}"
        initrd = f"{baseuri}{data['images']['initramfs']['path']}"
        metal = f"{baseuri}{data['images']['metal']['path']}"
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
    os.environ["PATH"] += f":{os.getcwd()}"
    if which('openshift-install') is None:
        error("Couldnt find openshift-install in your path")
        sys.exit(0)
    INSTALLER_COREOS = os.popen('openshift-install coreos print-stream-json 2>/dev/null').read()
    data = json.loads(INSTALLER_COREOS)
    return data['architectures']['x86_64']['artifacts']['metal']['formats']['iso']['disk']['location']


def get_installer_iso_sha():
    INSTALLER_COREOS = os.popen('openshift-install coreos print-stream-json 2>/dev/null').read()
    data = json.loads(INSTALLER_COREOS)
    return data['architectures']['x86_64']['artifacts']['metal']['formats']['iso']['disk']['sha256']


def get_latest_rhcos_metal(url):
    buildurl = f'{url}/builds.json'
    with urlopen(buildurl) as b:
        data = json.loads(b.read().decode())
        for build in data['builds']:
            build = build['id']
            kernel = f"{url}/{build}/x86_64/rhcos-{build}-installer-kernel-x86_64"
            initrd = f"{url}/{build}/x86_64/rhcos-{build}-installer-initramfs.x86_64.img"
            metal = f"{url}/{build}/x86_64/rhcos-{build}-metal.x86_64.raw.gz"
            return kernel, initrd, metal


def get_latest_fedora(arch='x86_64'):
    request = Request('https://fedoraproject.org/cloud/download/_payload.json', headers={'Accept': 'application/json'})
    for entry in json.loads(urlopen(request).read()):
        if isinstance(entry, str) and entry.startswith('Cloud') and arch in entry and 'qcow2' in entry:
            short = os.path.basename(entry)
            major = short.replace('Fedora-Cloud-Base-', '').split('-')[0]
            return f"https://download.fedoraproject.org/pub/fedora/linux/releases/{major}/Cloud/{arch}/images/{short}"


def find_ignition_files(role, cluster):
    clusterpath = os.path.expanduser(f"~/.kcli/clusters/{cluster}/{role}.ign")
    nodepoolpath = os.path.expanduser(f"~/.kcli/clusters/{cluster}/nodepool.ign")
    if os.path.exists(clusterpath):
        return clusterpath
    elif os.path.exists(nodepoolpath):
        return nodepoolpath
    else:
        return None


def pretty_print(o, value=False, width=None):
    data = yaml.dump(o, default_flow_style=False, indent=2, allow_unicode=True, Dumper=NoAliasDumper, width=width)
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
                error(f"Couldn't parse yaml in .kcli/config.yml. Got {err}")
                sys.exit(1)
        if name in oldini:
            pprint(f"Skipping existing Host {name}")
            return
        ini = oldini
    ini[name] = {k: data[k] for k in data if data[k] is not None}
    with open(path, 'w') as conf_file:
        try:
            yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                           sort_keys=False)
        except:
            yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    pprint(f"Using {name} as hostname")
    pprint(f"Host {name} created")


def delete_host(name):
    path = os.path.expanduser('~/.kcli/config.yml')
    if not os.path.exists(path):
        pprint(f"Skipping non existing Host {name}")
        return
    else:
        with open(path, 'r') as entries:
            try:
                ini = yaml.safe_load(entries)
            except yaml.scanner.ScannerError as err:
                error(f"Couldn't parse yaml in .kcli/config.yml. Got {err}")
                sys.exit(1)
        if name not in ini:
            pprint(f"Skipping non existing Host {name}")
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
        success(f"Host {name} deleted")


def get_binary(name, linuxurl, macosurl, compressed=False):
    if which(name) is not None:
        return which(name)
    binary = f'/var/tmp/{name}'
    if os.path.exists(binary):
        pprint(f"Using {name} from /var/tmp")
    else:
        pprint(f"Downloading {name} in /var/tmp")
        url = macosurl if os.path.exists('/Users') else linuxurl
        if compressed:
            downloadcmd = f"curl -L '{url}' | gunzip > {binary}"
        else:
            downloadcmd = f"curl -L '{url}' > {binary}"
        downloadcmd += f"; chmod u+x {binary}"
        os.system(downloadcmd)
    return binary


def _ssh_credentials(k, name):
    vmport = None
    info = k.info(name, debug=False)
    if not info:
        return None, None, None
    user, ip, status = info.get('user', 'root'), info.get('ip'), info.get('status')
    if status in ['down', 'suspended', 'unknown']:
        error(f"{name} down")
    if 'nodeport' in info:
        vmport = info['nodeport']
        nodehost = info.get('host')
        ip = k.node_host(name=nodehost)
        if ip is None:
            warning(f"Connecting to {name} using node fqdn")
            ip = nodehost
    elif 'loadbalancerip' in info:
        ip = info['loadbalancerip']
    if ip is None:
        error(f"No ip found for {name}")
    return user, ip, vmport


def mergeignition(name, ignitionextrapath, data):
    pprint(f"Merging ignition data from existing {ignitionextrapath} for {name}")
    with open(ignitionextrapath, 'r') as extra:
        try:
            ignitionextra = json.load(extra)
        except Exception as e:
            error(f"Couldn't process {ignitionextrapath}. Ignoring")
            error(e)
            sys.exit(1)
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
        if 'config' in data['ignition'] and data['ignition']['config']:
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
    result = f'/workdir/{x}' if container_mode() else x
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
    if f'{element}_{field}' in data:
        new = data[f'{element}_{field}']
        results.extend(new)
    return results


def is_debian9(image):
    return 'debian9' in image.lower()


def is_debian_new(image):
    return 'debian10' in image.lower() or 'debian12' in image.lower()


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
    return 'coreos' in image or 'rhcos' in image or 'fcos' in image or 'fedora-coreos' in image\
        or needs_combustion(image) or 'art-dev' in image


def needs_combustion(image):
    return 'susemicro' in image or 'SLE-Micro' in image


def ignition_version(image):
    version = '3.1.0'
    ignition_versions = {f"4{i}": '2.2.0' for i in range(6)}
    ignition_versions.update({46: '3.1.0', 47: '3.1.0', 48: '3.2.0'})
    image = os.path.basename(image)
    version_match = re.match('rhcos-*(..).*', image)
    if version_match is not None and isinstance(version_match.group(1), int):
        openshift_version = int(version_match.group(1))
        version = ignition_versions[openshift_version]
    return version


def create_embed_ignition_cmd(name, poolpath, baseiso, extra_args=None):
    coreosinstaller = f"podman run --privileged --rm -w /data -v {poolpath}:/data -v /dev:/dev"
    if not os.path.exists('/Users'):
        coreosinstaller += " -v /run/udev:/run/udev"
    coreosinstaller += " quay.io/coreos/coreos-installer:release"
    isocmd = f"{coreosinstaller} iso ignition embed -fi iso.ign -o {name} {baseiso}"
    if extra_args is not None:
        isocmd += f"; {coreosinstaller} iso kargs modify -a '{extra_args}' {baseiso}"
    return isocmd


def get_hypershift(version='latest', macosx=False):
    if which('podman') is None:
        error("Please install podman first in order to install hypershift")
        return 1
    operator_image = version if '/' in version else f'quay.io/hypershift/hypershift-operator:{version}'
    hypercmd = f"podman pull {operator_image} ;"
    hypercmd += f"podman create --name hypershift-copy {operator_image} ;"
    hypercmd += "podman cp hypershift-copy:/usr/bin/hypershift . ;"
    hypercmd += "chmod 700 hypershift ;"
    hypercmd += "podman rm -f hypershift-copy"
    call(hypercmd, shell=True)


def get_kubectl(version='latest'):
    SYSTEM = 'darwin' if os.path.exists('/Users') else 'linux'
    pprint("Downloading kubectl in current directory")
    if version == 'latest':
        r = urlopen("https://storage.googleapis.com/kubernetes-release/release/stable.txt")
        version = str(r.read(), 'utf-8').strip()
    else:
        if not version.startswith('v'):
            version = f'v{version}'
        url = "https://api.github.com/repos/kubernetes/kubernetes/releases?per_page=1000"
        data = json.loads(urlopen(url, timeout=5).read())
        valid_versions = [line['tag_name'] for line in data]
        if version.count('.') == 1:
            latest = [v for v in valid_versions if v.startswith(version)]
            if latest:
                version = latest[0]
                pprint(f"Using version {version}")
            else:
                error(f"version {version} not available")
                return 1
        elif version not in valid_versions:
            error(f"version {version} not available")
            return 1
    kubecmd = "curl -LO https://storage.googleapis.com/kubernetes-release/release/%s/bin/%s/amd64/kubectl" % (version,
                                                                                                              SYSTEM)
    kubecmd += "; chmod 700 kubectl"
    call(kubecmd, shell=True)


def get_oc(version='stable', tag='4.13', macosx=False):
    SYSTEM = 'mac' if os.path.exists('/Users') else 'linux'
    arch = 'arm64' if os.uname().machine == 'aarch64' else 'x86_64'
    pprint("Downloading oc in current directory")
    occmd = "curl -Ls "
    el8 = os.path.exists('/etc/redhat-release') and 'release 8' in open('/etc/redhat-release').read()
    if el8:
        warning("Downloading 4.15 oc as you're using an el8 box")
        tag = '4.15.0'
    if str(tag).count('.') == 1:
        tag = f'latest-{tag}'
    occmd += f"https://mirror.openshift.com/pub/openshift-v4/{arch}/clients/ocp/{tag}/openshift-client-{SYSTEM}.tar.gz"
    occmd += "| tar zxf - oc"
    occmd += "; chmod 700 oc"
    call(occmd, shell=True)
    if container_mode():
        if macosx:
            occmd += f"https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/{tag}/"
            occmd += f"openshift-client-{SYSTEM}.tar.gz"
            occmd += "| tar zxf -C /workdir - oc"
            occmd += "; chmod 700 /workdir/oc"
            call(occmd, shell=True)
        else:
            move('oc', '/workdir/oc')


def get_oc_mirror(version='stable', tag='4.13', macosx=False):
    if os.path.exists('/Users'):
        error("oc-mirror is not available on Mac")
        sys.exit(1)
    arch = 'arm64' if os.uname().machine == 'aarch64' else 'x86_64'
    pprint("Downloading oc-mirror in current directory")
    mirrorcmd = "curl -Ls "
    if str(tag).count('.') == 1:
        tag = f'latest-{tag}'
    mirrorcmd += f"https://mirror.openshift.com/pub/openshift-v4/{arch}/clients/ocp/{tag}/oc-mirror.tar.gz"
    mirrorcmd += "| tar zxf - oc-mirror"
    mirrorcmd += "; chmod 700 oc-mirror"
    call(mirrorcmd, shell=True)
    if container_mode():
        move('oc-mirror', '/workdir/oc-mirror')


def get_helm(version='latest'):
    SYSTEM = 'darwin' if os.path.exists('/Users') else 'linux'
    pprint("Downloading helm in current directory")
    if version == 'latest':
        version = jinjafilters.github_version('helm/helm')
    elif not version.startswith('v'):
        version = f"v{version}"
    helmcmd = f"curl -Ls https://get.helm.sh/helm-{version}-{SYSTEM}-amd64.tar.gz |"
    helmcmd += f"tar zxf - --strip-components 1 {SYSTEM}-amd64/helm;"
    helmcmd += "chmod 700 helm"
    call(helmcmd, shell=True)


def kube_create_app(config, appname, appdir, overrides={}, outputdir=None):
    appdata = {'name': appname, 'cluster': 'mykube', 'domain': 'karmalabs.corp', 'ctlplanes': 1, 'workers': 0}
    cwd = os.getcwd()
    os.environ["PATH"] += f":{cwd}"
    overrides['cwd'] = cwd
    default_parameter_file = f"{appdir}/{appname}/kcli_default.yml"
    if os.path.exists(default_parameter_file):
        with open(default_parameter_file, 'r') as entries:
            appdefault = yaml.safe_load(entries)
            appdata.update(appdefault)
    appdata.update(overrides)
    cluster = appdata['cluster']
    with TemporaryDirectory() as tmpdir:
        app_files = glob(f'{appdir}/{appname}/*.sh')
        app_files.extend(glob(f'{appdir}/{appname}/*py'))
        app_files.extend(glob(f'{appdir}/{appname}/*.y*ml'))
        app_files = [os.path.basename(_fic) for _fic in app_files]
        for app_file in app_files:
            rendered = config.process_inputfile(cluster, f"{appdir}/{appname}/{app_file}", overrides=appdata)
            destfile = f"{outputdir if outputdir is not None else tmpdir}/{app_file}"
            with open(destfile, 'w') as f:
                f.write(rendered)
        if outputdir is None:
            os.chdir(tmpdir)
            result = call(f'bash {tmpdir}/install.sh', shell=True)
        else:
            pprint(f"Copied artifacts to {outputdir}")
            result = 0
    os.chdir(cwd)
    return result


def kube_delete_app(config, appname, appdir, overrides={}):
    appdata = {'name': appname, 'cluster': 'mykube', 'domain': 'karmalabs.corp', 'ctlplanes': 1, 'workers': 0}
    found = False
    cwd = os.getcwd()
    os.environ["PATH"] += f":{cwd}"
    overrides['cwd'] = cwd
    default_parameter_file = f"{appdir}/{appname}/kcli_default.yml"
    if os.path.exists(default_parameter_file):
        with open(default_parameter_file, 'r') as entries:
            appdefault = yaml.safe_load(entries)
            appdata.update(appdefault)
    appdata.update(overrides)
    cluster = appdata['cluster']
    with TemporaryDirectory() as tmpdir:
        app_files = glob(f'{appdir}/{appname}/*.sh')
        app_files.extend(glob(f'{appdir}/{appname}/*py'))
        app_files.extend(glob(f'{appdir}/{appname}/*.y*ml'))
        app_files = [os.path.basename(_fic) for _fic in app_files]
        for app_file in app_files:
            if app_file == 'uninstall.sh':
                found = True
            rendered = config.process_inputfile(cluster, f"{appdir}/{appname}/{app_file}", overrides=overrides)
            with open(f"{tmpdir}/{app_file}", 'w') as f:
                f.write(rendered)
        os.chdir(tmpdir)
        if not found:
            warning("Uninstall not supported for this app")
            result = 1
        else:
            result = call(f'bash {tmpdir}/uninstall.sh', shell=True)
    os.chdir(cwd)
    return result


def openshift_create_app(config, appname, appdir, overrides={}, outputdir=None):
    appdata = {'name': appname, 'cluster': 'myopenshift', 'domain': 'karmalabs.corp', 'ctlplanes': 1, 'workers': 0}
    install_cr = overrides.get('install_cr', True)
    cwd = os.getcwd()
    os.environ["PATH"] += f":{cwd}"
    overrides['cwd'] = cwd
    default_parameter_file = f"{appdir}/{appname}/kcli_default.yml"
    appdefault = {}
    if os.path.exists(default_parameter_file):
        with open(default_parameter_file, 'r') as entries:
            appdefault = yaml.safe_load(entries)
            appdata.update(appdefault)
            if 'namespace' in appdefault and 'namespace' in overrides:
                warning(f"Forcing namespace to {appdefault['namespace']}")
                del overrides['namespace']
    appdata.update(overrides)
    cluster = appdata['cluster']
    with TemporaryDirectory() as tmpdir:
        app_files = glob(f'{appdir}/{appname}/*.sh')
        app_files.extend(glob(f'{appdir}/{appname}/*py'))
        app_files.extend(glob(f'{appdir}/{appname}/*.y*ml'))
        app_files = [os.path.basename(_fic) for _fic in app_files]
        for app_file in app_files:
            rendered = config.process_inputfile(cluster, f"{appdir}/{appname}/{app_file}", overrides=appdata)
            destfile = f"{outputdir if outputdir is not None else tmpdir}/{app_file}"
            with open(destfile, 'w') as g:
                g.write(rendered)
        destfile = f"{outputdir if outputdir is not None else tmpdir}/install.yml"
        with open(destfile, 'w') as g:
            rendered = config.process_inputfile(cluster, f"{appdir}/install.yml.j2", overrides=appdata)
            g.write(rendered)
        destfile = f"{outputdir if outputdir is not None else tmpdir}/install.sh"
        with open(destfile, 'w') as f:
            f.write("oc create -f install.yml\n")
            if os.path.exists(f"{appdir}/{appname}/pre.sh"):
                f.write("bash pre.sh\n")
            if install_cr and os.path.exists(f"{appdir}/{appname}/cr.yml"):
                namespace = appdefault.get('namespace') or overrides.get('namespace')
                cr_overrides = {'csv': overrides.get('csv'), 'namespace': namespace}
                rendered = config.process_inputfile(cluster, f"{appdir}/cr.sh", overrides=cr_overrides)
                f.write(rendered)
            if os.path.exists(f"{appdir}/{appname}/post.sh"):
                f.write("\nbash post.sh\n")
        if outputdir is None:
            os.chdir(tmpdir)
            result = call('bash install.sh', shell=True)
        else:
            pprint(f"Copied artifacts to {outputdir}")
            result = 0
    os.chdir(cwd)
    return result


def openshift_delete_app(config, appname, appdir, overrides={}):
    appdata = {'name': appname, 'cluster': 'myopenshift', 'domain': 'karmalabs.corp', 'ctlplanes': 1, 'workers': 0}
    cwd = os.getcwd()
    os.environ["PATH"] += f":{cwd}"
    overrides['cwd'] = cwd
    default_parameter_file = f"{appdir}/{appname}/kcli_default.yml"
    if os.path.exists(default_parameter_file):
        with open(default_parameter_file, 'r') as entries:
            appdefault = yaml.safe_load(entries)
            appdata.update(appdefault)
            if 'namespace' in appdefault and 'namespace' in overrides:
                warning(f"Forcing namespace to {appdefault['namespace']}")
                del overrides['namespace']
    appdata.update(overrides)
    cluster = appdata['cluster']
    with TemporaryDirectory() as tmpdir:
        app_files = glob(f'{appdir}/{appname}/*.sh')
        app_files.extend(glob(f'{appdir}/{appname}/*py'))
        app_files.extend(glob(f'{appdir}/{appname}/*.y*ml'))
        app_files = [os.path.basename(_fic) for _fic in app_files]
        for app_file in app_files:
            rendered = config.process_inputfile(cluster, f"{appdir}/{appname}/{app_file}", overrides=appdata)
            destfile = f"{tmpdir }/{app_file}"
            with open(destfile, 'w') as g:
                g.write(rendered)
        destfile = f"{tmpdir}/install.yml"
        with open(destfile, 'w') as g:
            rendered = config.process_inputfile(cluster, f"{appdir}/install.yml.j2", overrides=appdata)
            g.write(rendered)
        destfile = f"{tmpdir}/uninstall.sh"
        with open(destfile, 'w') as f:
            if os.path.exists(f"{tmpdir}/cr.yml"):
                f.write("oc delete -f cr.yml\n")
            f.write("oc delete -f install.yml")
        os.chdir(tmpdir)
        result = call('bash uninstall.sh', shell=True)
    os.chdir(cwd)
    return result


def make_iso(name, tmpdir, userdata, metadata, netdata, openstack=False, combustion=False):
    with open(f"{tmpdir}/user-data", 'w') as x:
        x.write(userdata)
    with open(f"{tmpdir}/meta-data", 'w') as y:
        y.write(metadata)
    if which('mkisofs') is None and which('genisoimage') is None and which('xorrisofs') is None:
        error("mkisofs, genisoimage or xorrisofs are required in order to create cloudinit iso")
        sys.exit(1)
    isocmd = 'genisoimage' if which('genisoimage') is not None else 'mkisofs' if which('mkisofs') is not None\
        else 'xorrisofs'
    isocmd += f" --quiet -o {tmpdir}/{name}.ISO --volid cidata"
    if combustion:
        os.makedirs(f"{tmpdir}/root/ignition")
        move(f"{tmpdir}/user-data", f"{tmpdir}/root/ignition/config.ign")
        if os.path.exists(f"{tmpdir}/combustion_script"):
            os.makedirs(f"{tmpdir}/root/combustion")
            move(f"{tmpdir}/combustion_script", f"{tmpdir}/root/combustion/script")
        isocmd += f" -V ignition --joliet --rock {tmpdir}/root"
    elif openstack:
        os.makedirs(f"{tmpdir}/root/openstack/latest")
        move(f"{tmpdir}/user-data", f"{tmpdir}/root/openstack/latest/user_data")
        if os.path.getsize(f"{tmpdir}/meta-data") == 0:
            open(f"{tmpdir}/meta-data", 'w').write('{}')
        move(f"{tmpdir}/meta-data", f"{tmpdir}/root/openstack/latest/meta_data.json")
        isocmd += f" -V config-2 --joliet --rock {tmpdir}/root"
    else:
        isocmd += f" --joliet --rock {tmpdir}/user-data {tmpdir}/meta-data"
    if netdata is not None:
        with open(f"{tmpdir}/network-config", 'w') as z:
            z.write(netdata)
        if openstack:
            move(f"{tmpdir}/network-config", f"{tmpdir}/root/openstack/latest/network_config.json")
        else:
            isocmd += f" {tmpdir}/network-config"
    isocmd += f" >/dev/null 2>{tmpdir}/error.log"
    return os.system(isocmd)


def filter_compression_extension(name):
    return name.replace('.gz', '').replace('.xz', '').replace('.bz2', '')


def generate_rhcos_iso(k, cluster, pool, version='latest', installer=False, arch='x86_64', extra_args=None):
    if installer:
        liveiso = get_installer_iso()
        baseiso = os.path.basename(liveiso)
    else:
        baseiso = f'rhcos-live.{arch}.iso'
        path = f'{version}/latest' if version != 'latest' else 'latest'
        liveiso = f"https://mirror.openshift.com/pub/openshift-v4/{arch}/dependencies/rhcos/{path}/{baseiso}"
    kubevirt = 'kubevirt' in str(type(k))
    openstack = 'openstack' in str(type(k))
    vsphere = 'vsphere' in str(type(k))
    proxmox = 'proxmox' in str(type(k))
    name = f'{cluster}-iso' if kubevirt else f'{cluster}.iso'
    if name in [os.path.basename(iso) for iso in k.volumes(iso=True)]:
        warning(f"Deleting old iso {name}")
        k.delete_image(name)
    if kubevirt:
        pprint(f"Creating iso {name}")
        k.add_image(liveiso, pool, name=name)
        isocmd = "coreos-installer iso ignition embed -fi /files/iso.ign /storage/disk.img"
        pvc = name.replace('_', '-').replace('.', '-').lower()
        pprint(f"Patching iso {name} with ignition")
        k.patch_pvc(pvc, isocmd, image="quay.io/coreos/coreos-installer:release", files=['iso.ign'])
        k.update_cdi_endpoint(pvc, f'{cluster}.iso')
        return
    if openstack or vsphere or proxmox:
        pprint(f"Creating iso {name}")
        baseisocmd = f"curl -L {liveiso} -o /tmp/{os.path.basename(liveiso)}"
        call(baseisocmd, shell=True)
        copy2('iso.ign', '/tmp')
        isocmd = create_embed_ignition_cmd(name, '/tmp', baseiso, extra_args=extra_args)
        os.system(isocmd)
        result = k.add_image(f'/tmp/{name}', pool, name=name)
        os.remove(f'/tmp/{os.path.basename(liveiso)}')
        os.remove(f'/tmp/{name}')
        if result['result'] != 'success':
            error(result['reason'])
        return
    if baseiso not in k.volumes(iso=True):
        pprint(f"Downloading {liveiso}")
        k.add_image(liveiso, pool)
    poolpath = k.get_pool_path(pool)
    if installer and (k.conn == 'fake' or k.host in ['localhost', '127.0.0.1']):
        if not correct_sha(f"{poolpath}/{baseiso}", get_installer_iso_sha()):
            error(f"Corrupted iso {poolpath}/{baseiso}")
            sys.exit(1)
    pprint(f"Creating iso {name}")
    isocmd = create_embed_ignition_cmd(name, poolpath, baseiso, extra_args=extra_args)
    os.environ["PATH"] += f":{os.getcwd()}"
    if k.conn == 'fake':
        os.system(isocmd)
    elif k.host in ['localhost', '127.0.0.1']:
        if which('podman') is None:
            error("podman is required in order to embed iso ignition")
            sys.exit(1)
        copy2('iso.ign', poolpath)
        os.system(isocmd)
    elif k.protocol == 'ssh':
        warning("podman is required in the remote hypervisor in order to embed iso ignition")
        createbindircmd = f'ssh {k.identitycommand} -p {k.port} {k.user}@{k.host} "mkdir bin >/dev/null 2>&1"'
        os.system(createbindircmd)
        scpbincmd = f'scp {k.identitycommand} -qP {k.port} coreos-installer {k.user}@{k.host}:bin'
        os.system(scpbincmd)
        scpcmd = f'scp {k.identitycommand} -qP {k.port} iso.ign {k.user}@{k.host}:{poolpath}'
        os.system(scpcmd)
        isocmd = f'ssh {k.identitycommand} -p {k.port} {k.user}@{k.host} "PATH=/root/bin {isocmd}"'
        os.system(isocmd)


def olm_app(package):
    os.environ["PATH"] += f":{os.getcwd()}"
    own = True
    name, source, defaultchannel, csv, description, installmodes, crds = None, None, None, None, None, None, []
    target_namespace = None
    channels = []
    manifestscmd = f"oc get packagemanifest -n openshift-marketplace {package} -o yaml 2>/dev/null"
    data = yaml.safe_load(os.popen(manifestscmd).read())
    if data is not None:
        name = data['metadata']['name']
        target_namespace = name.split('-operator')[0]
        status = data['status']
        source = status['catalogSource']
        defaultchannel = status['defaultChannel']
        for channel in status['channels']:
            channels.append(channel['name'])
            if channel['name'] == defaultchannel:
                csv = channel['currentCSV']
                description = channel['currentCSVDesc']['description']
                installmodes = channel['currentCSVDesc']['installModes']
                for mode in installmodes:
                    if mode['type'] == 'OwnNamespace' and not mode['supported']:
                        target_namespace = 'openshift-operators'
                        own = False
                        break
                csvdesc = channel['currentCSVDesc']
                csvdescannotations = csvdesc['annotations']
                if own and 'operatorframework.io/suggested-namespace' in csvdescannotations:
                    target_namespace = csvdescannotations['operatorframework.io/suggested-namespace']
                if 'customresourcedefinitions' in csvdesc and 'owned' in csvdesc['customresourcedefinitions']:
                    for crd in csvdesc['customresourcedefinitions']['owned']:
                        crds.append(crd['name'])
    return name, source, defaultchannel, csv, description, target_namespace, channels, crds


def need_fake():
    kclidir = os.path.expanduser("~/.kcli")
    groups = [getgrgid(g).gr_name for g in os.getgroups()]
    if not glob(f"{kclidir}/config.y*ml") and\
       ((groups == ['root'] and not os.path.exists("/var/run/libvirt/libvirt-sock")) or 'libvirt' not in groups):
        if os.path.exists('/i_am_a_container') and os.environ.get('KUBERNETES_SERVICE_HOST') is not None:
            return False
        else:
            return True
    else:
        return False


def info_network(k, name):
    networks = k.list_networks()
    if name in networks:
        networkinfo = networks[name]
    else:
        error(f"Network {name} not found")
        return {}
    return networkinfo


def get_ssh_pub_key():
    for _dir in ['.kcli', '.ssh']:
        for path in SSH_PUB_LOCATIONS:
            pubpath = os.path.expanduser(f"~/{_dir}/{path}")
            privpath = pubpath.replace('.pub', '')
            if os.path.exists(pubpath):
                if not os.path.exists(privpath):
                    warning(f"private key associated to {pubpath} not found, you might have trouble accessing the vm")
                return pubpath


def container_mode():
    return os.path.exists("/i_am_a_container") and os.path.exists('/workdir')


def netmask_to_prefix(netmask):
    return sum(bin(int(x)).count('1') for x in netmask.split('.'))


def valid_ip(ip):
    try:
        ip_address(ip)
        return True
    except:
        return False


def get_git_version():
    git_version, git_date = 'N/A', 'N/A'
    versiondir = os.path.dirname(version.__file__)
    git_file = f'{versiondir}/git'
    if os.path.exists(git_file) and os.stat(git_file).st_size > 0:
        data = open(git_file).read().rstrip().split(' ')
        if len(data) == 2:
            git_version, git_date = data
    return git_version, git_date


def compare_git_versions(commit1, commit2):
    date1, date2 = None, None
    mycwd = os.getcwd()
    with TemporaryDirectory() as tmpdir:
        cmd = f"git clone -q https://github.com/karmab/kcli {tmpdir}"
        call(cmd, shell=True)
        os.chdir(tmpdir)
        timestamp1 = os.popen(f"git show -s --format=%ct {commit1}").read().strip()
        date1 = datetime.fromtimestamp(int(timestamp1))
        timestamp2 = os.popen(f"git show -s --format=%ct {commit2}").read().strip()
        date2 = datetime.fromtimestamp(int(timestamp2))
        os.chdir(mycwd)
    return True if date1 < date2 else False


def correct_sha(_file, sha):
    sha256_hash = sha256()
    with open(_file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    downloaded_sha = sha256_hash.hexdigest()
    return downloaded_sha == sha


def get_rhcos_url_from_file(filename, _type='kvm'):
    openshift_version = filename.split('.')[0].replace('rhcos-4', 'rhcos-4.')
    minor_version = f"{filename.split('-')[1]}-{filename.split('-')[2]}"
    arch = filename.split('.')[3]
    url = "https://releases-art-rhcos.svc.ci.openshift.org/art/storage/releases/"
    url += f"{openshift_version}/{minor_version}/{arch}/{filename}.gz"
    return url


def info_baremetal_hosts(baremetal_hosts, overrides={}, debug=False, full=False):
    failures = []
    for host in baremetal_hosts:
        bmc_url = host.get('url') or host.get('bmc_url')
        bmc_user = host.get('user') or host.get('bmc_user') or overrides.get('bmc_user')
        bmc_password = host.get('password') or host.get('bmc_password') or overrides.get('bmc_password')
        if bmc_url is not None:
            red = Redfish(bmc_url, bmc_user, bmc_password, debug=debug)
            node_name = host['name'] if 'name' in host else f"with url {bmc_url}"
            pprint(f"Reporting info on Host {node_name}")
            try:
                info = red.info()
            except Exception as e:
                msg = f'Hit {e} when getting info on host {node_name}'
                error(msg)
                failures.append(msg)
            if full:
                pretty_print(info)
            else:
                keys = ['UUID', 'SERIAL', 'BOOT', 'HostName', 'IndicatorLED', 'Manufacturer', 'Model', 'MemorySummary',
                        'PowerState', 'PartNumber', 'SKU', 'SystemType']
                data = {key: info[key] for key in keys if key in info}
                pretty_print(data)
    if failures:
        return {'result': 'failure', 'reason': '\n'.join(failures)}
    return {'result': 'success'}


def reset_baremetal_hosts(baremetal_hosts, overrides={}, debug=False):
    failures = []
    for host in baremetal_hosts:
        bmc_url = host.get('url') or host.get('bmc_url')
        bmc_user = host.get('user') or host.get('bmc_user') or overrides.get('bmc_user')
        bmc_password = host.get('password') or host.get('bmc_password') or overrides.get('bmc_password')
        if bmc_url is not None:
            red = Redfish(bmc_url, bmc_user, bmc_password, debug=debug)
            node_name = host['name'] if 'name' in host else f"with url {bmc_url}"
            pprint(f"Resetting Host {node_name}")
            try:
                red.reset()
            except Exception as e:
                msg = f'Hit {e} when resetting host {node_name}'
                error(msg)
                failures.append(msg)
    if failures:
        return {'result': 'failure', 'reason': '\n'.join(failures)}
    return {'result': 'success'}


def start_baremetal_hosts(baremetal_hosts, iso_url, overrides={}, debug=False):
    failures = []
    sno = iso_url is not None and iso_url.endswith('-sno.iso')
    for index, host in enumerate(baremetal_hosts):
        index_iso_url = iso_url
        bmc_url = host.get('url') or host.get('bmc_url')
        if sno and index > 0:
            role = host.get('role') or overrides.get('role') or 'worker'
            index_iso_url = iso_url.replace('-sno.iso', f'-{role}.iso')
        bmc_user = host.get('username') or host.get('user') or host.get('bmc_username') or host.get('bmc_user')\
            or overrides.get('bmc_user') or overrides.get('bmc_username')\
            or overrides.get('user') or overrides.get('username')
        bmc_password = host.get('password') or host.get('bmc_password') or overrides.get('bmc_password')
        bmc_reset = host.get('reset') or host.get('bmc_reset') or overrides.get('bmc_reset', False)
        if bmc_url is not None:
            red = Redfish(bmc_url, bmc_user, bmc_password, debug=debug)
            if bmc_reset:
                red.reset()
                sleep(240)
            node_name = host['name'] if 'name' in host else f"with url {bmc_url}"
            if index_iso_url is not None:
                pprint(f"Booting Host {node_name} with {index_iso_url}")
                try:
                    red.set_iso(index_iso_url)
                except Exception as e:
                    msg = f"Hit {e} when plugging iso to host {node_name}"
                    error(msg)
                    return {'result': 'failure', 'reason': msg}
            else:
                pprint(f"Booting Host {node_name}")
                try:
                    red.start()
                except Exception as e:
                    msg = f"Hit {e} when starting host {node_name}"
                    error(msg)
                    failures.append(msg)
        else:
            warning(f"Skipping entry {index} because either bmc_url, bmc_user or bmc_password is not set")
    if failures:
        return {'result': 'failure', 'reason': '\n'.join(failures)}
    return {'result': 'success'}


def stop_baremetal_hosts(baremetal_hosts, overrides={}, debug=False):
    failures = []
    for host in baremetal_hosts:
        bmc_url = host.get('url') or host.get('bmc_url')
        bmc_user = host.get('user') or host.get('bmc_user') or overrides.get('bmc_user')
        bmc_password = host.get('password') or host.get('bmc_password') or overrides.get('bmc_password')
        if bmc_url is not None:
            red = Redfish(bmc_url, bmc_user, bmc_password, debug=debug)
            node_name = host['name'] if 'name' in host else f"with url {bmc_url}"
            pprint(f"Stopping Host {node_name}")
            try:
                red.stop()
            except Exception as e:
                msg = f'Hit {e} when stopping host {node_name}'
                error(msg)
                failures.append(msg)
    if failures:
        return {'result': 'failure', 'reason': '\n'.join(failures)}
    return {'result': 'success'}


def update_baremetal_hosts(baremetal_hosts, overrides={}, debug=False):
    failures = []
    for index, host in enumerate(baremetal_hosts):
        bmc_url = host.get('url') or host.get('bmc_url')
        bmc_user = host.get('username') or host.get('user') or host.get('bmc_username') or host.get('bmc_user')\
            or overrides.get('bmc_user') or overrides.get('bmc_username')\
            or overrides.get('user') or overrides.get('username')
        bmc_password = host.get('password') or host.get('bmc_password') or overrides.get('bmc_password')
        secureboot = host.get('secureboot') or host.get('bmc_secureboot') or overrides.get('secureboot')
        if bmc_url is not None and secureboot is not None:
            red = Redfish(bmc_url, bmc_user, bmc_password, debug=debug)
            node_name = host['name'] if 'name' in host else f"with url {bmc_url}"
            pprint(f"Updating secureboot in Host {node_name}")
            try:
                if secureboot:
                    red.enable_secureboot()
                else:
                    red.disable_secureboot()
            except Exception as e:
                msg = f"Hit {e} when updating secureboot in host {node_name}"
                error(msg)
                failures.append(msg)
        else:
            warning(f"Skipping entry {index} because either bmc_url, bmc_user or bmc_password is not set")
    if failures:
        return {'result': 'failure', 'reason': '\n'.join(failures)}
    return {'result': 'success'}


def get_changelog(diff, data=False):
    if which('git') is None:
        error("git needed for this functionality")
        sys.exit(1)
    if not diff:
        diff = ['main']
    if len(diff) > 1:
        ori, dest = diff[:2]
    else:
        git_version = get_git_version()[0]
        if git_version != 'N/A':
            ori, dest = git_version, diff[0]
        else:
            error("No source commit available. Use kcli changelog diff1 diff2")
            sys.exit(1)
    with TemporaryDirectory() as tmpdir:
        cmd = f"git clone -q https://github.com/karmab/kcli {tmpdir}"
        call(cmd, shell=True)
        os.chdir(tmpdir)
        cmd = f"git --no-pager log --decorate=no --oneline {ori}..{dest}"
        if data:
            cmd += f"> {tmpdir}/results.txt"
            call(cmd, shell=True)
            return open(f"{tmpdir}/results.txt").read()
        else:
            call(cmd, shell=True)


def wait_cloud_dns(cluster, domain):
    timeout = 0
    while True:
        pprint(f"Waiting for api.{cluster}.{domain} to resolve")
        try:
            socket.gethostbyname(f"api.{cluster}.{domain}")
            return
        except:
            sleep(10)
            timeout += 10
        if timeout > 120:
            warning(f"Timeout waiting for api.{cluster}.{domain} to resolve")
            return


def deploy_cloud_storage(config, cluster, apply=True):
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    commondir = os.path.dirname(pprint.__code__.co_filename)
    storage_data = config.process_inputfile('xxx', f"{commondir}/storage.sh.{config.type}")
    with open(f"{clusterdir}/storage.sh", 'w') as f:
        f.write(storage_data)
    if apply:
        storagecmd = f"bash {clusterdir}/storage.sh"
        call(storagecmd, shell=True)


def update_etc_hosts(cluster, domain, api_ip):
    if not os.path.exists("/i_am_a_container"):
        hosts = open("/etc/hosts").readlines()
        wronglines = [e for e in hosts if not e.startswith('#') and f"api.{cluster}.{domain}" in e and api_ip not in e]
        for wrong in wronglines:
            warning(f"Cleaning wrong entry {wrong} in /etc/hosts")
            call(f"sudo sed -i '/{wrong.strip()}/d' /etc/hosts", shell=True)
        hosts = open("/etc/hosts").readlines()
        correct = [e for e in hosts if not e.startswith('#') and f"api.{cluster}.{domain}" in e and api_ip in e]
        if not correct:
            call(f"sudo sh -c 'echo {api_ip} api.{cluster}.{domain} >> /etc/hosts'", shell=True)
    else:
        call(f"sh -c 'echo {api_ip} api.{cluster}.{domain} >> /etc/hosts'", shell=True)
        if os.path.exists('/etcdir/hosts'):
            call(f"sh -c 'echo {api_ip} api.{cluster}.{domain} >> /etcdir/hosts'", shell=True)
        else:
            warning("Make sure to have the following entry in your /etc/hosts")
            warning(f"{api_ip} api.{cluster}.{domain}")


def separate_yamls(origin):
    basedir = os.path.dirname(origin)
    target = os.path.basename(origin).replace('.yml', '').replace('.yaml', '')
    with open(origin) as o:
        data = yaml.safe_load_all(o)
        for index, entry in enumerate(data):
            with open(f'{basedir}/{target}-{index}.yaml', 'w') as t:
                yaml.safe_dump(entry, t)
    os.remove(origin)


def install_provider(provider, pip=False):
    if provider == 'kvm':
        warning("Nothing needed")
        sys.exit(0)
    if os.path.exists('/Users'):
        warning("Using pip")
        pip = True
    pkgmgr = None
    if which('dnf') is not None:
        pkgmgr = 'dnf'
    elif which('yum') is not None:
        pkgmgr = 'yum'
    elif which('apt-get') is not None:
        pkgmgr = 'apt-get'
    if not pip and pkgmgr is None:
        error("Package based installation requires either dnf or apt-get")
        sys.exit(1)
    if provider == 'aws':
        cmd = 'pip3 install boto3' if pip else f'{pkgmgr} -y install python3-boto3'
    if provider == 'azure':
        if not pip:
            warning("Using pip as this is the only way for this provider")
        cmd = 'pip3 install azure-mgmt-compute azure-mgmt-network azure-mgmt-resource azure-mgmt-core azure-identity'
        cmd += ' azure-mgmt-marketplaceordering azure-storage-blob azure-mgmt-dns azure-mgmt-containerservice'
        cmd += ' azure-mgmt-authorization azure.mgmt.storage azure.mgmt.msi'
    elif provider == 'gcp':
        if not pip:
            warning("Using pip as this is the only way for this provider")
        cmd = 'pip3 install google-api-python-client google-auth-httplib2 google-cloud-dns google-cloud-storage '
        cmd += 'google-cloud-container google-cloud-compute'
    elif provider == 'ibm':
        if not pip:
            warning("Using pip as this is the only way for this provider")
        cmd = 'pip3 install ibm_vpc ibm-cos-sdk ibm-platform-services ibm-cloud-networking-services'
    elif provider == 'kubevirt':
        cmd = 'pip3 install kubernetes' if pip else f'{pkgmgr} -y install python3-kubernetes'
    elif provider == 'openstack':
        if pip:
            cmd = 'pip3 install python-cinderclient python-neutronclient python-glanceclient python-keystoneclient '
            cmd += 'python-novaclient python-swiftclient'
        else:
            cmd = f'{pkgmgr} -y install python3-keystoneclient python3-glanceclient python3-cinderclient '
            cmd += 'python3-neutronclient python3-novaclient python3-swiftclient'
    elif provider == 'ovirt':
        cmd = 'pip3 install ovirt-engine-sdk-python' if pip else f'{pkgmgr} -y install python3-ovirt-engine-sdk4'
    elif provider == 'packet':
        if not pip:
            warning("Using pip as this is the only way for this provider")
        cmd = 'pip3 install packet-python'
    elif provider == 'proxmox':
        if not pip:
            warning("Using pip as this is the only way for this provider")
        cmd = 'pip3 install proxmoxer'
    elif provider == 'vsphere':
        if pip:
            cmd = 'pip3 install pyvmomi cryptography'
        else:
            cmd = f'{pkgmgr} -y install python3-pyvmomi python3-cryptography'
    pprint(f"Running {cmd}")
    call(cmd, shell=True)


def fix_typos(data):
    if 'ctlplane' in data and 'ctlplanes' not in data:
        warning("Assuming you meant ctlplanes")
        data['ctlplanes'] = data['ctlplane']
    if 'worker' in data and 'ctlplanes' not in data:
        warning("Assuming you meant workers")
        data['workers'] = data['worker']


def interactive_vm():
    overrides = {}
    default_parameters = {'name': get_random_name(), 'image': 'centos8stream', 'numcpus': 2, 'memory': 512,
                          'pool': 'default', 'disks': [10], 'nets': ['default']}
    pprint("Override the following items or accept default values:")
    for key in default_parameters:
        default_value = default_parameters[key]
        value = input(f"{key}: ({default_value}) ")
        if value is None or value == '':
            value = default_value
        elif value == 'None':
            value = None
        elif isinstance(default_value, list):
            value = json.loads(value) if '[' in value else [value]
        elif isinstance(default_value, int):
            value = int(value)
        overrides[key] = value
    return overrides


def interactive_kube(_type):
    overrides = {}
    default_parameters = {'cluster': get_random_name(), 'domain': 'karmalabs.corp', 'network': 'default',
                          'version': None, 'ctlplanes': 1, 'workers': 0, 'memory': 6144, 'numcpus': 4, 'disk_size': 30}
    if _type == 'openshift':
        default_parameters.update({'pull_secret': 'openshift_pull.json', 'version': 'stable', 'tag': OPENSHIFT_TAG,
                                   'ctlplanes': 3, 'workers': 0, 'memory': 16384})
    elif _type == 'openshift-sno':
        default_parameters.update({'pull_secret': 'openshift_pull.json', 'version': 'stable', 'tag': OPENSHIFT_TAG,
                                   'memory': 20480, 'sno_disk': None, 'sno_vm': False, 'sno_wait': False,
                                   'sno_cpuset': None})
    pprint("Override the following items or accept default values:")
    for key in default_parameters:
        default_value = default_parameters[key]
        value = input(f"{key}: ({default_value}) ")
        if value is None or value == '':
            value = default_parameters[key]
        elif value == 'None':
            value = None
        elif isinstance(default_value, list):
            value = json.loads(value) if '[' in value else [value]
        elif isinstance(default_value, int):
            value = int(value)
        overrides[key] = value
    return overrides


def plan_constructor(loader, node, deep=False):
    mapping = {}
    types = []
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        value = loader.construct_object(value_node, deep=deep)
        if isinstance(value, dict):
            _type = value.get('type', 'vm')
            if key == 'parameters':
                mapping[key] = value
            elif _type not in types:
                mapping[_type] = [{key: value}]
                types.append(_type)
            elif [entry for entry in mapping[_type] if next(iter(entry)) == key]:
                raise Exception(f"Duplicate key {key} for type {_type}")
            else:
                mapping[_type].append({key: value})
        else:
            mapping[key] = value
    return mapping


class PlanLoader(yaml.SafeLoader):
    pass


PlanLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, plan_constructor)
