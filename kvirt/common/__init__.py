#!/usr/bin/env python
# coding=utf-8

import base64
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError
from distutils.spawn import find_executable
from netaddr import IPAddress
import random
import socket
from urllib.parse import quote
from urllib.request import urlretrieve
import json
import os
import yaml

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip', 'ks']
ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety', 'zesty', 'artful', 'bionic', 'cosmic']


def fetch(url, path):
    if 'raw.githubusercontent.com' not in url:
        url = url.replace('github.com', 'raw.githubusercontent.com').replace('blob/master', 'master')
    shortname = os.path.basename(url)
    if not os.path.exists(path):
        os.mkdir(path)
    urlretrieve(url, "%s/%s" % (path, shortname))


def cloudinit(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[],
              enableroot=True, overrides={}, iso=True, fqdn=False, storemetadata=True):
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
    default_gateway = gateway
    with open('/tmp/meta-data', 'w') as metadatafile:
        if domain is not None:
            localhostname = "%s.%s" % (name, domain)
        else:
            localhostname = name
        metadata = {"instance-id": localhostname, "local-hostname": localhostname}
        netdata = ''
        if nets:
            for index, net in enumerate(nets):
                if isinstance(net, str) or (len(net) == 1 and 'name' in net):
                    if index == 0:
                        continue
                    nicname = "eth%d" % index
                    ip = None
                    netmask = None
                    noconf = None
                    vips = []
                elif isinstance(net, dict):
                    nicname = net.get('nic', "eth%d" % index)
                    ip = net.get('ip')
                    netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
                    noconf = net.get('noconf')
                    vips = net.get('vips')
                netdata += "  auto %s\n" % nicname
                if noconf is not None:
                    netdata += "  iface %s inet manual\n" % nicname
                elif ip is not None and netmask is not None and not reserveip:
                    netdata += "  iface %s inet static\n" % nicname
                    netdata += "  address %s\n" % ip
                    netdata += "  netmask %s\n" % netmask
                    gateway = net.get('gateway')
                    if index == 0 and default_gateway is not None:
                        netdata += "  gateway %s\n" % default_gateway
                    elif gateway is not None:
                        netdata += "  gateway %s\n" % gateway
                    dns = net.get('dns')
                    if dns is not None:
                        netdata += "  dns-nameservers %s\n" % dns
                    domain = net.get('domain')
                    if domain is not None:
                        netdata += "  dns-search %s\n" % domain
                    if isinstance(vips, list) and vips:
                        for index, vip in enumerate(vips):
                            netdata += "  auto %s:%s\n  iface %s:%s inet static\n  address %s\n  netmask %s\n"\
                                % (nicname, index, nicname, index, vip, netmask)
                else:
                    netdata += "  iface %s inet dhcp\n" % nicname
            if netdata:
                metadata["network-interfaces"] = netdata
            metadatafile.write(json.dumps(metadata))
    with open('/tmp/user-data', 'w') as userdata:
        userdata.write('#cloud-config\nhostname: %s\n' % name)
        if fqdn:
            fqdn = "%s.%s" % (name, domain) if domain is not None else name
            userdata.write("fqdn: %s\n" % fqdn)
        if enableroot:
            userdata.write("ssh_pwauth: True\ndisable_root: false\n")
        if domain is not None:
            userdata.write("fqdn: %s.%s\n" % (name, domain))
        if keys or os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub"))\
                or os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub"))\
                or os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub"))\
                or os.path.exists(os.path.expanduser("~/.kcli/id_dsa.pub")):
            userdata.write("ssh_authorized_keys:\n")
        else:
            pprint("neither id_rsa or id_dsa public keys found in your .ssh or .kcli directory, you might have trouble "
                   "accessing the vm", color='red')
        if keys:
            for key in list(set(keys)):
                userdata.write("- %s\n" % key)
        publickeyfile = None
        if os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub")):
            publickeyfile = os.path.expanduser("~/.ssh/id_rsa.pub")
        elif os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub")):
            publickeyfile = os.path.expanduser("~/.ssh/id_dsa.pub")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub")):
            publickeyfile = os.path.expanduser("~/.kcli/id_rsa.pub")
        elif os.path.exists(os.path.expanduser("~/.kcli/id_dsa.pub")):
            publickeyfile = os.path.expanduser("~/.kcli/id_dsa.pub")
        if publickeyfile is not None:
            with open(publickeyfile, 'r') as ssh:
                key = ssh.read().rstrip()
                userdata.write("- %s\n" % key)
        if cmds:
                data = process_cmds(cmds, overrides)
                if data != '':
                    userdata.write("runcmd:\n")
                    userdata.write(data)
        userdata.write('ssh_pwauth: True\n')
        userdata.write('disable_root: false\n')
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
                userdata.write("write_files:\n")
                userdata.write(data)
    if iso:
        isocmd = 'mkisofs'
        if find_executable('genisoimage') is not None:
            isocmd = 'genisoimage'
        os.system("%s --quiet -o /tmp/%s.ISO --volid cidata --joliet --rock /tmp/user-data /tmp/meta-data" % (isocmd,
                                                                                                              name))


