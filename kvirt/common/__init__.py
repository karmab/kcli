#!/usr/bin/env python''

from jinja2 import Environment, FileSystemLoader
from distutils.spawn import find_executable
import errno
from netaddr import IPAddress
import socket
from urllib.parse import quote
from urllib.request import urlopen
import urllib.error
import json
import os
import yaml

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip']
ubuntus = ['utopic', 'vivid', 'wily', 'xenial', 'yakkety', 'zesty', 'artful', 'bionic', 'cosmic']


def symlinks(user, repo):
    mappings = []
    url1 = 'https://api.github.com/repos/%s/%s/git/refs/heads/master' % (user, repo)
    try:
        r = urlopen(url1)
    except urllib.error.HTTPError as e:
        print(("Couldn't access url %s, got %s.Leaving..." % (url1, e)))
        os._exit(1)
    base = json.load(r)
    sha = base['object']['sha']
    url2 = 'https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1' % (user, repo, sha)
    r = urlopen(url2)
    try:
        base = json.load(r)
    except:
        return []
    for e in base['tree']:
        if e['mode'] == '120000':
            mappings.append(e['path'])
    return mappings


def download(url, path, debug=False):
    filename = os.path.basename(url)
    if debug:
        print(("Fetching %s" % filename))
    url = urlopen(url)
    with open("%s/%s" % (path, filename), 'wb') as output:
        output.write(url.read())


def makelink(url, path, debug=False):
    filename = os.path.basename(url)
    url = urlopen(url)
    target = url.read()
    if debug:
        print(("Creating symlink for %s pointing to %s" % (filename, target)))
    os.symlink(target, "%s/%s" % (path, filename))


def fetch(url, path, syms=None):
    if not url.startswith('http'):
        url = "https://%s" % url
    if 'github.com' not in url or 'raw.githubusercontent.com' in url:
        download(url, path)
        return
    elif 'api.github.com' not in url:
        url = url.replace('github.com/', 'api.github.com/repos/').replace('tree/master', '')
        url = url.replace('blob/master', '')
    if 'contents' not in url:
        tempurl = url.replace('https://api.github.com/repos/', '')
        user = tempurl.split('/')[0]
        repo = tempurl.split('/')[1]
        syms = symlinks(user, repo)
        url = url.replace("%s/%s" % (user, repo), "%s/%s/contents" % (user, repo))
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise
    try:
        r = urlopen(url)
    except urllib.error.HTTPError:
        print(("Invalid url %s.Leaving..." % url))
        os._exit(1)
    try:
        base = json.load(r)
    except:
        print(("Couldnt load json data from url %s.Leaving..." % url))
        os._exit(1)
    if not isinstance(base, list):
        base = [base]
    for b in base:
        if 'name' not in b or 'type' not in b or 'download_url' not in b:
            print(("Missing data in url %s.Leaving..." % url))
            os._exit(1)
        filename = b['name']
        filetype = b['type']
        filepath = b['path']
        download_url = b['download_url']
        if filepath in syms:
            makelink(download_url, path)
        elif filetype == 'file':
            download(download_url, path)
        elif filetype == 'dir':
            fetch("%s/%s" % (url, filename), "%s/%s" % (path, filename), syms=syms)


def cloudinit(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[],
              enableroot=True, overrides={}, iso=True, fqdn=False):
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
                if isinstance(net, str):
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
        if keys or os.path.exists("%s/.ssh/id_rsa.pub"
                                  % os.environ['HOME']) or os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
            userdata.write("ssh_authorized_keys:\n")
        else:
            pprint("neither id_rsa or id_dsa public keys found in your .ssh directory, you might have trouble "
                   "accessing the vm", color='red')
        if keys:
            for key in list(set(keys)):
                userdata.write("- %s\n" % key)
        if os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
            publickeyfile = "%s/.ssh/id_rsa.pub" % os.environ['HOME']
            with open(publickeyfile, 'r') as ssh:
                key = ssh.read().rstrip()
                userdata.write("- %s\n" % key)
        if os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
            publickeyfile = "%s/.ssh/id_dsa.pub" % os.environ['HOME']
            with open(publickeyfile, 'r') as ssh:
                key = ssh.read().rstrip()
                userdata.write("- %s\n" % key)
        if cmds:
                data = process_cmds(cmds, overrides)
                if data != '':
                    userdata.write("runcmd:\n")
                    userdata.write(data)
                # for cmd in cmds:
                #     if cmd.startswith('#'):
                #         continue
                #     else:
                #         newcmd = Environment(block_start_string='[%', block_end_string='%]',
                #                              variable_start_string='[[',
                #                              variable_end_string=']]').from_string(cmd).render(overrides)
                #         userdata.write("- %s\n" % newcmd)
        userdata.write('ssh_pwauth: True\n')
        userdata.write('disable_root: false\n')
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
        if origin is not None:
            origin = os.path.expanduser(origin)
            if not os.path.exists(origin):
                print(("Skipping file %s as not found" % origin))
                continue
            binary = True if '.' in origin and origin.split('.')[-1].lower() in binary_types else False
            if binary:
                with open(origin, "rb") as f:
                    content = f.read().encode("base64")
            elif overrides:
                basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                env = Environment(block_start_string='[%', block_end_string='%]',
                                  variable_start_string='[[', variable_end_string=']]',
                                  loader=FileSystemLoader(basedir))
                templ = env.get_template(os.path.basename(origin))
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
                content = open(origin, 'r').readlines()
        elif content is None:
            continue
        data += "- owner: %s:%s\n" % (owner, owner)
        data += "  path: %s\n" % path
        data += "  permissions: '%s'\n" % (permissions)
        if binary:
            data += "  content: !!binary | \n"
        else:
            data += "  content: | \n"
        if isinstance(content, str):
            content = content.split('\n')
        for line in content:
            data += "     %s\n" % line.rstrip()
    return data


