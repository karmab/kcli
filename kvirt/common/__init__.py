#!/usr/bin/env python

from distutils.spawn import find_executable
import socket
import urllib2
import json
import os


def symlinks(user, repo):
    mappings = []
    url1 = 'https://api.github.com/repos/%s/%s/git/refs/heads/master' % (user, repo)
    r = urllib2.urlopen(url1)
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


def download(url, path):
    filename = os.path.basename(url)
    print("Fetching %s" % filename)
    url = urllib2.urlopen(url)
    with open("%s/%s" % (path, filename), 'wb') as output:
        output.write(url.read())


def makelink(url, path):
    filename = os.path.basename(url)
    url = urllib2.urlopen(url)
    target = url.read()
    print("Creating symlink for %s pointing to %s" % (filename, target))
    os.symlink(target, "%s/%s" % (path, filename))


def fetch(url, path, syms=None):
    if not url.startswith('http'):
        url = "https://%s" % url
    if 'github.com' not in url or 'raw.githubusercontent.com' in url:
        download(url, path)
        return
    elif 'api.github.com' not in url:
        url = url.replace('github.com/', 'api.github.com/repos/').replace('tree/master', 'contents')
    if 'contents' not in url:
        tempurl = url.replace('https://api.github.com/repos/', '')
        user = tempurl.split('/')[0]
        repo = tempurl.split('/')[1]
        syms = symlinks(user, repo)
        url = url.replace("%s/%s" % (user, repo), "%s/%s/contents" % (user, repo))
    if not os.path.exists(path):
        os.mkdir(path)
    r = urllib2.urlopen(url)
    try:
        base = json.load(r)
    except:
        print("Invalid url.Leaving...")
        os._exit(1)
    for b in base:
        if 'name' not in b or 'type' not in b or 'download_url' not in b:
            print("Invalid url.Leaving...")
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


def cloudinit(name, keys=None, cmds=[], nets=[], gateway=None, dns=None, domain=None, reserveip=False, files=[]):
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
                elif isinstance(net, dict):
                    nicname = net.get('nic', "eth%d" % index)
                    ip = net.get('ip')
                    netmask = net.get('mask')
                metadata += "  auto %s\n" % nicname
                if ip is not None and netmask is not None and not reserveip:
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
                # if dns is not None:
                #    metadatafile.write("  dns-nameservers %s\n" % dns)
                # if domain is not None:
                #    metadatafile.write("  dns-search %s\n" % domain)
    with open('/tmp/user-data', 'w') as userdata:
        userdata.write('#cloud-config\nhostname: %s\n' % name)
        if domain is not None:
            userdata.write("fqdn: %s.%s\n" % (name, domain))
        if keys is not None or os.path.exists("%s/.ssh/id_rsa.pub" % os.environ['HOME']) or os.path.exists("%s/.ssh/id_dsa.pub" % os.environ['HOME']):
            userdata.write("ssh_authorized_keys:\n")
        else:
            print("neither id_rsa.pub or id_dsa public keys found in your .ssh directory, you might have trouble accessing the vm")
        if keys is not None:
            for key in keys:
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
                        userdata.write("- %s\n" % cmd)
        if files:
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
                    # if origin.endswith('j2'):
                    #    origin = open(origin, 'r').read()
                    #    content = Environment().from_string(origin).render(name=name, gateway=gateway, dns=dns, domain=domain)
                    # else:
                    #    content = open(origin, 'r').readlines()
                    content = open(origin, 'r').readlines()
                elif content is None:
                    continue
                path = fil.get('path')
                owner = fil.get('owner', 'root')
                permissions = fil.get('permissions', '0600')
                userdata.write("- owner: %s:%s\n" % (owner, owner))
                userdata.write("  path: %s\n" % path)
                userdata.write("  permissions: '%s'\n" % (permissions))
                userdata.write("  content: | \n")
                if isinstance(content, str):
                    content = content.split('\n')
                for line in content:
                    userdata.write("     %s\n" % line.strip())
    isocmd = 'mkisofs'
    if find_executable('genisoimage') is not None:
        isocmd = 'genisoimage'
    os.system("%s --quiet -o /tmp/%s.iso --volid cidata --joliet --rock /tmp/user-data /tmp/meta-data" % (isocmd, name))


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port