def process_files(files=[], overrides={}):
    """

    :param files:
    :param overrides:
    :return:
    """
    data = ''
    for fil in files:
        if not isinstance(fil, dict):
            continue
        origin = fil.get('origin')
        content = fil.get('content')
        path = fil.get('path')
        owner = fil.get('owner', 'root')
        mode = fil.get('mode', '0600')
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
                env = Environment(loader=FileSystemLoader(basedir))
                try:
                    templ = env.get_template(os.path.basename(origin))
                except TemplateSyntaxError as e:
                    pprint("Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message),
                           color='red')
                    os._exit(1)
                fileentries = templ.render(overrides)
                # content = [line.rstrip() for line in fileentries.split('\n') if line.rstrip() != '']
                content = [line.rstrip() for line in fileentries.split('\n')]
                with open("/tmp/%s" % os.path.basename(path), 'w') as f:
                    for line in fileentries.split('\n'):
                        if line.rstrip() == '':
                            f.write("\n")
                        else:
                            f.write("%s\n" % line.rstrip())
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
    data = []
    for fil in files:
        if not isinstance(fil, dict):
            continue
        origin = fil.get('origin')
        content = fil.get('content')
        path = fil.get('path')
        mode = int(fil.get('mode', '644'), 8)
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
                env = Environment(loader=FileSystemLoader(basedir))
                try:
                    templ = env.get_template(os.path.basename(origin))
                except TemplateSyntaxError as e:
                    pprint("Error rendering line %s of file %s. Got: %s" % (e.lineno, e.filename, e.message),
                           color='red')
                    os._exit(1)
                fileentries = templ.render(overrides)
                # content = [line.rstrip() for line in fileentries.split('\n') if line.rstrip() != '']
                content = [line for line in fileentries.split('\n')]
            else:
                content = open(origin, 'r').readlines()
        elif content is None:
            continue
        if not isinstance(content, str):
            content = '\n'.join(content) + '\n'
        content = quote(content)
        data.append({'filesystem': 'root', 'path': path, 'mode': permissions,
                     "contents": {"source": "data:,%s" % content, "verification": {}}})
    return data


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
            newcmd = Environment().from_string(cmd).render(overrides)
            data += "- %s\n" % newcmd
    return data


def process_ignition_cmds(cmds, overrides):
    """

    :param cmds:
    :param overrides:
    :return:
    """
    path = '/root/first.sh'
    permissions = '700'
    content = ''
    for cmd in cmds:
        newcmd = Environment().from_string(cmd).render(overrides)
        content += "%s\n" % newcmd
    if content == '':
        return content
    else:
        if not content.startswith('#!'):
            content = "#!/bin/sh\n%s" % content
        content = quote(content)
        data = {'filesystem': 'root', 'path': path, 'mode': int(permissions, 8),
                "contents": {"source": "data:,%s" % content, "verification": {}}}
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