def process_ignition_files(files=[], overrides={}):
    data = []
    for fil in files:
        if not isinstance(fil, dict):
            continue
        origin = fil.get('origin')
        content = fil.get('content')
        path = fil.get('path')
        # owner = fil.get('owner', 'root')
        mode = int(fil.get('mode', '420'))
        permissions = fil.get('permissions', mode)
        if origin is not None:
            origin = os.path.expanduser(origin)
            if not os.path.exists(origin):
                print(("Skipping file %s as not found" % origin))
                continue
            binary = True if '.' in origin and origin.split('.')[-1].lower() in binary_types else False
            if binary:
                with open(origin, "rb") as f:
                    content = f.read().encode("base64")
            elif overrides:
                basedir = os.path.dirname(origin) if os.path.dirname(origin) != '' else '.'
                env = Environment(block_start_string='[%', block_end_string='%]',
                                  variable_start_string='[[', variable_end_string=']]',
                                  loader=FileSystemLoader(basedir))
                templ = env.get_template(os.path.basename(origin))
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
    data = ''
    for cmd in cmds:
        if cmd.startswith('#'):
            continue
        else:
            newcmd = Environment(block_start_string='[%', block_end_string='%]', variable_start_string='[[',
                                 variable_end_string=']]').from_string(cmd).render(overrides)
            data += "- %s\n" % newcmd
    return data


def process_ignition_cmds(cmds, overrides):
    path = '/root/first.sh'
    permissions = 448
    content = ''
    for cmd in cmds:
        newcmd = Environment(block_start_string='[%', block_end_string='%]', variable_start_string='[[',
                             variable_end_string=']]').from_string(cmd).render(overrides)
        content += "%s\n" % newcmd
    if content == '':
        return content
    else:
        # content = "#!/bin/bash\n%s" % content
        content = quote(content)
        data = {'filesystem': 'root', 'path': path, 'mode': permissions,
                "contents": {"source": "data:,%s" % content, "verification": {}}}
        return data


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def pprint(text, color=None):
    colors = {'blue': '34', 'red': '31', 'green': '32', 'yellow': '33', 'pink': '35', 'white': '37'}
    if color is not None and color in colors:
        color = colors[color]
        print(('\033[1;%sm%s\033[0;0m' % (color, text)))
    else:
        print(text)


def handle_response(result, name, quiet=False, element='', action='deployed', client=None):
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
    message = "%s [y/N]: " % message
    _input = input(message)
    if _input.lower() not in ['y', 'yes']:
        pprint("Leaving...", color='red')
        os._exit(1)
    return


def get_lastvm(client):
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
    newlist = []
    for item in oldlist:
        if item not in newlist:
            newlist.append(item)
    return newlist


def get_overrides(paramfile=None, param=[]):
    if paramfile is not None and os.path.exists(os.path.expanduser(paramfile)):
        with open(os.path.expanduser(paramfile)) as f:
            try:
                overrides = yaml.load(f)
            except:
                pprint("Couldnt parse your parameters file %s. Not using it" % paramfile, color='blue')
                overrides = {}
    elif param is not None:
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
                overrides[key] = value
    else:
        overrides = {}
    return overrides


def get_parameters(inputfile):
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


