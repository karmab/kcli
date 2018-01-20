#!/usr/bin/env python

from jinja2 import Environment, FileSystemLoader
from distutils.spawn import find_executable
import errno
import fileinput
import socket
import urllib2
import json
import os
import sys
import yaml

binary_types = ['bz2', 'deb', 'jpg', 'gz', 'jpeg', 'iso', 'png', 'rpm', 'tgz', 'zip']


def symlinks(user, repo):
    mappings = []
    url1 = 'https://api.github.com/repos/%s/%s/git/refs/heads/master' % (user, repo)
    try:
        r = urllib2.urlopen(url1)
    except urllib2.HTTPError:
        print("Invalid url %s.Leaving..." % url1)
        sys.exit(1)
    base = json.load(r)
    sha = base['object']['sha']
    url2 = 'https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1' % (user, repo, sha)
    r = urllib2.urlopen(url2)
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
        print("Fetching %s" % filename)
    url = urllib2.urlopen(url)
    with open("%s/%s" % (path, filename), 'wb') as output:
        output.write(url.read())


def makelink(url, path, debug=False):
    filename = os.path.basename(url)
    url = urllib2.urlopen(url)
    target = url.read()
    if debug:
        print("Creating symlink for %s pointing to %s" % (filename, target))
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
        r = urllib2.urlopen(url)
    except urllib2.HTTPError:
        print("Invalid url %s.Leaving..." % url)
        os._exit(1)
    try:
        base = json.load(r)
    except:
        print("Couldnt load json data from url %s.Leaving..." % url)
        os._exit(1)
    if not isinstance(base, list):
        base = [base]
    for b in base:
        if 'name' not in b or 'type' not in b or 'download_url' not in b:
            print("Missing data in url %s.Leaving..." % url)
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


def cloudinit(name, keys=[], cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[], enableroot=True, overrides={}):
    default_gateway = gateway
    with open('/tmp/meta-data', 'w') as metadatafile:
        if domain is not None:
            localhostname = "%s.%s" % (name, domain)
        else:
            localhostname = name
        metadatafile.write('instance-id: XXX\nlocal-hostname: %s\n' % localhostname)
        metadata = ''
        if nets:
            for index, net in enumerate(nets):
                if isinstance(net, str):
                    if index == 0:
                        continue
                    nicname = "eth%d" % index
                    ip = None
                    netmask = None
                    noconf = None
                elif isinstance(net, dict):
                    nicname = net.get('nic', "eth%d" % index)
                    ip = net.get('ip')
                    netmask = next((e for e in [net.get('mask'), net.get('netmask')] if e is not None), None)
                    noconf = net.get('noconf')
                metadata += "  auto %s\n" % nicname
                if noconf is not None:
                    metadata += "  iface %s inet manual\n" % nicname
                elif ip is not None and netmask is not None and not reserveip:
                    metadata += "  iface %s inet static\n" % nicname
                    metadata += "  address %s\n" % ip
                    metadata += "  netmask %s\n" % netmask
                    gateway = net.get('gateway')
                    if index == 0 and default_gateway is not None:
                        metadata += "  gateway %s\n" % default_gateway
                    elif gateway is not None:
                        metadata += "  gateway %s\n" % gateway
                    dns = net.get('dns')
                    if dns is not None:
                        metadata += "  dns-nameservers %s\n" % dns
                    domain = net.get('domain')
                    if domain is not None:
                        metadatafile.write("  dns-search %s\n" % domain)
                else:
                    metadata += "  iface %s inet dhcp\n" % nicname
            if metadata:
                metadatafile.write("network-interfaces: |\n")
                metadatafile.write(metadata)
    with open('/tmp/user-data', 'w') as userdata:
        userdata.write('#cloud-config\nhostname: %s\n' % name)
        if enableroot:
            userdata.write("ssh_pwauth: True\ndisable_root: false\n")
        if domain is not None:
            userdata.write("fqdn: %s.%s\n" % (name, domain))
        if keys or os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']) or os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
            userdata.write("ssh_authorized_keys:\n")
        else:
            print("neither id_rsa.pub or id_dsa public keys found in your .ssh directory, you might have trouble accessing the vm")
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
                userdata.write("runcmd:\n")
                for cmd in cmds:
                    if cmd.startswith('#'):
                        continue
                    else:
                        newcmd = Environment(block_start_string='[%', block_end_string='%]', variable_start_string='[[', variable_end_string=']]').from_string(cmd).render(overrides)
                        userdata.write("- %s\n" % newcmd)
        if files:
            binary = False
            userdata.write('ssh_pwauth: True\n')
            userdata.write('disable_root: false\n')
            userdata.write("write_files:\n")
            for fil in files:
                if not isinstance(fil, dict):
                    continue
                origin = fil.get('origin')
                content = fil.get('content')
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
                        env = Environment(block_start_string='[%', block_end_string='%]', variable_start_string='[[', variable_end_string=']]', loader=FileSystemLoader(basedir))
                        templ = env.get_template(os.path.basename(origin))
                        fileentries = templ.render(overrides)
                        content = [line.rstrip() for line in fileentries.split('\n') if line.rstrip() != '']
                    else:
                        content = open(origin, 'r').readlines()
                elif content is None:
                    continue
                path = fil.get('path')
                owner = fil.get('owner', 'root')
                mode = fil.get('mode', '0600')
                permissions = fil.get('permissions', mode)
                userdata.write("- owner: %s:%s\n" % (owner, owner))
                userdata.write("  path: %s\n" % path)
                userdata.write("  permissions: '%s'\n" % (permissions))
                if binary:
                    userdata.write("  content: !!binary | \n")
                else:
                    userdata.write("  content: | \n")
                if isinstance(content, str):
                    content = content.split('\n')
                for line in content:
                    userdata.write("     %s\n" % line.rstrip())
    isocmd = 'mkisofs'
    if find_executable('genisoimage') is not None:
        isocmd = 'genisoimage'
    os.system("%s --quiet -o /tmp/%s.ISO --volid cidata --joliet --rock /tmp/user-data /tmp/meta-data" % (isocmd, name))


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
        print('\033[1;%sm%s\033[0;0m' % (color, text))
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
    input = raw_input(message)
    if input.lower() not in ['y', 'yes']:
        pprint("Leaving...", color='red')
        os._exit(1)
    return


def lastvm(name, delete=False):
    configdir = "%s/.kcli/" % os.environ.get('HOME')
    vmfile = "%s/vm" % configdir
    if not os.path.exists(configdir):
        os.mkdir(configdir)
    if delete:
        if not os.path.exists(vmfile):
            return
        else:
            os.system("sed -i '/%s/d' %s/vm" % (name, configdir))
        return
    if not os.path.exists(vmfile) or os.stat(vmfile).st_size == 0:
        with open(vmfile, 'w') as f:
            f.write(name)
        return
    firstline = True
    for line in fileinput.input(vmfile, inplace=True):
        line = "%s\n%s" % (name, line) if firstline else line
        print line,
        firstline = False


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