def pprint(text, color=None):
    """

    :param text:
    :param color:
    """
    colors = {'blue': '34', 'red': '31', 'green': '32', 'yellow': '33', 'pink': '35', 'white': '37'}
    if color is not None and color in colors:
        color = colors[color]
        print('\033[1;%sm%s\033[0;0m' % (color, text))
    else:
        print(text)


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
    if result['result'] == 'success':
        if not quiet:
            response = "%s%s %s" % (element, name, action)
            if client is not None:
                response += " on %s" % client
            pprint(response, color='green')
        return 0
    else:
        if not quiet:
            reason = result['reason']
            pprint("%s%s not %s because %s" % (element, name, action, reason), color='red')
        return 1


def confirm(message):
    """

    :param message:
    :return:
    """
    message = "%s [y/N]: " % message
    _input = input(message)
    if _input.lower() not in ['y', 'yes']:
        pprint("Leaving...", color='red')
        os._exit(1)
    return


def get_lastvm(client):
    """

    :param client:
    :return:
    """
    lastvm = "%s/.kcli/vm" % os.environ.get('HOME')
    if os.path.exists(lastvm) and os.stat(lastvm).st_size > 0:
        for line in open(lastvm).readlines():
            line = line.split(' ')
            if len(line) != 2:
                continue
            cli = line[0].strip()
            vm = line[1].strip()
            if cli == client:
                pprint("Using %s from %s as vm" % (vm, cli), color='green')
                return vm
    pprint("Missing Vm's name", color='red')
    os._exit(1)


def set_lastvm(name, client, delete=False):
    """

    :param name:
    :param client:
    :param delete:
    :return:
    """
    configdir = "%s/.kcli/" % os.environ.get('HOME')
    vmfile = "%s/vm" % configdir
    if not os.path.exists(configdir):
        os.mkdir(configdir)
    if delete:
        if not os.path.exists(vmfile):
            return
        else:
            os.system("sed -i '/%s %s/d' %s/vm" % (client, name, configdir))
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
    if paramfile is not None and os.path.exists(os.path.expanduser(paramfile)):
        with open(os.path.expanduser(paramfile)) as f:
            try:
                overrides = yaml.load(f)
            except:
                pprint("Couldnt parse your parameters file %s. Not using it" % paramfile, color='blue')
                overrides = {}
    if param is not None:
        overrides = {}
        for x in param:
            if len(x.split('=')) != 2:
                continue
            else:
                key, value = x.split('=')
                if value.isdigit():
                    value = int(value)
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.startswith('[') and value.endswith(']'):
                    value = value[1:-1].split(',')
                overrides[key] = value
    else:
        overrides = {}
    return overrides


def get_parameters(inputfile):
    """

    :param inputfile:
    :return:
    """
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
            if not fields:
                fields = ['name', 'instanceid', 'creationdate', 'host', 'status', 'description', 'autostart',
                          'template', 'plan', 'profile', 'flavor', 'cpus', 'memory', 'nets', 'ip', 'disks', 'snapshots',
                          'tags', 'nodeport']
            for key in fields:
                if key not in yamlinfo:
                    continue
                else:
                    value = yamlinfo[key]
                    if key == 'nets':
                        for net in value:
                            device = net['device']
                            mac = net['mac']
                            network = net['net']
                            network_type = net['type']
                            result += "net interface: %s mac: %s net: %s type: %s\n" % (device, mac, network,
                                                                                        network_type)
                    elif key == 'disks':
                        for disk in value:
                            device = disk['device']
                            disksize = disk['size']
                            diskformat = disk['format']
                            drivertype = disk['type']
                            path = disk['path']
                            result += "diskname: %s disksize: %sGB diskformat: %s type: %s path: %s\n" % (device,
                                                                                                          disksize,
                                                                                                          diskformat,
                                                                                                          drivertype,
                                                                                                          path)
                    elif key == 'snapshots':
                        for snap in value:
                            snapshot = snap['snapshot']
                            current = snap['current']
                            result += "snapshot: %s current: %s\n" % (snapshot, current)
                    else:
                        if values:
                            result += "%s\n" % value
                        else:
                            result += "%s: %s\n" % (key, value)
            return result.rstrip()