def print_info(yamlinfo, output='plain', fields=None, values=False):
        if fields is not None:
            for key in list(yamlinfo):
                if key not in fields:
                    del yamlinfo[key]
        if output == 'yaml':
            print((yaml.dump(yamlinfo, default_flow_style=False, indent=2, allow_unicode=True,
                             encoding=None).replace("'", '')[:-1]))
        else:
            if fields is None:
                fields = ['name', 'creationdate', 'host', 'status', 'description', 'autostart', 'template', 'plan',
                          'profile', 'cpus', 'memory', 'nets', 'ip', 'disks', 'snapshots', 'tags', 'hostname']
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
                            print(("net interface: %s mac: %s net: %s type: %s" % (device, mac, network,
                                                                                   network_type)))
                    elif key == 'disks':
                        for disk in value:
                            device = disk['device']
                            disksize = disk['size']
                            diskformat = disk['format']
                            drivertype = disk['type']
                            path = disk['path']
                            print(("diskname: %s disksize: %sGB diskformat: %s type: %s path: %s" % (device, disksize,
                                                                                                     diskformat,
                                                                                                     drivertype, path)))
                    elif key == 'snapshots':
                        for snap in value:
                            snapshot = snap['snapshot']
                            current = snap['current']
                            print(("snapshot: %s current: %s" % (snapshot, current)))
                    else:
                        if values:
                            print(value)
                        else:
                            print(("%s: %s" % (key, value)))


def ssh(name, ip='', host=None, port=22, hostuser=None, user=None, local=None, remote=None, tunnel=False,
        insecure=False, cmd=None, X=False, debug=False, D=None):
        if ip == '':
            return None
        else:
            sshcommand = "-A %s@%s" % (user, ip)
            if D:
                sshcommand = "-D %s %s" % (D, sshcommand)
            if X:
                sshcommand = "-X %s" % (sshcommand)
            if cmd:
                sshcommand = "%s %s" % (sshcommand, cmd)
            if host not in ['localhost', '127.0.0.1'] and tunnel:
                sshcommand = "-o ProxyCommand='ssh -qp %s -W %%h:%%p %s@%s' %s" % (port, hostuser, host, sshcommand)
            if local is not None:
                sshcommand = "-L %s %s" % (local, sshcommand)
            if remote is not None:
                sshcommand = "-R %s %s" % (remote, sshcommand)
            if insecure:
                sshcommand = "ssh -o LogLevel=quiet -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' %s"\
                    % sshcommand
            else:
                sshcommand = "ssh %s" % sshcommand
            if debug:
                print(sshcommand)
            return sshcommand


def scp(name, ip='', host=None, port=22, hostuser=None, user=None, source=None, destination=None, recursive=None,
        tunnel=False, debug=False, download=False):
        if ip == '':
            print("No ip found. Cannot scp...")
        else:
            if host not in ['localhost', '127.0.0.1'] and tunnel:
                arguments = "-o ProxyCommand='ssh -qp %s -W %%h:%%p %s@%s'" % (port, hostuser, host)
            else:
                arguments = ''
            scpcommand = 'scp'
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
    if 'centos' in template.lower():
        user = 'centos'
    elif 'coreos' in template.lower():
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
             enableroot=True, overrides={}, iso=True, fqdn=False):
    default_gateway = gateway
    publickeys = []
    if domain is not None:
        localhostname = "%s.%s" % (name, domain)
    else:
        localhostname = name
    if os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']):
        publickeyfile = "%s/.ssh/id_rsa.pub" % os.environ['HOME']
    elif os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
        publickeyfile = "%s/.ssh/id_dsa.pub" % os.environ['HOME']
    if publickeyfile is not None:
        with open(publickeyfile, 'r') as ssh:
            publickeys.append(ssh.read().rstrip())
    if keys:
        for key in list(set(keys)):
            publickeys.append(key)
    if not publickeys:
        pprint("neither id_rsa or id_dsa public keys found in your .ssh directory, you might have trouble "
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
        content = "[Unit]\nDescription=First Boot\n\n\n[Service]\nType=oneshot\nExecStart=/root/first.sh\n"
        content += "[Install]\nWantedBy=multi-user.target\n"
        cmdunit = {"contents": content, "name": "first-boot.service"}
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
                cidr = IPAddress(netmask).netmask_bits()
                noconf = net.get('noconf')
                vips = net.get('vips')
            if noconf is not None:
                netdata += "[Match]\nName=%s\n\n[Network]\nDHCP=no\n" % nicname
            elif ip is not None and cidr is not None and not reserveip and gateway is not None:
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
                networkunits.append({"contents": netdata, "name": "static.network"})
    if networkunits:
        networkd = {"units": networkunits}
    else:
        networkd = {}
    data = {'ignition': {'version': '2.0.0', 'config': {}}, 'storage': storage, 'systemd': systemd,
            'networkd': networkd, 'passwd': {'users': [{'name': 'core', 'sshAuthorizedKeys': publickeys}]}}
    return json.dumps(data)