def ssh(name, ip='', host=None, port=22, hostuser=None, user=None, local=None, remote=None, tunnel=False,
        insecure=False, cmd=None, X=False, Y=False, debug=False, D=None):
        """

        :param name:
        :param ip:
        :param host:
        :param port:
        :param hostuser:
        :param user:
        :param local:
        :param remote:
        :param tunnel:
        :param insecure:
        :param cmd:
        :param X:
        :param Y:
        :param debug:
        :param D:
        :return:
        """
        if ip == '':
            return None
        else:
            sshcommand = "%s@%s" % (user, ip)
            identityfile = None
            if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                identityfile = os.path.expanduser("~/.kcli/id_rsa")
            elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                identityfile = os.path.expanduser("~/.kcli/id_rsa")
            if identityfile is not None:
                sshcommand = "-i %s %s" % (identityfile, sshcommand)
            if D:
                sshcommand = "-D %s %s" % (D, sshcommand)
            if X:
                sshcommand = "-X %s" % sshcommand
            if Y:
                sshcommand = "-Y %s" % sshcommand
            if cmd:
                sshcommand = "%s %s" % (sshcommand, cmd)
            if host is not None and host not in ['localhost', '127.0.0.1'] and tunnel and hostuser is not None:
                tunnelcommand = "-qp %s -W %%h:%%p %s@%s" % (port, hostuser, host)
                if identityfile is not None:
                    tunnelcommand = "-i %s %s" % (identityfile, tunnelcommand)
                if insecure:
                    tunnelcommand = "-o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no %s"\
                        % tunnelcommand
                sshcommand = "-o ProxyCommand='ssh %s' %s" % (tunnelcommand, sshcommand)
            if local is not None:
                sshcommand = "-L %s %s" % (local, sshcommand)
            if remote is not None:
                sshcommand = "-R %s %s" % (remote, sshcommand)
            if insecure:
                sshcommand = "ssh -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no %s"\
                    % sshcommand
            else:
                sshcommand = "ssh %s" % sshcommand
            if debug:
                print(sshcommand)
            return sshcommand


def scp(name, ip='', host=None, port=22, hostuser=None, user=None, source=None, destination=None, recursive=None,
        tunnel=False, debug=False, download=False):
        """

        :param name:
        :param ip:
        :param host:
        :param port:
        :param hostuser:
        :param user:
        :param source:
        :param destination:
        :param recursive:
        :param tunnel:
        :param debug:
        :param download:
        :return:
        """
        if ip == '':
            print("No ip found. Cannot scp...")
        else:
            if host is not None and host not in ['localhost', '127.0.0.1'] and tunnel and hostuser is not None:
                arguments = "-o ProxyCommand='ssh -qp %s -W %%h:%%p %s@%s'" % (port, hostuser, host)
            else:
                arguments = ''
            scpcommand = 'scp'
            identityfile = None
            if os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                identityfile = os.path.expanduser("~/.kcli/id_rsa")
            elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa")):
                identityfile = os.path.expanduser("~/.kcli/id_rsa")
            if identityfile is not None:
                scpcommand = "%s -i %s" % (scpcommand, identityfile)
            if recursive:
                scpcommand = "%s -r" % scpcommand
            if download:
                scpcommand = "%s %s %s@%s:%s %s" % (scpcommand, arguments, user, ip, source, destination)
            else:
                scpcommand = "%s %s %s %s@%s:%s" % (scpcommand, arguments, source, user, ip, destination)
            if debug:
                print(scpcommand)
            return scpcommand


def get_user(template):
    """

    :param template:
    :return:
    """
    if 'centos' in template.lower():
        user = 'centos'
    elif 'coreos' in template.lower() or 'rhcos' in template.lower():
        user = 'core'
    elif 'cirros' in template.lower():
        user = 'cirros'
    elif [x for x in ubuntus if x in template.lower()]:
        user = 'ubuntu'
    elif 'fedora' in template.lower():
        user = 'fedora'
    elif 'rhel' in template.lower():
        user = 'cloud-user'
    elif 'debian' in template.lower():
        user = 'debian'
    elif 'arch' in template.lower():
        user = 'arch'
    else:
        user = 'root'
    return user


def ignition(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[],
             enableroot=True, overrides={}, iso=True, fqdn=False, etcd=None):
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
    :param etcd:
    :return:
    """
    if os.path.exists("%s.ign" % name):
        pprint("Using existing %s.ign for %s" % (name, name), color="blue")
        return open("%s.ign" % name).read()
    default_gateway = gateway
    publickeys = []
    if domain is not None:
        localhostname = "%s.%s" % (name, domain)
    else:
        localhostname = name
    if os.path.exists(os.path.expanduser("~/.ssh/id_rsa.pub")):
        publickeyfile = os.path.expanduser("~/.ssh/id_rsa.pub")
    elif os.path.exists(os.path.expanduser("~/.ssh/id_dsa.pub")):
        publickeyfile = os.path.expanduser("~/.ssh/id_dsa.pub")
    elif os.path.exists(os.path.expanduser("~/.kcli/id_rsa.pub")):
        publickeyfile = os.path.expanduser("~/.kcli/id_rsa.pub")
    elif os.path.exists(os.path.expanduser("~/.kcli/id_dsa.pub")):
        publickeyfile = os.path.expanduser("~/.kcli/id_dsa.pub")
    if publickeyfile is not None:
        with open(publickeyfile, 'r') as ssh:
            publickeys.append(ssh.read().rstrip())
    if keys:
        for key in list(set(keys)):
            publickeys.append(key)
    if not publickeys:
        pprint("neither id_rsa or id_dsa public keys found in your .ssh or .kcli directory, you might have trouble "
               "accessing the vm", color='red')
    storage = {"files": []}
    storage["files"].append({"filesystem": "root", "path": "/etc/hostname",
                             "contents": {"source": "data:,%s" % localhostname, "verification": {}}, "mode": 420})
    if files:
        filesdata = process_ignition_files(files=files, overrides=overrides)
        if filesdata:
            storage["files"].extend(filesdata)
    cmdunit = None
    if cmds:
        cmdsdata = process_ignition_cmds(cmds, overrides)
        storage["files"].append(cmdsdata)
        content = "[Service]\nType=oneshot\nExecStart=/root/first.sh\n[Install]\nWantedBy=multi-user.target\n"
        cmdunit = {"contents": content, "name": "first-boot.service", "enabled": True}
    if cmdunit is not None:
        systemd = {"units": [cmdunit]}
    else:
        systemd = {}
    networkunits = []
    if nets:
        for index, net in enumerate(nets):
            netdata = ''
            if isinstance(net, str):
                if index == 0:
                    continue
                nicname = "eth%d" % index
                ip = None
                netmask = None
                cidr = None
                noconf = None
                vips = []
            elif isinstance(net, dict):
                nicname = net.get('nic', "eth%d" % index)
                ip = net.get('ip')
                gateway = net.get('gateway')
                netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
                noconf = net.get('noconf')
                vips = net.get('vips')
            if noconf is not None:
                netdata += "[Match]\nName=%s\n\n[Network]\nDHCP=no\n" % nicname
            elif ip is not None and netmask is not None and not reserveip and gateway is not None:
                cidr = IPAddress(netmask).netmask_bits()
                netdata += "[Match]\nName=%s\n\n" % nicname
                if index == 0 and default_gateway is not None:
                    gateway = default_gateway
                netdata += "[Network]\nAddress=%s/%s\nGateway=%s\n" % (ip, cidr, gateway)
                dns = net.get('dns')
                if dns is not None:
                    netdata += "DNS=%s\n" % dns
                # domain = net.get('domain')
                # if domain is not None:
                #    netdata += "  dns-search %s\n" % domain
                if isinstance(vips, list) and vips:
                    for vip in vips:
                        netdata += "[Network]\nAddress=%s/%s\nGateway=%s\n" % (vip, netmask, gateway)
            if netdata != '':
                # networkunits.append({"contents": netdata, "name": "static.network"})
                networkunits.append({"contents": netdata, "name": "%s.network" % nicname})
    if networkunits:
        networkd = {"units": networkunits}
    else:
        networkd = {}
    data = {'ignition': {'version': '2.2.0', 'config': {}}, 'storage': storage, 'systemd': systemd,
            'networkd': networkd, 'passwd': {'users': [{'name': 'core', 'sshAuthorizedKeys': publickeys}]}}
    if enableroot:
        rootdata = {'name': 'root', 'sshAuthorizedKeys': publickeys}
        data['passwd']['users'].append(rootdata)
    if etcd is not None:
        ipcommand = "ifconfig %s | grep \"inet \" | awk '{print $2}'" % etcd
        metadataget = '#!/bin/sh\necho COREOS_CUSTOM_HOSTNAME=`hostname` > /run/metadata/coreos\n'
        metadataget += 'echo COREOS_CUSTOM_PRIVATE_IPV4=`%s` >> /run/metadata/coreos\n' % ipcommand
        storage["files"].append({"filesystem": "root", "path": "/opt/get-metadata.sh",
                                 "contents": {"source": "data:,%s" % quote(metadataget), "verification": {}},
                                 "mode": int('700', 8)})
        metacontent = "[Service]\nExecStart=\nExecStart=/opt/get-metadata.sh\n"
        metadrop = {"dropins": [{"contents": metacontent, "name": "use-script.conf"}],
                    "name": "coreos-metadata.service"}
        etcdcontent = "[Unit]\nRequires=coreos-metadata.service\nAfter=coreos-metadata.service\n\n"
        etcdcontent += "[Service]\nEnvironmentFile=/run/metadata/coreos\nEnvironment=\"ETCD_IMAGE_TAG=v3.0.15\"\n"
        etcdcontent += "ExecStart=\nExecStart=/usr/lib/coreos/etcd-wrapper $ETCD_OPTS \\\n"
        etcdcontent += "--name=\"${COREOS_CUSTOM_HOSTNAME}\" \\\n  "
        etcdcontent += "--listen-peer-urls=\"http://${COREOS_CUSTOM_PRIVATE_IPV4}:2380\" \\\n  "
        etcdcontent += "--listen-client-urls=\"http://0.0.0.0:2379\" \\\n  "
        etcdcontent += "--initial-advertise-peer-urls=\"http://${COREOS_CUSTOM_PRIVATE_IPV4}:2380\" \\\n  "
        etcdcontent += "--initial-cluster=\"${COREOS_CUSTOM_HOSTNAME}=http://${COREOS_CUSTOM_PRIVATE_IPV4}:2380\" \\\n"
        etcdcontent += "--advertise-client-urls=\"http://${COREOS_CUSTOM_PRIVATE_IPV4}:2379\""
        etcddrop = {"dropins": [{"contents": etcdcontent, "name": "20-clct-etcd-member.conf"}],
                    "name": "etcd-member.service", "enabled": True}
        if 'units' in data['systemd']:
            data['systemd']['units'].append(metadrop)
            data['systemd']['units'].append(etcddrop)
        else:
            data['systemd']['units'] = [metadrop, etcddrop]
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
