#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# coding=utf-8

from copy import deepcopy
from distutils.spawn import find_executable
from getpass import getuser
from kvirt.config import Kconfig
from kvirt.examples import plandatacreate, vmdatacreate, hostcreate, _list, plancreate, planinfo, productinfo, start
from kvirt.examples import repocreate, isocreate, kubegenericcreate, kubek3screate, kubeopenshiftcreate, kubekindcreate
from kvirt.examples import dnscreate, diskcreate, diskdelete, vmcreate, vmconsole, vmexport, niccreate, nicdelete
from kvirt.examples import disconnectercreate, appopenshiftcreate, plantemplatecreate
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt import version
from kvirt.defaults import IMAGES, VERSION, LOCAL_OPENSHIFT_APPS, SSH_PUB_LOCATIONS
from prettytable import PrettyTable
import argcomplete
import argparse
from argparse import RawDescriptionHelpFormatter as rawhelp
from ipaddress import ip_address
from glob import glob
from kvirt import common
from kvirt.common import error, pprint, success, warning, ssh, _ssh_credentials, container_mode
from kvirt import nameutils
import os
import random
import requests
from subprocess import call
import sys
from urllib.parse import urlparse
import yaml


def cache_vms(baseconfig, region, zone, namespace):
    cache_file = "%s/.kcli/%s_vms.yml" % (os.environ['HOME'], baseconfig.client)
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as vms:
            _list = yaml.safe_load(vms)
        pprint("Using cache information...")
    else:
        config = Kconfig(client=baseconfig.client, debug=baseconfig.debug, region=region, zone=zone,
                         namespace=namespace)
        _list = config.k.list()
        with open(cache_file, 'w') as c:
            pprint(f"Caching results for {baseconfig.client}...")
            try:
                yaml.safe_dump(_list, c, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                               sort_keys=False)
            except:
                yaml.safe_dump(_list, c, default_flow_style=False, encoding='utf-8', allow_unicode=True,
                               sort_keys=False)
    return _list


def valid_fqdn(name):
    if name is not None and '/' in name:
        msg = "Vm name can't include /"
        raise argparse.ArgumentTypeError(msg)
    return name


def valid_url(url):
    if url is not None:
        parsed_url = urlparse(url)
        if parsed_url.scheme == '' or parsed_url.netloc == '':
            msg = "Malformed url"
            raise argparse.ArgumentTypeError(msg)
    return url


def valid_members(members):
    try:
        return members[1:-1].split(',')
    except:
        msg = "Incorrect members list"
        raise argparse.ArgumentTypeError(msg)


def valid_cluster(name):
    if name is not None:
        if '/' in name:
            msg = "Cluster name can't include /"
            raise argparse.ArgumentTypeError(msg)
    return name


def alias(text):
    return "Alias for %s" % text


def get_subparser_print_help(parser, subcommand):
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)]
    for subparsers_action in subparsers_actions:
        for choice, subparser in subparsers_action.choices.items():
            if choice == subcommand:
                subparser.print_help()
                return


def get_subparser(parser, subcommand):
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)]
    for subparsers_action in subparsers_actions:
        for choice, subparser in subparsers_action.choices.items():
            if choice == subcommand:
                return subparser


def get_version(args):
    full_version = "version: %s" % VERSION
    versiondir = os.path.dirname(version.__file__)
    git_file = '%s/git' % versiondir
    git_version = 'N/A'
    git_date = ''
    if os.path.exists(git_file) and os.stat(git_file).st_size > 0:
        git_version, git_date = open(git_file).read().rstrip().split(' ')
        git_date = '(%s)' % git_date
    full_version += " commit: %s %s" % (git_version, git_date)
    update = 'N/A'
    if git_version != 'N/A':
        try:
            upstream_version = requests.get("https://api.github.com/repos/karmab/kcli/commits/master").json()['sha'][:7]
            update = True if upstream_version != git_version else False
        except:
            pass
    full_version += " Available Updates: %s" % update
    print(full_version)


def delete_cache(args):
    yes_top = args.yes_top
    yes = args.yes
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    cache_file = "%s/.kcli/%s_vms.yml" % (os.environ['HOME'], baseconfig.client)
    if os.path.exists(cache_file):
        pprint(f"Deleting cache on {baseconfig.client}")
        os.remove(cache_file)
    else:
        warning(f"No cache file found for {baseconfig.client}")


def start_vm(args):
    """Start vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    codes = []
    for name in names:
        pprint(f"Starting vm {name}...")
        result = k.start(name)
        code = common.handle_response(result, name, element='', action='started')
        codes.append(code)
    sys.exit(1 if 1 in codes else 0)


def start_container(args):
    """Start containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    for name in names:
        pprint(f"Starting container {name}...")
        cont.start_container(name)


def stop_vm(args):
    """Stop vms"""
    soft = args.soft
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    if config.extraclients:
        ks = config.extraclients
        ks.update({config.client: config.k})
    else:
        ks = {config.client: config.k}
    codes = []
    for cli in ks:
        k = ks[cli]
        for name in names:
            pprint(f"Stopping vm {name} in {cli}...")
            result = k.stop(name, soft=soft)
            code = common.handle_response(result, name, element='', action='stopped')
            codes.append(code)
    sys.exit(1 if 1 in codes else 0)


def stop_container(args):
    """Stop containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    if config.extraclients:
        ks = config.extraclients
        ks.update({config.client: config.k})
    else:
        ks = {config.client: config.k}
    for cli in ks:
        cont = Kcontainerconfig(config, client=args.containerclient).cont
        for name in names:
            pprint(f"Stopping container {name} in {cli}...")
            cont.stop_container(name)


def restart_vm(args):
    """Restart vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    codes = []
    for name in names:
        pprint(f"Restarting vm {name}...")
        result = k.restart(name)
        code = common.handle_response(result, name, element='', action='restarted')
        codes.append(code)
    sys.exit(1 if 1 in codes else 0)


def restart_container(args):
    """Restart containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    for name in names:
        pprint(f"Restarting container {name}...")
        cont.stop_container(name)
        cont.start_container(name)


def console_vm(args):
    """Vnc/Spice/Serial Vm console"""
    serial = args.serial
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    name = common.get_lastvm(config.client) if not args.name else args.name
    k = config.k
    tunnel = config.tunnel
    if serial:
        k.serialconsole(name)
    else:
        k.console(name=name, tunnel=tunnel)


def console_container(args):
    """Container console"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    name = common.get_lastvm(config.client) if not args.name else args.name
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    cont.console_container(name)
    return


def delete_vm(args):
    """Delete vm"""
    snapshots = args.snapshots
    count = args.count
    yes_top = args.yes_top
    yes = args.yes
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        names = args.names
        if not names:
            error("Can't delete vms on multiple hosts without specifying their names")
            sys.exit(1)
    else:
        allclients = {config.client: config.k}
        names = [common.get_lastvm(config.client)] if not args.names else args.names
    if count > 1:
        if len(args.names) == 1:
            names = ["%s-%d" % (args.names[0], number) for number in range(count)]
        else:
            error("Using count when deleting vms requires specifying an unique name")
            sys.exit(1)
    dnsclients = allclients.copy()
    for cli in sorted(allclients):
        k = allclients[cli]
        if not yes and not yes_top:
            common.confirm("Are you sure?")
        codes = []
        for name in names:
            pprint(f"Deleting vm {name} on {cli}")
            dnsclient, domain = k.dnsinfo(name)
            if config.rhnunregister:
                image = k.info(name).get('image')
                if 'rhel' in image:
                    pprint(f"Removing rhel subscription for {name}")
                    ip, vmport = _ssh_credentials(k, name)[1:]
                    cmd = "subscription-manager unregister"
                    sshcmd = ssh(name, ip=ip, user='root', tunnel=config.tunnel,
                                 tunnelhost=config.tunnelhost, tunnelport=config.tunnelport,
                                 tunneluser=config.tunneluser, insecure=True, cmd=cmd, vmport=vmport)
                    os.system(sshcmd)
                else:
                    warning(f"vm {name} doesnt appear as a rhel box. Skipping unregistration")
            result = k.delete(name, snapshots=snapshots)
            if result['result'] == 'success':
                success(f"{name} deleted")
                codes.append(0)
                common.set_lastvm(name, cli, delete=True)
            else:
                reason = result['reason']
                codes.append(1)
                error(f"Could not delete {name} because {reason}")
                common.set_lastvm(name, cli, delete=True)
            if dnsclient is not None and domain is not None:
                pprint(f"Deleting Dns entry for {name} in {domain}")
                if dnsclient in dnsclients:
                    z = dnsclients[dnsclient]
                else:
                    z = Kconfig(client=dnsclient).k
                    dnsclients[dnsclient] = z
                z.delete_dns(name, domain)
            cluster = name.split('-')[0] if '-master-' in name or '-worker-' in name else None
            clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
            if cluster is not None and os.path.exists(clusterdir):
                os.environ['KUBECONFIG'] = "%s/auth/kubeconfig" % clusterdir
                if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
                    with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
                        installparam = yaml.safe_load(install)
                        kubetype = installparam.get('kubetype', 'kubectl')
                        binary = 'oc' if kubetype == 'openshift' else 'kubectl'
                        domain = installparam.get('domain')
                        if domain is not None:
                            try:
                                pprint(f"Deleting node {name}.{domain} from your cluster")
                                call(f'{binary} delete node {name}.{domain}', shell=True)
                            except:
                                continue
    sys.exit(1 if 1 in codes else 0)


def delete_container(args):
    """Delete container"""
    yes = args.yes
    yes_top = args.yes_top
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        names = args.names
    else:
        allclients = {config.client: config.k}
        names = args.names
    for cli in sorted(allclients):
        if not yes and not yes_top:
            common.confirm("Are you sure?")
        codes = [0]
        cont = Kcontainerconfig(config, client=args.containerclient).cont
        for name in names:
            pprint(f"Deleting container {name} on {cli}")
            cont.delete_container(name)
    sys.exit(1 if 1 in codes else 0)


def download_image(args):
    """Download Image"""
    pool = args.pool
    image = args.image
    cmd = args.cmd
    url = args.url
    size = args.size
    arch = args.arch
    openstack = args.openstack
    update_profile = not args.skip_profile
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(pool=pool, image=image, download=True, cmd=cmd, url=url, update_profile=update_profile,
                                size=size, arch=arch, kvm_openstack=openstack)
    if result['result'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


def download_iso(args):
    """Download ISO"""
    pool = args.pool
    url = args.url
    iso = args.iso if args.iso is not None else os.path.basename(url)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(pool=pool, image=iso, download=True, url=url, update_profile=False)
    if result['result'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


def delete_image(args):
    images = args.images
    pool = args.pool
    yes = args.yes
    yes_top = args.yes_top
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
    else:
        allclients = {config.client: config.k}
    for cli in sorted(allclients):
        k = allclients[cli]
        if not yes and not yes_top:
            common.confirm("Are you sure?")
        codes = []
        for image in images:
            clientprofile = "%s_%s" % (cli, image)
            imgprofiles = [p for p in config.profiles if 'image' in config.profiles[p] and
                           config.profiles[p]['image'] == os.path.basename(image) and
                           p.startswith('%s_' % cli)]
            pprint(f"Deleting image {image} on {cli}")
            if clientprofile in config.profiles and 'image' in config.profiles[clientprofile]:
                profileimage = config.profiles[clientprofile]['image']
                config.delete_profile(clientprofile, quiet=True)
                result = k.delete_image(profileimage, pool=pool)
            elif imgprofiles:
                imgprofile = imgprofiles[0]
                config.delete_profile(imgprofile, quiet=True)
                result = k.delete_image(image, pool=pool)
            else:
                result = k.delete_image(image, pool=pool)
            if result['result'] == 'success':
                success(f"{image} deleted")
                codes.append(0)
            else:
                reason = result['reason']
                error(f"Could not delete image {image} because {reason}")
                codes.append(1)
    sys.exit(1 if 1 in codes else 0)


def create_profile(args):
    """Create profile"""
    profile = args.profile
    overrides = common.get_overrides(param=args.param)
    baseconfig = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
    result = baseconfig.create_profile(profile, overrides=overrides)
    code = common.handle_response(result, profile, element='Profile', action='created', client=baseconfig.client)
    return code


def delete_profile(args):
    """Delete profile"""
    profile = args.profile
    baseconfig = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
    pprint(f"Deleting on {baseconfig.client}")
    result = baseconfig.delete_profile(profile)
    code = common.handle_response(result, profile, element='Profile', action='deleted', client=baseconfig.client)
    return code
    # sys.exit(0) if result['result'] == 'success' else sys.exit(1)


def update_profile(args):
    """Update profile"""
    profile = args.profile
    overrides = common.get_overrides(param=args.param)
    baseconfig = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
    result = baseconfig.update_profile(profile, overrides=overrides)
    code = common.handle_response(result, profile, element='Profile', action='updated', client=baseconfig.client)
    return code


def info_vm(args):
    """Get info on vm"""
    output = args.output
    fields = args.fields.split(',') if args.fields is not None else []
    values = args.values
    config = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if config.cache:
        names = [common.get_lastvm(config.client)] if not args.names else args.names
        _list = cache_vms(config, args.region, args.zone, args.namespace)
        vms = {vm['name']: vm for vm in _list}
    else:
        config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
        names = [common.get_lastvm(config.client)] if not args.names else args.names
    for name in names:
        if config.cache and name in vms:
            data = vms[name]
        else:
            data = config.k.info(name, debug=args.debug)
        if data:
            print(common.print_info(data, output=output, fields=fields, values=values, pretty=True))


def enable_host(args):
    """Enable host"""
    host = args.name
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.enable_host(host)
    if result['result'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


def disable_host(args):
    """Disable host"""
    host = args.name
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.disable_host(host)
    if result['result'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


def delete_host(args):
    """Delete host"""
    common.delete_host(args.name)


def sync_host(args):
    """Handle host"""
    hosts = args.names
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(sync=hosts)
    if result['result'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


def list_vm(args):
    """List vms"""
    filters = args.filters
    if args.client is not None and args.client == 'all':
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
        args.client = ','.join(baseconfig.clients)
    if args.client is not None and ',' in args.client:
        vms = PrettyTable(["Name", "Host", "Status", "Ips", "Source", "Plan", "Profile"])
        for client in args.client.split(','):
            config = Kbaseconfig(client=client, debug=args.debug, quiet=True)
            if config.cache:
                _list = cache_vms(config, args.region, args.zone, args.namespace)
            else:
                config = Kconfig(client=client, debug=args.debug, region=args.region,
                                 zone=args.zone, namespace=args.namespace)
                _list = config.k.list()
            for vm in _list:
                name = vm.get('name')
                status = vm.get('status')
                ip = vm.get('ip', '')
                source = vm.get('image', '')
                plan = vm.get('plan', '')
                profile = vm.get('profile', '')
                vminfo = [name, client, status, ip, source, plan, profile]
                if filters:
                    if status == filters:
                        vms.add_row(vminfo)
                else:
                    vms.add_row(vminfo)
        print(vms)
    else:
        vms = PrettyTable(["Name", "Status", "Ips", "Source", "Plan", "Profile"])
        config = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
        if config.cache:
            _list = cache_vms(config, args.region, args.zone, args.namespace)
        else:
            config = Kconfig(client=args.client, debug=args.debug, region=args.region,
                             zone=args.zone, namespace=args.namespace)
            _list = config.k.list()
        for vm in _list:
            name = vm.get('name')
            status = vm.get('status')
            ip = vm.get('ip', '')
            source = vm.get('image', '')
            plan = vm.get('plan', '')
            profile = vm.get('profile', '')
            vminfo = [name, status, ip, source, plan, profile]
            if filters:
                if status == filters:
                    vms.add_row(vminfo)
            else:
                vms.add_row(vminfo)
        print(vms)
    return


def list_container(args):
    """List containers"""
    filters = args.filters
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    pprint("Listing containers...")
    containers = PrettyTable(["Name", "Status", "Image", "Plan", "Command", "Ports", "Deploy"])
    for container in cont.list_containers():
        if filters:
            status = container[1]
            if status == filters:
                containers.add_row(container)
        else:
            containers.add_row(container)
    print(containers)
    return


def profilelist_container(args):
    """List container profiles"""
    short = args.short
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    profiles = baseconfig.list_containerprofiles()
    if short:
        profilestable = PrettyTable(["Profile"])
        for profile in sorted(profiles):
            profilename = profile[0]
            profilestable.add_row([profilename])
    else:
        profilestable = PrettyTable(["Profile", "Image", "Nets", "Ports", "Volumes", "Cmd"])
        for profile in sorted(profiles):
            profilestable.add_row(profile)
    profilestable.align["Profile"] = "l"
    print(profilestable)
    return


def list_containerimage(args):
    """List container images"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.type != 'kvm':
        error("Operation not supported on this kind of client.Leaving...")
        sys.exit(1)
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    common.pprint("Listing images...")
    images = PrettyTable(["Name"])
    for image in cont.list_images():
        images.add_row([image])
    print(images)
    return


def list_host(args):
    """List hosts"""
    clientstable = PrettyTable(["Client", "Type", "Enabled", "Current"])
    clientstable.align["Client"] = "l"
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    for client in sorted(baseconfig.clients):
        enabled = baseconfig.ini[client].get('enabled', True)
        _type = baseconfig.ini[client].get('type', 'kvm')
        if client == baseconfig.client:
            clientstable.add_row([client, _type, enabled, 'X'])
        else:
            clientstable.add_row([client, _type, enabled, ''])
    print(clientstable)
    return


def list_lb(args):
    """List lbs"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    loadbalancers = config.list_loadbalancers()
    if short:
        loadbalancerstable = PrettyTable(["Loadbalancer"])
        for lb in sorted(loadbalancers):
            loadbalancerstable.add_row([lb])
    else:
        loadbalancerstable = PrettyTable(["LoadBalancer", "IPAddress", "IPProtocol", "Ports", "Target"])
        for lb in sorted(loadbalancers):
            loadbalancerstable.add_row(lb)
    loadbalancerstable.align["Loadbalancer"] = "l"
    print(loadbalancerstable)
    return


def info_profile(args):
    """List profiles"""
    profile = args.profile
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    profiles = baseconfig.list_profiles()
    for entry in profiles:
        if entry[0] == profile:
            profile, flavor, pool, disks, image, nets, cloudinit, nested, reservedns, reservehost = entry
            print(f"profile: {profile}")
            print(f"flavor: {flavor}")
            print(f"pool: {pool}")
            print(f"disks: {disks}")
            print(f"image: {image}")
            print(f"nets: {nets}")
            print(f"cloudinit: {cloudinit}")
            print(f"nested: {nested}")
            print(f"reservedns: {reservedns}")
            print(f"reservehost: {reservehost}")
            sys.exit(0)
            break
    error(f"Profile {profile} doesn't exist")
    sys.exit(1)


def list_profile(args):
    """List profiles"""
    short = args.short
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    profiles = baseconfig.list_profiles()
    if short:
        profilestable = PrettyTable(["Profile"])
        for profile in sorted(profiles):
            profilename = profile[0]
            profilestable.add_row([profilename])
    else:
        profilestable = PrettyTable(["Profile", "Flavor",
                                     "Pool", "Disks", "Image",
                                     "Nets", "Cloudinit", "Nested",
                                     "Reservedns", "Reservehost"])
        for profile in sorted(profiles):
            profilestable.add_row(profile)
    profilestable.align["Profile"] = "l"
    print(profilestable)
    return


def list_dns(args):
    """List flavors"""
    short = args.short
    domain = args.domain
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    entries = k.list_dns(domain)
    if short:
        dnstable = PrettyTable(["Entry"])
        for entry in sorted(entries):
            entryname = entry[0]
            dnstable.add_row([entryname])
    else:
        dnstable = PrettyTable(["Entry", "Type", "TTL", "Data"])
        for entry in sorted(entries):
            dnstable.add_row(entry)
    dnstable.align["Flavor"] = "l"
    print(dnstable)
    return


def list_flavor(args):
    """List flavors"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    flavors = k.flavors()
    if short:
        flavorstable = PrettyTable(["Flavor"])
        for flavor in sorted(flavors):
            flavorname = flavor[0]
            flavorstable.add_row([flavorname])
    else:
        flavorstable = PrettyTable(["Flavor", "Numcpus", "Memory"])
        for flavor in sorted(flavors):
            flavorstable.add_row(flavor)
    flavorstable.align["Flavor"] = "l"
    print(flavorstable)
    return


def list_image(args):
    """List images"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    imagestable = PrettyTable(["Images"])
    imagestable.align["Images"] = "l"
    for image in k.volumes():
        imagestable.add_row([image])
    print(imagestable)
    return


def list_iso(args):
    """List isos"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    isostable = PrettyTable(["Iso"])
    isostable.align["Iso"] = "l"
    for iso in k.volumes(iso=True):
        isostable.add_row([iso])
    print(isostable)
    return


def list_network(args):
    """List networks"""
    short = args.short
    subnets = args.subnets
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    if not subnets:
        networks = k.list_networks()
        pprint("Listing Networks...")
        if short:
            networkstable = PrettyTable(["Network"])
            for network in sorted(networks):
                networkstable.add_row([network])
        else:
            networkstable = PrettyTable(["Network", "Type", "Cidr", "Dhcp", "Domain", "Mode"])
            for network in sorted(networks):
                networktype = networks[network]['type']
                cidr = networks[network]['cidr']
                dhcp = networks[network]['dhcp']
                mode = networks[network]['mode']
                if 'domain' in networks[network]:
                    domain = networks[network]['domain']
                else:
                    domain = 'N/A'
                networkstable.add_row([network, networktype, cidr, dhcp, domain, mode])
        networkstable.align["Network"] = "l"
        print(networkstable)
        return
    else:
        subnets = k.list_subnets()
        pprint("Listing Subnets...")
        if short:
            subnetstable = PrettyTable(["Subnets"])
            for subnet in sorted(subnets):
                subnetstable.add_row([subnet])
        else:
            subnetstable = PrettyTable(["Subnet", "Az", "Cidr", "Network"])
            for subnet in sorted(subnets):
                cidr = subnets[subnet]['cidr']
                az = subnets[subnet]['az']
                if 'network' in subnets[subnet]:
                    network = subnets[subnet]['network']
                else:
                    network = 'N/A'
                subnetstable.add_row([subnet, az, cidr, network])
        subnetstable.align["Network"] = "l"
        print(subnetstable)
        return


def list_plan(args):
    """List plans"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        plans = PrettyTable(["Plan", "Host", "Vms"])
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        for cli in sorted(allclients):
            currentconfig = Kconfig(client=cli, debug=args.debug, region=args.region, zone=args.zone,
                                    namespace=args.namespace)
            for plan in currentconfig.list_plans():
                planname = plan[0]
                planvms = plan[1]
                plans.add_row([planname, cli, planvms])
    else:
        plans = PrettyTable(["Plan", "Vms"])
        for plan in config.list_plans():
            planname = plan[0]
            planvms = plan[1]
            plans.add_row([planname, planvms])
    print(plans)
    return


def choose_parameter_file(paramfile):
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    return paramfile


def get_cluster_parameter_file(paramfile):
    clustersdir = os.path.expanduser("~/.kcli/clusters")
    if (paramfile is None or not os.path.exists(paramfile)) and os.environ['KUBECONFIG'].startswith(clustersdir):
        cluster = os.environ['KUBECONFIG'].replace("%s/" % clustersdir, '').split('/')[0]
        clusterparamfile = "%s/%s/kcli_parameters.yml" % (clustersdir, cluster)
        if os.path.exists(clusterparamfile):
            paramfile = clusterparamfile
    return paramfile


def create_app_generic(args):
    apps = args.apps
    outputdir = args.outputdir
    if outputdir is not None:
        if container_mode() and not outputdir.startswith('/'):
            outputdir = "/workdir/%s" % outputdir
        if os.path.exists(outputdir) and os.path.isfile(outputdir):
            error("Invalid outputdir %s" % outputdir)
            sys.exit(1)
        elif not os.path.exists(outputdir):
            os.mkdir(outputdir)
    paramfile = choose_parameter_file(args.paramfile)
    if find_executable('kubectl') is None:
        error("You need kubectl to install apps")
        sys.exit(1)
    if 'KUBECONFIG' not in os.environ:
        error("KUBECONFIG env variable needs to be set")
        sys.exit(1)
    elif not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = "%s/%s" % (os.getcwd(), os.environ['KUBECONFIG'])
    paramfile = get_cluster_parameter_file(paramfile)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    available_apps = baseconfig.list_apps_generic(quiet=True)
    for app in apps:
        if app not in available_apps:
            error(f"app {app} not available. Skipping...")
            continue
        pprint(f"Adding app {app}")
        overrides['%s_version' % app] = overrides['%s_version' % app] if '%s_version' % app in overrides else 'latest'
        baseconfig.create_app_generic(app, overrides, outputdir=outputdir)


def create_app_openshift(args):
    apps = args.apps
    outputdir = args.outputdir
    if outputdir is not None:
        if container_mode() and not outputdir.startswith('/'):
            outputdir = "/workdir/%s" % outputdir
        if os.path.exists(outputdir) and os.path.isfile(outputdir):
            error(f"Invalid outputdir {outputdir}")
            sys.exit(1)
        elif not os.path.exists(outputdir):
            os.mkdir(outputdir)
    paramfile = choose_parameter_file(args.paramfile)
    if find_executable('oc') is None:
        error("You need oc to install apps")
        sys.exit(1)
    if 'KUBECONFIG' not in os.environ:
        error("KUBECONFIG env variable needs to be set")
        sys.exit(1)
    elif not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = "%s/%s" % (os.getcwd(), os.environ['KUBECONFIG'])
    paramfile = get_cluster_parameter_file(paramfile)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    for app in apps:
        if app in LOCAL_OPENSHIFT_APPS:
            name = app
        else:
            name, source, channel, csv, description, namespace, channels, crd = common.olm_app(app)
            if name is None:
                error(f"Couldn't find any app matching {app}. Skipping...")
                continue
            if 'channel' in overrides:
                overrides_channel = overrides['channel']
                if overrides_channel not in channels:
                    error(f"Target channel {channel} not found in {channels}. Skipping...")
                    continue
                else:
                    channel = overrides_channel
            app_data = {'name': name, 'source': source, 'channel': channel, 'csv': csv, 'namespace': namespace,
                        'crd': crd}
            overrides.update(app_data)
        pprint(f"Adding app {app}")
        baseconfig.create_app_openshift(name, overrides, outputdir=outputdir)


def delete_app_generic(args):
    apps = args.apps
    paramfile = choose_parameter_file(args.paramfile)
    if find_executable('kubectl') is None:
        error("You need kubectl to install apps")
        sys.exit(1)
    if 'KUBECONFIG' not in os.environ:
        error("KUBECONFIG env variable needs to be set")
        sys.exit(1)
    elif not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = "%s/%s" % (os.getcwd(), os.environ['KUBECONFIG'])
    paramfile = get_cluster_parameter_file(paramfile)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    available_apps = baseconfig.list_apps_generic(quiet=True)
    for app in apps:
        if app not in available_apps:
            error(f"app {app} not available. Skipping...")
            continue
        pprint(f"Deleting app {app}")
        overrides['%s_version' % app] = overrides['%s_version' % app] if '%s_version' % app in overrides else 'latest'
        baseconfig.delete_app_generic(app, overrides)


def delete_app_openshift(args):
    apps = args.apps
    paramfile = choose_parameter_file(args.paramfile)
    if find_executable('oc') is None:
        error("You need oc to install apps")
        sys.exit(1)
    if 'KUBECONFIG' not in os.environ:
        error("KUBECONFIG env variable needs to be set")
        sys.exit(1)
    elif not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = "%s/%s" % (os.getcwd(), os.environ['KUBECONFIG'])
    paramfile = get_cluster_parameter_file(paramfile)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    for app in apps:
        if app in LOCAL_OPENSHIFT_APPS:
            name = app
        else:
            name, source, channel, csv, description, namespace, channels, crd = common.olm_app(app)
            if name is None:
                error(f"Couldn't find any app matching {app}. Skipping...")
                continue
            app_data = {'name': name, 'source': source, 'channel': channel, 'csv': csv, 'namespace': namespace,
                        'crd': crd}
            overrides.update(app_data)
        pprint(f"Deleting app {name}")
        baseconfig.delete_app_openshift(app, overrides)


def list_apps_generic(args):
    """List generic kube apps"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    apps = PrettyTable(["Name"])
    for app in baseconfig.list_apps_generic(quiet=True):
        apps.add_row([app])
    print(apps)


def list_apps_openshift(args):
    """List openshift kube apps"""
    if find_executable('oc') is None:
        error("You need oc to list apps")
        sys.exit(1)
    if 'KUBECONFIG' not in os.environ:
        error("KUBECONFIG env variable needs to be set")
        sys.exit(1)
    elif not os.path.isabs(os.environ['KUBECONFIG']):
        os.environ['KUBECONFIG'] = "%s/%s" % (os.getcwd(), os.environ['KUBECONFIG'])
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    apps = PrettyTable(["Name"])
    for app in baseconfig.list_apps_openshift(quiet=True):
        apps.add_row([app])
    print(apps)


def list_kube(args):
    """List kube"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        kubestable = PrettyTable(["Cluster", "Type", "Plan", "Host", "Vms"])
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        for cli in sorted(allclients):
            currentconfig = Kconfig(client=cli, debug=args.debug, region=args.region, zone=args.zone,
                                    namespace=args.namespace)
            kubes = currentconfig.list_kubes()
            for kubename in kubes:
                kube = kubes[kubename]
                kubetype = kube['type']
                kubeplan = kube['plan']
                kubevms = kube['vms']
                kubestable.add_row([kubename, kubetype, kubeplan, cli, kubevms])
    else:
        kubestable = PrettyTable(["Cluster", "Type", "Plan", "Vms"])
        kubes = config.list_kubes()
        for kubename in kubes:
            kube = kubes[kubename]
            kubetype = kube['type']
            kubevms = kube['vms']
            kubeplan = kube['plan']
            kubestable.add_row([kubename, kubetype, kubeplan, kubevms])
    print(kubestable)
    return


def list_pool(args):
    """List pools"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pools = k.list_pools()
    if short:
        poolstable = PrettyTable(["Pool"])
        for pool in sorted(pools):
            poolstable.add_row([pool])
    else:
        poolstable = PrettyTable(["Pool", "Path"])
        for pool in sorted(pools):
            poolpath = k.get_pool_path(pool)
            poolstable.add_row([pool, poolpath])
    poolstable.align["Pool"] = "l"
    print(poolstable)
    return


def list_product(args):
    """List products"""
    group = args.group
    repo = args.repo
    search = args.search
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if search is not None:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        products = PrettyTable(["Repo", "Product", "Group", "Description", "Numvms", "Memory"])
        products.align["Repo"] = "l"
        productsinfo = baseconfig.list_products(repo=repo)
        for prod in sorted(productsinfo, key=lambda x: (x['repo'], x['group'], x['name'])):
            name = prod['name']
            repo = prod['repo']
            prodgroup = prod['group']
            description = prod.get('description', 'N/A')
            if search.lower() not in name.lower() and search.lower() not in description.lower():
                continue
            if group is not None and prodgroup != group:
                continue
            numvms = prod.get('numvms', 'N/A')
            memory = prod.get('memory', 'N/A')
            group = prod.get('group', 'N/A')
            products.add_row([repo, name, group, description, numvms, memory])
    else:
        products = PrettyTable(["Repo", "Product", "Group", "Description", "Numvms", "Memory"])
        products.align["Repo"] = "l"
        productsinfo = baseconfig.list_products(group=group, repo=repo)
        for product in sorted(productsinfo, key=lambda x: (x['repo'], x['group'], x['name'])):
            name = product['name']
            repo = product['repo']
            description = product.get('description', 'N/A')
            numvms = product.get('numvms', 'N/A')
            memory = product.get('memory', 'N/A')
            group = product.get('group', 'N/A')
            products.add_row([repo, name, group, description, numvms, memory])
    print(products)
    return


def list_repo(args):
    """List repos"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    repos = PrettyTable(["Repo", "Url"])
    repos.align["Repo"] = "l"
    reposinfo = baseconfig.list_repos()
    for repo in sorted(reposinfo):
        url = reposinfo[repo]
        repos.add_row([repo, url])
    print(repos)
    return


def list_vmdisk(args):
    """List vm disks"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint("Listing disks...")
    diskstable = PrettyTable(["Name", "Pool", "Path"])
    diskstable.align["Name"] = "l"
    disks = k.list_disks()
    for disk in sorted(disks):
        path = disks[disk]['path']
        pool = disks[disk]['pool']
        diskstable.add_row([disk, pool, path])
    print(diskstable)
    return


def create_openshift_iso(args):
    cluster = args.cluster
    ignitionfile = args.ignitionfile
    direct = args.direct
    overrides = common.get_overrides(param=args.param)
    client = 'fake' if common.need_fake() else args.client
    config = Kconfig(client=client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.create_openshift_iso(cluster, overrides=overrides, ignitionfile=ignitionfile, direct=direct)


def create_openshift_disconnecter(args):
    plan = args.plan
    if plan is None:
        plan = nameutils.get_random_name()
        pprint(f"Using {plan} as name of the plan")
    overrides = common.get_overrides(param=args.param)
    if 'cluster' not in overrides:
        overrides['cluster'] = plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.create_openshift_disconnecter(plan, overrides=overrides)


def create_vm(args):
    """Create vms"""
    name = args.name
    onlyassets = True if 'assets' in vars(args) else False
    image = args.image
    profile = args.profile
    count = args.count
    profilefile = args.profilefile
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    console = args.console
    serial = args.serial
    if args.wait:
        overrides['wait'] = args.wait
    if overrides.get('wait', False) and 'keys' not in overrides and common.get_ssh_pub_key() is None:
        error("No usable public key found, which is mandatory when using wait")
        sys.exit(1)
    customprofile = {}
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    for key in overrides:
        if key in vars(config) and vars(config)[key] is not None and type(overrides[key]) != type(vars(config)[key]):
            key_type = str(type(vars(config)[key]))
            error(f"The provided parameter {key} has a wrong type, it should be {key_type}")
            sys.exit(1)
    if 'name' in overrides:
        name = overrides['name']
    if name is None:
        name = nameutils.get_random_name()
        if config.type in ['gcp', 'kubevirt']:
            name = name.replace('_', '-')
        if config.type != 'aws' and not onlyassets:
            pprint(f"Using {name} as name of the vm")
    if image is not None:
        if image in config.profiles and not onlyassets:
            pprint(f"Using {image} as profile")
        profile = image
    elif profile is not None:
        if profile.endswith('.yml'):
            profilefile = profile
            profile = None
            if not os.path.exists(profilefile):
                error(f"Missing profile file {profilefile}")
                sys.exit(1)
            else:
                with open(profilefile, 'r') as entries:
                    entries = yaml.safe_load(entries)
                    entrieskeys = list(entries.keys())
                    if len(entrieskeys) == 1:
                        profile = entrieskeys[0]
                        customprofile = entries[profile]
                        pprint(f"Using data from {profilefile} as profile")
                    else:
                        error(f"Cant' parse {profilefile} as profile file")
                        sys.exit(1)
    elif overrides or onlyassets:
        profile = 'kvirt'
        config.profiles[profile] = {}
    else:
        error("You need to either provide a profile, an image or some parameters")
        sys.exit(1)
    if count == 1:
        result = config.create_vm(name, profile, overrides=overrides, customprofile=customprofile,
                                  onlyassets=onlyassets)
        if not onlyassets:
            if console:
                config.k.console(name=name, tunnel=config.tunnel)
            elif serial:
                config.k.serialconsole(name)
            else:
                code = common.handle_response(result, name, element='', action='created', client=config.client)
                return code
        elif 'reason' in result:
            error(result['reason'])
        else:
            print(result['data'])
    else:
        codes = []
        if 'plan' not in overrides:
            overrides['plan'] = name
        for number in range(count):
            currentname = "%s-%d" % (name, number)
            currentoverrides = deepcopy(overrides)
            if 'nets' in currentoverrides:
                for index, net in enumerate(currentoverrides['nets']):
                    if not isinstance(net, dict):
                        continue
                    if 'mac' in net:
                        suffix = hex(int(net['mac'][-2:]) + number)[2:].rjust(2, '0')
                        currentoverrides['nets'][index]['mac'] = f"{net['mac'][:-2]}{suffix}"
                    if 'ip' in net:
                        ip = str(ip_address(net['ip']) + number)
                        currentoverrides['nets'][index]['ip'] = ip
            result = config.create_vm(currentname, profile, overrides=currentoverrides, customprofile=customprofile,
                                      onlyassets=onlyassets)
            if not onlyassets:
                codes.append(common.handle_response(result, currentname, element='', action='created',
                                                    client=config.client))
        return max(codes)


def clone_vm(args):
    """Clone existing vm"""
    name = args.name
    base = args.base
    full = args.full
    start = args.start
    pprint(f"Cloning vm {name} from vm {base}...")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    result = k.clone(base, name, full=full, start=start)
    if result['result'] == 'success' and os.access(os.path.expanduser('~/.kcli'), os.W_OK):
        common.set_lastvm(name, config.client)


def update_vm(args):
    """Update ip, memory or numcpus"""
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    ip = overrides.get('ip')
    flavor = overrides.get('flavor')
    numcpus = overrides.get('numcpus')
    memory = overrides.get('memory')
    plan = overrides.get('plan')
    autostart = overrides.get('autostart')
    dns = overrides.get('dns')
    host = overrides.get('host')
    domain = overrides.get('domain')
    cloudinit = overrides.get('cloudinit')
    image = overrides.get('image')
    nets = overrides.get('nets')
    disks = overrides.get('disks')
    information = overrides.get('information')
    iso = overrides.get('iso')
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    extra_metadata = {k: overrides[k] for k in overrides if k not in config.list_keywords()}
    k = config.k
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    for name in names:
        if dns:
            pprint(f"Creating Dns entry for {name}...")
            networks = k.vm_ports(name)
            if networks and domain is None:
                domain = networks[0]
            if not nets:
                return
            else:
                k.reserve_dns(name=name, nets=networks, domain=domain, ip=ip)
        if ip is not None:
            pprint(f"Updating ip of vm {name} to {ip}...")
            k.update_metadata(name, 'ip', ip)
        if cloudinit:
            pprint(f"Removing cloudinit information of vm {name}")
            k.remove_cloudinit(name)
        if plan is not None:
            pprint(f"Updating plan of vm {name} to {plan}...")
            k.update_metadata(name, 'plan', plan)
        if image is not None:
            pprint(f"Updating image of vm {name} to {image}...")
            k.update_metadata(name, 'image', image)
        if memory is not None:
            pprint(f"Updating memory of vm {name} to {memory}...")
            k.update_memory(name, memory)
        if numcpus is not None:
            pprint(f"Updating numcpus of vm {name} to {numcpus}...")
            k.update_cpus(name, numcpus)
        if autostart is not None:
            pprint(f"Setting autostart to {autostart} for vm {name}...")
            k.update_start(name, start=autostart)
        if information:
            pprint(f"Setting information for vm {name}...")
            k.update_information(name, information)
        if iso is not None:
            pprint(f"Switching iso for vm {name} to {iso}...")
            if iso == 'None':
                iso = None
            k.update_iso(name, iso)
        if flavor is not None:
            pprint(f"Updating flavor of vm {name} to {flavor}...")
            k.update_flavor(name, flavor)
        if host:
            pprint(f"Creating Host entry for vm {name}...")
            networks = k.vm_ports(name)
            if networks:
                if domain is None:
                    domain = networks[0]
                k.reserve_host(name, networks, domain)
        currentvm = k.info(name)
        currentnets = currentvm.get('nets', [])
        currentdisks = currentvm.get('disks', [])
        if disks:
            pprint(f"Updating disks of vm {name}")
            if len(currentdisks) < len(disks):
                pprint(f"Adding Disks to {name}")
                for disk in disks[len(currentdisks):]:
                    if isinstance(disk, int):
                        size = disk
                        pool = config.pool
                    elif isinstance(disk, str) and disk.isdigit():
                        size = int(disk)
                        pool = config.pool
                    elif isinstance(disk, dict):
                        size = disk.get('size', config.disksize)
                        pool = disk.get('pool', config.pool)
                    else:
                        continue
                    k.add_disk(name=name, size=size, pool=pool)
            if len(currentdisks) > len(disks):
                pprint(f"Removing Disks of {name}")
                for disk in currentdisks[len(currentdisks) - len(disks):]:
                    diskname = os.path.basename(disk['path'])
                    diskpool = os.path.dirname(disk['path'])
                    k.delete_disk(name=name, diskname=diskname, pool=diskpool)
        if nets:
            pprint(f"Updating nets of vm {name}")
            if len(currentnets) < len(nets):
                pprint(f"Adding Nics to {name}")
                for net in nets[len(currentnets):]:
                    if isinstance(net, str):
                        network = net
                    elif isinstance(net, dict) and 'name' in net:
                        network = net['name']
                    else:
                        error(f"Skipping wrong nic spec for {name}")
                        continue
                    k.add_nic(name, network)
            if len(currentnets) > len(nets):
                pprint(f"Removing Nics of {name}")
                for net in range(len(currentnets), len(nets), -1):
                    interface = "eth%s" % (net - 1)
                    k.delete_nic(name, interface)
        if extra_metadata:
            for key in extra_metadata:
                k.update_metadata(name, key, extra_metadata[key])
        if overrides.get('files', []):
            newfiles = overrides['files']
            pprint(f"Remediating files of {name}")
            config.remediate_files(name, newfiles, overrides)


def create_vmdisk(args):
    """Add disk to vm"""
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    name = args.name
    novm = args.novm
    size = args.size
    image = args.image
    interface = args.interface
    if interface not in ['virtio', 'ide', 'scsi']:
        error("Incorrect disk interface. Choose between virtio, scsi or ide...")
        sys.exit(1)
    pool = args.pool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if size is None:
        error("Missing size. Leaving...")
        sys.exit(1)
    if pool is None:
        error("Missing pool. Leaving...")
        sys.exit(1)
    if novm:
        pprint(f"Creating disk {name}...")
    else:
        pprint(f"Adding disk to {name}...")
    k.add_disk(name=name, size=size, pool=pool, image=image, interface=interface, novm=novm, overrides=overrides)


def delete_vmdisk(args):
    """Delete disk of vm"""
    yes_top = args.yes_top
    yes = args.yes
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    name = args.vm
    diskname = args.diskname
    novm = args.novm
    pool = args.pool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Deleting disk {diskname}")
    k.delete_disk(name=name, diskname=diskname, pool=pool, novm=novm)
    return


def create_dns(args):
    """Create dns entries"""
    names = args.names
    net = args.net
    domain = args.domain
    ip = args.ip
    alias = args.alias
    if alias is None:
        alias = []
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    name = names[0]
    if len(names) > 1:
        alias.extend(names[1:])
    if alias:
        pprint("Creating alias entries for %s" % ' '.join(alias))
    k.reserve_dns(name=name, nets=[net], domain=domain, ip=ip, alias=alias, primary=True)


def delete_dns(args):
    """Delete dns entries"""
    names = args.names
    net = args.net
    allentries = args.all
    domain = args.domain if args.domain is not None else net
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    for name in names:
        pprint(f"Deleting Dns entry for {name}")
        k.delete_dns(name, domain, allentries=allentries)


def export_vm(args):
    """Export a vm"""
    image = args.image
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    names = [common.get_lastvm(config.client)] if not args.names else args.names
    k = config.k
    codes = []
    for name in names:
        result = k.export(name=name, image=image)
        if result['result'] == 'success':
            success(f"Vm {name} exported")
            codes.append(0)
        else:
            reason = result['reason']
            error(f"Could not export vm {name} because {reason}")
            codes.append(1)
    sys.exit(1 if 1 in codes else 0)


def create_lb(args):
    """Create loadbalancer"""
    checkpath = args.checkpath
    checkport = args.checkport
    ports = args.ports
    domain = args.domain
    internal = args.internal
    if args.vms is None:
        vms = []
    else:
        good_vms = args.vms[1:-1] if args.vms.startswith('[') and args.vms.endswith(']') else args.vms
        vms = [v.strip() for v in good_vms.split(',')]
    good_ports = args.ports[1:-1] if args.ports.startswith('[') and args.ports.endswith(']') else args.ports
    ports = [p.strip() for p in good_ports.split(',')]
    name = nameutils.get_random_name().replace('_', '-') if args.name is None else args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.create_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain, checkport=checkport,
                               internal=internal)
    return 0


def delete_lb(args):
    """Delete loadbalancer"""
    yes = args.yes
    yes_top = args.yes_top
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.delete_loadbalancer(args.name)
    return 0


def create_generic_kube(args):
    """Create Generic kube"""
    paramfile = args.paramfile
    force = args.force
    cluster = args.cluster
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if force:
        config.delete_kube(cluster, overrides=overrides)
    config.create_kube_generic(cluster, overrides=overrides)


def create_kind_kube(args):
    """Create K3s kube"""
    paramfile = args.paramfile
    force = args.force
    cluster = args.cluster if args.cluster is not None else 'testk'
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if force:
        config.delete_kube(cluster, overrides=overrides)
    config.create_kube_kind(cluster, overrides=overrides)


def create_k3s_kube(args):
    """Create K3s kube"""
    paramfile = args.paramfile
    force = args.force
    cluster = args.cluster if args.cluster is not None else 'testk'
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if force:
        config.delete_kube(cluster, overrides=overrides)
    config.create_kube_k3s(cluster, overrides=overrides)


def create_openshift_kube(args):
    """Create Openshift kube"""
    paramfile = args.paramfile
    force = args.force
    cluster = args.cluster
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    client = 'fake' if common.need_fake() else args.client
    config = Kconfig(client=client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if args.subcommand_create_kube == 'okd':
        overrides['upstream'] = True
    if force:
        config.delete_kube(cluster, overrides=overrides)
    config.create_kube_openshift(cluster, overrides=overrides)


def delete_kube(args):
    """Delete kube"""
    yes = args.yes
    yes_top = args.yes_top
    cluster = args.cluster if args.cluster is not None else 'testk'
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    config.delete_kube(cluster, overrides=overrides)


def scale_generic_kube(args):
    """Scale generic kube"""
    workers = args.workers
    paramfile = args.paramfile
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    cluster = overrides.get('cluster', args.cluster)
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if not os.path.exists(clusterdir):
        error(f"Cluster directory {clusterdir} not found...")
        sys.exit(1)
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if workers > 0:
        overrides['workers'] = workers
    config.scale_kube_generic(cluster, overrides=overrides)


def scale_k3s_kube(args):
    """Scale k3s kube"""
    workers = args.workers
    paramfile = args.paramfile
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    cluster = overrides.get('cluster', args.cluster)
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if not os.path.exists(clusterdir):
        error(f"Cluster directory {clusterdir} not found...")
        sys.exit(1)
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if workers > 0:
        overrides['workers'] = workers
    config.scale_kube_k3s(cluster, overrides=overrides)


def scale_openshift_kube(args):
    """Scale openshift kube"""
    workers = args.workers
    paramfile = args.paramfile
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    cluster = overrides.get('cluster', args.cluster)
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if not os.path.exists(clusterdir):
        error(f"Cluster directory {clusterdir} not found...")
        sys.exit(1)
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if workers > 0:
        overrides['workers'] = workers
    config.scale_kube_openshift(cluster, overrides=overrides)


def update_generic_kube(args):
    args.type = 'generic'
    update_kube(args)


def update_openshift_kube(args):
    args.type = 'openshift'
    update_kube(args)


def update_kind_kube(args):
    args.type = 'kind'
    update_kube(args)


def update_k3s_kube(args):
    args.type = 'k3s'
    update_kube(args)


def update_kube(args):
    """Update kube"""
    cluster = args.cluster
    _type = args.type
    data = {'kube': cluster, 'kubetype': _type}
    plan = None
    paramfile = args.paramfile
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if not overrides:
        warning("No parameters provided, using stored one")
    if 'ipi' in overrides and overrides['ipi']:
        error("Update cluster workflow not available when using ipi")
        sys.exit(1)
    clusterdir = os.path.expanduser("~/.kcli/clusters/%s" % cluster)
    if not os.path.exists(clusterdir):
        error("Cluster directory %s not found..." % clusterdir)
        sys.exit(1)
    if os.path.exists("%s/kcli_parameters.yml" % clusterdir):
        with open("%s/kcli_parameters.yml" % clusterdir, 'r') as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    data['basedir'] = '/workdir' if container_mode() else '.'
    if plan is None:
        plan = cluster
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.update_kube(plan, _type, overrides=data)


def create_vmnic(args):
    """Add nic to vm"""
    name = args.name
    network = args.network
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if network is None:
        error("Missing network. Leaving...")
        sys.exit(1)
    pprint(f"Adding nic to vm {name}...")
    k.add_nic(name=name, network=network)


def delete_vmnic(args):
    """Delete nic of vm"""
    name = args.name
    interface = args.interface
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Deleting nic from vm {name}...")
    k.delete_nic(name, interface)
    return


def create_pool(args):
    """Create/Delete pool"""
    pool = args.pool
    pooltype = args.pooltype
    path = args.path
    thinpool = args.thinpool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if path is None:
        error("Missing path. Leaving...")
        sys.exit(1)
    pprint(f"Creating pool {pool}...")
    k.create_pool(name=pool, poolpath=path, pooltype=pooltype, thinpool=thinpool)


def delete_pool(args):
    """Delete pool"""
    pool = args.pool
    full = args.full
    yes = args.yes
    yes_top = args.yes_top
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Deleting pool {pool}...")
    result = k.delete_pool(name=pool, full=full)
    common.handle_response(result, pool, element='Pool', action='deleted')


def create_plan(args):
    """Create plan"""
    plan = args.plan
    ansible = args.ansible
    url = args.url
    path = args.path
    container = args.container
    inputfile = args.inputfile
    force = args.force
    pre = not args.skippre
    post = not args.skippost
    paramfile = args.paramfile
    threaded = args.threaded
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if container_mode():
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    _type = config.ini[config.client].get('type', 'kvm')
    overrides.update({'type': _type})
    if force:
        if plan is None:
            error("Force requires specifying a plan name")
            return 1
        else:
            config.delete_plan(plan, unregister=config.rhnunregister)
    if plan is None:
        plan = nameutils.get_random_name()
        pprint(f"Using {plan} as name of the plan")
    result = config.plan(plan, ansible=ansible, url=url, path=path, container=container, inputfile=inputfile,
                         overrides=overrides, pre=pre, post=post, threaded=threaded)
    if 'result' in result and result['result'] == 'success':
        sys.exit(0)
    else:
        if 'reason' in result:
            error(result['reason'])
        sys.exit(1)


def create_playbook(args):
    """Create plan"""
    inputfile = args.inputfile
    store = args.store
    paramfile = args.paramfile
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if container_mode():
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    _type = baseconfig.ini[baseconfig.client].get('type', 'kvm')
    overrides.update({'type': _type})
    baseconfig.create_playbook(inputfile, overrides=overrides, store=store)
    return 0


def update_plan(args):
    """Update plan"""
    autostart = args.autostart
    noautostart = args.noautostart
    remediate = args.remediate
    plan = args.plan
    url = args.url
    path = args.path
    container = args.container
    inputfile = args.inputfile
    paramfile = args.paramfile
    if container_mode():
        inputfile = "/workdir/%s" % inputfile if inputfile is not None else "/workdir/kcli_plan.yml"
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if autostart:
        config.autostart_plan(plan)
        return 0
    elif noautostart:
        config.noautostart_plan(plan)
        return 0
    config.plan(plan, url=url, path=path, container=container, inputfile=inputfile, overrides=overrides, update=True,
                remediate=remediate)
    return 0


def delete_plan(args):
    """Delete plan"""
    plans = args.plans
    codes = []
    yes = args.yes
    yes_top = args.yes_top
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    for plan in plans:
        result = config.delete_plan(plan, unregister=config.rhnunregister)
        if 'result' in result and result['result'] == 'success':
            codes.append(0)
        else:
            codes.append(4)
    sys.exit(4 if 4 in codes else 0)


def expose_plan(args):
    plan = args.plan
    if plan is None:
        plan = nameutils.get_random_name()
        pprint(f"Using {plan} as name of the plan")
    port = args.port
    inputfile = args.inputfile
    installermode = args.installermode
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if container_mode():
        inputfile = "/workdir/%s" % inputfile
    overrides = common.get_overrides(param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    extraconfigs = {}
    for extraclient in config.extraclients:
        extraconfigs[extraclient] = Kconfig(client=extraclient, debug=args.debug, region=args.region, zone=args.zone,
                                            namespace=args.namespace)
    config.expose_plan(plan, inputfile=inputfile, overrides=overrides, port=port, extraconfigs=extraconfigs,
                       installermode=installermode)
    return 0


def start_plan(args):
    """Start plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.start_plan(plan)
    return 0


def stop_plan(args):
    """Stop plan"""
    plan = args.plan
    soft = args.soft
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.stop_plan(plan, soft=soft)
    return 0


def autostart_plan(args):
    """Autostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.autostart_plan(plan)
    return 0


def noautostart_plan(args):
    """Noautostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.noautostart_plan(plan)
    return 0


def restart_plan(args):
    """Restart plan"""
    soft = args.soft
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.stop_plan(plan, soft=soft)
    config.start_plan(plan)
    return 0


def info_generic_app(args):
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    baseconfig.info_app_generic(args.app)


def info_openshift_disconnecter(args):
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    baseconfig.info_openshift_disconnecter()


def info_openshift_app(args):
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    baseconfig.info_app_openshift(args.app)


def info_plan(args):
    """Info plan """
    doc = args.doc
    quiet = args.quiet
    url = args.url
    path = args.path
    inputfile = args.inputfile
    if container_mode():
        inputfile = "/workdir/%s" % inputfile if inputfile is not None else "/workdir/kcli_plan.yml"
    if url is None:
        baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
        baseconfig.info_plan(inputfile, quiet=quiet, doc=doc)
    else:
        config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
        config.plan('info', url=url, path=path, inputfile=inputfile, info=True, quiet=quiet, doc=doc)
    return 0


def info_generic_kube(args):
    """Info Generic kube"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    baseconfig.info_kube_generic(quiet=True)


def info_kind_kube(args):
    """Info Kind kube"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    baseconfig.info_kube_kind(quiet=True)


def info_k3s_kube(args):
    """Info K3s kube"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    baseconfig.info_kube_k3s(quiet=True)


def info_openshift_kube(args):
    """Info Openshift kube"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    baseconfig.info_kube_openshift(quiet=True)


def info_network(args):
    """Info network """
    name = args.name
    pprint(f"Providing information about network {name}...")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    networkinfo = config.k.info_network(name)
    if networkinfo:
        common.pretty_print(networkinfo)


def info_keyword(args):
    """Info keyword"""
    keyword = args.keyword
    pprint(f"Providing information about keyword {keyword}...")
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, offline=True)
    default = baseconfig.default
    keywords = baseconfig.list_keywords()
    if keyword not in keywords:
        error(f"Keyword {keyword} not found")
        return 1
    else:
        print("Default value: %s" % default[keyword])
        print("Current value: %s" % keywords[keyword])


def download_plan(args):
    """Download plan"""
    plan = args.plan
    url = args.url
    if plan is None:
        plan = nameutils.get_random_name()
        pprint(f"Using {plan} as name of the plan")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, url=url, download=True)
    return 0


def download_coreos_installer(args):
    """Download Coreos Installer"""
    paramfile = args.paramfile
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    common.get_coreos_installer(version=overrides.get('version', 'latest'), arch=overrides.get('arch'))


def download_kubectl(args):
    """Download Kubectl"""
    paramfile = args.paramfile
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    common.get_kubectl(version=overrides.get('version', 'latest'))


def download_helm(args):
    """Download Helm"""
    paramfile = args.paramfile
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    common.get_helm(version=overrides.get('version', 'latest'))


def download_oc(args):
    """Download Oc"""
    paramfile = args.paramfile
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    common.get_oc(version=overrides.get('version', 'latest'))


def download_openshift_installer(args):
    """Download Openshift Installer"""
    paramfile = args.paramfile
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    return baseconfig.download_openshift_installer(overrides)


def download_okd_installer(args):
    """Download Okd Installer"""
    paramfile = args.paramfile
    if container_mode():
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    overrides['upstream'] = True
    return baseconfig.download_openshift_installer(overrides)


def create_pipeline_github(args):
    """Create Github Pipeline"""
    plan = args.plan
    inputfile = args.inputfile
    kube = args.kube
    script = args.script
    paramfile = args.paramfile
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if container_mode():
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    overrides = common.get_overrides(param=args.param)
    renderfile = baseconfig.create_github_pipeline(plan, inputfile, paramfile=paramfile, overrides=overrides,
                                                   kube=kube, script=script)
    print(renderfile)
    return 0


def create_pipeline_jenkins(args):
    """Create Jenkins Pipeline"""
    plan = args.plan
    inputfile = args.inputfile
    kube = args.kube
    paramfile = args.paramfile
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if container_mode():
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if not kube and not os.path.exists(inputfile):
        error(f"File {inputfile} not found")
        return 0
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    renderfile = baseconfig.create_jenkins_pipeline(plan, inputfile, overrides=overrides, kube=kube)
    print(renderfile)
    return 0


def create_pipeline_tekton(args):
    """Create Tekton Pipeline"""
    inputfile = args.inputfile
    kube = args.kube
    paramfile = args.paramfile
    plan = args.plan
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if container_mode():
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    overrides = common.get_overrides(param=args.param)
    renderfile = baseconfig.create_tekton_pipeline(plan, inputfile, paramfile=paramfile, overrides=overrides, kube=kube)
    print(renderfile)
    return 0


def render_file(args):
    """Render file"""
    plan = None
    inputfile = args.inputfile
    paramfiles = args.paramfile if args.paramfile is not None else []
    ignore = args.ignore
    if container_mode():
        inputfile = "/workdir/%s" % inputfile if inputfile is not None else "/workdir/kcli_plan.yml"
        if paramfiles:
            paramfiles = ["/workdir/%s" % paramfile for paramfile in paramfiles]
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfiles = ["/workdir/kcli_parameters.yml"]
    elif not paramfiles and os.path.exists("kcli_parameters.yml"):
        paramfiles = ["kcli_parameters.yml"]
    overrides = {}
    allparamfiles = [paramfile for paramfile in glob("*_default.y*ml")]
    allparamfiles.extend(paramfiles)
    for paramfile in allparamfiles:
        overrides.update(common.get_overrides(paramfile=paramfile))
    overrides.update(common.get_overrides(param=args.param))
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    default_data = {'config_%s' % k: baseconfig.default[k] for k in baseconfig.default}
    client_data = {'config_%s' % k: baseconfig.ini[baseconfig.client][k] for k in baseconfig.ini[baseconfig.client]}
    client_data['config_type'] = client_data.get('config_type', 'kvm')
    client_data['config_host'] = client_data.get('config_host', '127.0.0.1')
    default_user = getuser() if client_data['config_type'] == 'kvm'\
        and client_data['config_host'] in ['localhost', '127.0.0.1'] else 'root'
    client_data['config_user'] = client_data.get('config_user', default_user)
    config_data = default_data.copy()
    config_data.update(client_data)
    overrides.update(config_data)
    if not os.path.exists(inputfile):
        error(f"File {inputfile} not found")
        return 0
    renderfile = baseconfig.process_inputfile(plan, inputfile, overrides=overrides, ignore=ignore)
    print(renderfile)
    return 0


def create_vmdata(args):
    """Create cloudinit/ignition data for vm"""
    args.assets = True
    args.profile = None
    args.profilefile = None
    args.wait = False
    args.console = None
    args.serial = None
    args.count = 1
    create_vm(args)
    return 0


def create_plandata(args):
    """Create cloudinit/ignition data"""
    plan = None
    inputfile = args.inputfile
    pre = not args.skippre
    outputdir = args.outputdir
    paramfile = args.paramfile
    if container_mode():
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                     namespace=args.namespace)
    config_data = {'config_%s' % k: config.ini[config.client][k] for k in config.ini[config.client]}
    config_data['config_type'] = config_data.get('config_type', 'kvm')
    overrides.update(config_data)
    if not os.path.exists(inputfile):
        error(f"File {inputfile} not found")
        return 0
    results = config.plan(plan, inputfile=inputfile, overrides=overrides, onlyassets=True, pre=pre)
    if results.get('assets'):
        for num, asset in enumerate(results['assets']):
            if outputdir is None:
                print(asset)
            else:
                if not os.path.exists(outputdir):
                    os.mkdir(outputdir)
                # if 'ignition' in asset:
                #    with open("%s/%s.ign" % (outputdir, "%0.2d" % num), 'w') as f:
                #        f.write(asset)
                assetdata = yaml.safe_load(asset)
                hostname = assetdata.get('hostname')
                if hostname is None:
                    continue
                pprint("Rendering %s" % hostname)
                hostnamedir = "%s/%s" % (outputdir, hostname)
                if not os.path.exists(hostnamedir):
                    os.mkdir(hostnamedir)
                runcmd = assetdata.get('runcmd', [])
                write_files = assetdata.get('write_files', [])
                with open("%s/runcmd" % hostnamedir, 'w') as f:
                    f.write('\n'.join(runcmd))
                for _file in write_files:
                    content = _file['content']
                    path = _file['path'].replace('/root/', '')
                    SSH_PRIV_LOCATIONS = [location.replace('.pub', '') for location in SSH_PUB_LOCATIONS]
                    if 'openshift_pull.json' in path or path in SSH_PRIV_LOCATIONS or path in SSH_PUB_LOCATIONS:
                        warning("Skipping %s" % path)
                        continue
                    if '/' in path and not os.path.exists("%s/%s" % (hostnamedir, os.path.dirname(path))):
                        os.makedirs("%s/%s" % (hostnamedir, os.path.dirname(path)))
                        with open("%s/%s/%s" % (hostnamedir, os.path.dirname(path), os.path.basename(path)), 'w') as f:
                            f.write(content)
                    else:
                        with open("%s/%s" % (hostnamedir, path), 'w') as f:
                            f.write(content)
        if outputdir is not None:
            renderplan = config.process_inputfile(plan, inputfile, overrides=overrides)
            with open("%s/kcli_plan.yml" % outputdir, 'w') as f:
                f.write(renderplan)
    return 0


def create_plantemplate(args):
    """Create plan template"""
    skipfiles = args.skipfiles
    skipscripts = args.skipscripts
    directory = args.directory
    paramfile = args.paramfile
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    baseconfig.create_plan_template(directory, overrides=overrides, skipfiles=skipfiles, skipscripts=skipscripts)


def create_snapshot_plan(args):
    """Snapshot plan"""
    plan = args.plan
    snapshot = args.snapshot
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.snapshot_plan(plan, snapshotname=snapshot)
    return 0


def delete_snapshot_plan(args):
    """Snapshot plan"""
    plan = args.plan
    snapshot = args.snapshot
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    for vm in sorted(k.list(), key=lambda x: x['name']):
        name = vm['name']
        if vm['plan'] == plan:
            pprint(f"Deleting snapshot {snapshot} of vm {name}...")
            k.snapshot(snapshot, name, delete=True)
    return 0


def revert_snapshot_plan(args):
    """Revert snapshot of plan"""
    plan = args.plan
    snapshot = args.snapshot
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.revert_plan(plan, snapshotname=snapshot)
    return 0


def create_repo(args):
    """Create repo"""
    repo = args.repo
    url = args.url
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if repo is None:
        error("Missing repo. Leaving...")
        sys.exit(1)
    if url is None:
        error("Missing url. Leaving...")
        sys.exit(1)
    pprint(f"Adding repo {repo}...")
    baseconfig.create_repo(repo, url)
    return 0


def delete_repo(args):
    """Delete repo"""
    repo = args.repo
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if repo is None:
        error("Missing repo. Leaving...")
        sys.exit(1)
    pprint(f"Deleting repo {repo}...")
    baseconfig.delete_repo(repo)
    return


def update_repo(args):
    """Update repo"""
    repo = args.repo
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    if repo is None:
        pprint("Updating all repos...")
        repos = baseconfig.list_repos()
        for repo in repos:
            pprint(f"Updating repo {repo}...")
            baseconfig.update_repo(repo)
    else:
        pprint(f"Updating repo {repo}...")
        baseconfig.update_repo(repo)
    return


def info_product(args):
    """Info product"""
    repo = args.repo
    product = args.product
    group = args.group
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    pprint(f"Providing information on product {product}...")
    baseconfig.info_product(product, repo, group)


def create_product(args):
    """Create product"""
    repo = args.repo
    product = args.product
    latest = args.latest
    group = args.group
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    plan = overrides['plan'] if 'plan' in overrides else None
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    pprint(f"Creating product {product}...")
    config.create_product(product, repo=repo, group=group, plan=plan, latest=latest, overrides=overrides)
    return 0


def ssh_vm(args):
    """Ssh into vm"""
    local = args.L
    remote = args.R
    D = args.D
    X = args.X
    Y = args.Y
    identityfile = args.identityfile
    user = args.user
    vmport = args.port
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    name = [common.get_lastvm(baseconfig.client)] if not args.name else args.name
    tunnel = baseconfig.tunnel
    tunnelhost = baseconfig.tunnelhost
    tunneluser = baseconfig.tunneluser
    tunnelport = baseconfig.tunnelport
    if tunnel and tunnelhost is None and baseconfig.type != 'kubevirt':
        error("Tunnel requested but no tunnelhost defined")
        sys.exit(1)
    insecure = baseconfig.insecure
    if len(name) > 1:
        cmd = ' '.join(name[1:])
    else:
        cmd = None
    name = name[0]
    if '@' in name and len(name.split('@')) == 2:
        user = name.split('@')[0]
        name = name.split('@')[1]
    if os.path.exists("/i_am_a_container") and not os.path.exists("/root/.kcli/config.yml")\
            and not os.path.exists("/root/.ssh/config"):
        insecure = True
    sshcommand = None
    if baseconfig.cache:
        _list = cache_vms(baseconfig, args.region, args.zone, args.namespace)
        vms = [vm for vm in _list if vm['name'] == name]
        if vms:
            vm = vms[0]
            ip = vm.get('ip')
            if ip is None:
                error(f"No ip found in cache for {name}...")
            else:
                if user is None:
                    user = baseconfig.vmuser if baseconfig.vmuser is not None else vm.get('user')
                if vmport is None:
                    vmport = baseconfig.vmport if baseconfig.vmport is not None else vm.get('vmport')
                sshcommand = common.ssh(name, ip=ip, user=user, local=local, remote=remote, tunnel=tunnel,
                                        tunnelhost=tunnelhost, tunnelport=tunnelport, tunneluser=tunneluser,
                                        insecure=insecure, cmd=cmd, X=X, Y=Y, D=D, debug=args.debug, vmport=vmport,
                                        identityfile=identityfile)
    if sshcommand is None:
        config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
        k = config.k
        u, ip, vmport = common._ssh_credentials(k, name)
        if tunnel and tunnelhost is None and config.type == 'kubevirt':
            info = k.info(name, debug=False)
            tunnelhost = k.node_host(name=info.get('host'))
            if tunnelhost is None:
                error(f"No valid node ip found for {name}")
        if ip is None:
            return
        if user is None:
            user = config.vmuser if config.vmuser is not None else u
        if vmport is None and config.vmport is not None:
            vmport = config.vmport
        if config.type in ['kvm', 'packet'] and '.' not in ip and ':' not in ip:
            vmport = ip
            ip = config.host
        sshcommand = common.ssh(name, ip=ip, user=user, local=local, remote=remote, tunnel=tunnel,
                                tunnelhost=tunnelhost, tunnelport=tunnelport, tunneluser=tunneluser,
                                insecure=insecure, cmd=cmd, X=X, Y=Y, D=D, debug=args.debug, vmport=vmport,
                                identityfile=identityfile)
    if sshcommand is not None:
        if find_executable('ssh') is not None:
            os.system(sshcommand)
        else:
            print(sshcommand)
    else:
        error(f"Couldnt ssh to {name}")


def scp_vm(args):
    """Scp into vm"""
    identityfile = args.identityfile
    recursive = args.recursive
    source = args.source[0]
    source = "/workdir/%s" % source if container_mode() else source
    destination = args.destination[0]
    user = args.user
    vmport = args.port
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    tunnel = baseconfig.tunnel
    tunnelhost = baseconfig.tunnelhost
    tunneluser = baseconfig.tunneluser
    tunnelport = baseconfig.tunnelport
    if tunnel and tunnelhost is None:
        error("Tunnel requested but no tunnelhost defined")
        sys.exit(1)
    insecure = baseconfig.insecure
    if len(source.split(':')) == 2:
        name, source = source.split(':')
        download = True
    elif len(destination.split(':')) == 2:
        name, destination = destination.split(':')
        download = False
    else:
        error("Couldn't run scp")
        return
    if '@' in name and len(name.split('@')) == 2:
        user, name = name.split('@')
    if download:
        pprint(f"Retrieving file {source} from {name}")
    else:
        pprint(f"Copying file {source} to {name}")
    scpcommand = None
    if baseconfig.cache:
        _list = cache_vms(baseconfig, args.region, args.zone, args.namespace)
        vms = [vm for vm in _list if vm['name'] == name]
        if vms:
            vm = vms[0]
            ip = vm.get('ip')
            if ip is None:
                error(f"No ip found in cache for {name}...")
            else:
                if user is None:
                    user = baseconfig.vmuser if baseconfig.vmuser is not None else vm.get('user')
                if vmport is None:
                    vmport = baseconfig.vmport if baseconfig.vmport is not None else vm.get('vmport')
                scpcommand = common.scp(name, ip=ip, user=user, source=source, destination=destination,
                                        recursive=recursive, tunnel=tunnel, tunnelhost=tunnelhost,
                                        tunnelport=tunnelport, tunneluser=tunneluser, debug=args.debug,
                                        download=download, vmport=vmport, insecure=insecure, identityfile=identityfile)
    if scpcommand is None:
        config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
        k = config.k
        u, ip, vmport = common._ssh_credentials(k, name)
        if ip is None:
            return
        if user is None:
            user = config.vmuser if config.vmuser is not None else u
        if vmport is None and config.vmport is not None:
            vmport = config.vmport
        if config.type in ['kvm', 'packet'] and '.' not in ip and ':' not in ip:
            vmport = ip
            ip = '127.0.0.1'
        scpcommand = common.scp(name, ip=ip, user=user, source=source, destination=destination, recursive=recursive,
                                tunnel=tunnel, tunnelhost=tunnelhost, tunnelport=tunnelport, tunneluser=tunneluser,
                                debug=config.debug, download=download, vmport=vmport, insecure=insecure,
                                identityfile=identityfile)
    if scpcommand is not None:
        if find_executable('scp') is not None:
            os.system(scpcommand)
        else:
            print(scpcommand)
    else:
        error("Couldn't run scp")


def create_network(args):
    """Create Network"""
    name = args.name
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    isolated = args.isolated
    cidr = args.cidr
    nodhcp = args.nodhcp
    domain = args.domain
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if name is None:
        error("Missing Network")
        sys.exit(1)
    if isolated:
        nat = False
    else:
        nat = True
    dhcp = not nodhcp
    if args.dual is not None:
        overrides['dual_cidr'] = args.dual
    result = k.create_network(name=name, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, overrides=overrides)
    common.handle_response(result, name, element='Network')


def delete_network(args):
    """Delete Network"""
    yes = args.yes
    yes_top = args.yes_top
    names = args.names
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    for name in names:
        result = k.delete_network(name=name)
        common.handle_response(result, name, element='Network', action='deleted')


def create_host_group(args):
    """Generate Host group"""
    data = {}
    data['_type'] = 'group'
    data['name'] = args.name
    data['algorithm'] = args.algorithm
    data['members'] = args.members
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_kvm(args):
    """Generate Kvm Host"""
    data = {}
    data['_type'] = 'kvm'
    data['name'] = args.name
    data['host'] = args.host
    data['port'] = args.port
    data['user'] = args.user
    data['protocol'] = args.protocol
    data['url'] = args.url
    data['pool'] = args.pool
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_ovirt(args):
    """Create Ovirt Host"""
    data = {}
    data['name'] = args.name
    data['_type'] = 'ovirt'
    data['host'] = args.host
    data['datacenter'] = args.datacenter
    data['ca_file'] = args.ca
    data['cluster'] = args.cluster
    data['org'] = args.org
    data['user'] = args.user
    data['password'] = args.password
    if args.pool is not None:
        data['pool'] = args.pool
    data['client'] = args.client
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_gcp(args):
    """Create Gcp Host"""
    data = {}
    data['name'] = args.name
    data['credentials'] = args.credentials
    data['project'] = args.project
    data['zone'] = args.zone
    data['_type'] = 'gcp'
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_aws(args):
    """Create Aws Host"""
    data = {}
    data['name'] = args.name
    data['_type'] = 'aws'
    data['access_key_id'] = args.access_key_id
    data['access_key_secret'] = args.access_key_secret
    data['region'] = args.region
    data['keypair'] = args.keypair
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_ibm(args):
    """"Create IBM Cloud host"""
    data = {}
    data['name'] = args.name
    data['_type'] = 'ibm'
    data['iam_api_key'] = args.iam_api_key
    data['region'] = args.region
    data['vpc'] = args.vpc
    data['zone'] = args.zone
    data['access_key_id'] = args.access_key_id
    data['secret_access_key'] = args.access_key_secret
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_openstack(args):
    """Create Openstack Host"""
    data = {}
    data['name'] = args.name
    data['_type'] = 'openstack'
    data['user'] = args.user
    data['password'] = args.password
    data['project'] = args.project
    data['domain'] = args.domain
    data['auth_url'] = args.auth_url
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_kubevirt(args):
    """Create Kubevirt Host"""
    data = {}
    data['name'] = args.name
    data['_type'] = 'kubevirt'
    if args.pool is not None:
        data['pool'] = args.pool
    if args.token is not None:
        data['token'] = args.token
    if args.ca is not None:
        data['ca_file'] = args.ca
    data['multus'] = args.multus
    data['cdi'] = args.cdi
    if args.host is not None:
        data['host'] = args.host
    if args.port is not None:
        data['port'] = args.port
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_host_vsphere(args):
    """Create Vsphere Host"""
    data = {}
    data['name'] = args.name
    data['_type'] = 'vsphere'
    data['host'] = args.host
    data['user'] = args.user
    data['password'] = args.password
    data['datacenter'] = args.datacenter
    data['cluster'] = args.cluster
    if args.pool is not None:
        data['pool'] = args.pool
    common.create_host(data)
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug, quiet=True)
    if len(baseconfig.clients) == 1:
        baseconfig.set_defaults()


def create_container(args):
    """Create container"""
    name = args.name
    image = args.image
    profile = args.profile
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    containerprofiles = {k: v for k, v in config.profiles.items() if 'type' in v and v['type'] == 'container'}
    if name is None:
        name = nameutils.get_random_name()
        if config.type == 'kubevirt':
            name = name.replace('_', '-')
    if image is not None:
        profile = image
        if image in containerprofiles:
            pprint(f"Using {image} as a profile")
        else:
            containerprofiles[image] = {'image': image}
    pprint(f"Deploying container {name} from profile {profile}...")
    profile = containerprofiles[profile]
    image = next((e for e in [profile.get('image'), profile.get('image')] if e is not None), None)
    if image is None:
        error(f"Missing image in profile {profile}. Leaving...")
        sys.exit(1)
    cmd = profile.get('cmd')
    ports = profile.get('ports')
    environment = profile.get('environment')
    volumes = next((e for e in [profile.get('volumes'), profile.get('disks')] if e is not None), None)
    profile.update(overrides)
    params = {'name': name, 'image': image, 'ports': ports, 'volumes': volumes, 'environment': environment,
              'overrides': overrides}
    if cmd is not None:
        params['cmds'] = [cmd]
    cont.create_container(**params)
    success(f"container {name} created")
    return


def snapshotcreate_vm(args):
    """Create snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Creating snapshot of {name} named {snapshot}...")
    result = k.snapshot(snapshot, name)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def snapshotdelete_vm(args):
    """Delete snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Deleting snapshot {snapshot} of vm {name}...")
    result = k.snapshot(snapshot, name, delete=True)
    code = common.handle_response(result, name, element='', action='snapshot deleted')
    return code


def snapshotrevert_vm(args):
    """Revert snapshot of vm"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Reverting snapshot {snapshot} of vm {name}...")
    result = k.snapshot(snapshot, name, revert=True)
    code = common.handle_response(result, name, element='', action='snapshot reverted')
    return code


def snapshotlist_vm(args):
    """List snapshots of vm"""
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Listing snapshots of {name}...")
    snapshots = k.snapshot('', name, listing=True)
    if isinstance(snapshots, dict):
        error(f"Vm {name} not found")
        return
    else:
        for snapshot in snapshots:
            print(snapshot)
    return


def create_bucket(args):
    """Create bucket"""
    buckets = args.buckets
    public = args.public
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    for bucket in buckets:
        pprint(f"Creating bucket {bucket}...")
        k.create_bucket(bucket, public=public)


def delete_bucket(args):
    """Delete bucket"""
    yes_top = args.yes_top
    yes = args.yes
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    buckets = args.buckets
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    for bucket in buckets:
        pprint(f"Deleting bucket {bucket}...")
        k.delete_bucket(bucket)


def list_bucket(args):
    """List buckets"""
    pprint("Listing buckets...")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    buckets = k.list_buckets()
    bucketstable = PrettyTable(["Bucket"])
    for bucket in sorted(buckets):
        bucketstable.add_row([bucket])
    bucketstable.align["Bucket"] = "l"
    print(bucketstable)


def list_bucketfiles(args):
    """List bucket files"""
    bucket = args.bucket
    pprint(f"Listing bucket files of bucket {bucket}...")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    bucketfiles = k.list_bucketfiles(bucket)
    bucketfilestable = PrettyTable(["BucketFiles"])
    for bucketfile in sorted(bucketfiles):
        bucketfilestable.add_row([bucketfile])
    bucketfilestable.align["BucketFiles"] = "l"
    print(bucketfilestable)


def create_bucketfile(args):
    bucket = args.bucket
    temp_url = args.temp
    public = args.public
    path = args.path
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Uploading file {path} to bucket {bucket}...")
    result = k.upload_to_bucket(bucket, path, temp_url=temp_url, public=public)
    if result is not None:
        pprint(f"bucketfile available at the following url:\n\n{result}")


def delete_bucketfile(args):
    bucket = args.bucket
    path = args.path
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Deleting file {path} to bucket {bucket}...")
    k.delete_from_bucket(bucket, path)


def download_bucketfile(args):
    bucket = args.bucket
    path = args.path
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pprint(f"Downloading file {path} from bucket {bucket}...")
    k.download_from_bucket(bucket, path)


def report_host(args):
    """Report info about host"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    k.report()


def switch_host(args):
    """Handle host"""
    host = args.name
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    result = baseconfig.switch_host(host)
    if result['result'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


def list_keyword(args):
    """List keywords"""
    baseconfig = Kbaseconfig(client=args.client, debug=args.debug)
    default = baseconfig.default
    keywordstable = PrettyTable(["Keyword", "Default Value", "Current Value"])
    keywordstable.align["Client"] = "l"
    keywords = baseconfig.list_keywords()
    for keyword in sorted(keywords):
        value = keywords[keyword]
        default_value = default[keyword]
        keywordstable.add_row([keyword, default_value, value])
    print(keywordstable)
    return


def cli():
    """

    """
    PARAMETERS_HELP = 'specify parameter or keyword for rendering (multiple can be specified)'
    parser = argparse.ArgumentParser(description='Libvirt/Ovirt/Vsphere/Gcp/Aws/Openstack/Kubevirt Wrapper/Ibm Cloud')
    parser.add_argument('-C', '--client')
    parser.add_argument('--containerclient', help='Containerclient to use')
    parser.add_argument('--dnsclient', help='Dnsclient to use')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-n', '--namespace', help='Namespace to use. specific to kubevirt')
    parser.add_argument('-r', '--region', help='Region to use. specific to aws/gcp/ibm')
    parser.add_argument('-z', '--zone', help='Zone to use. specific to gcp/ibm')

    subparsers = parser.add_subparsers(metavar='', title='Available Commands')

    containerconsole_desc = 'Attach To Container'
    containerconsole_parser = subparsers.add_parser('attach', description=containerconsole_desc,
                                                    help=containerconsole_desc)
    containerconsole_parser.add_argument('name', metavar='CONTAINERNAME', nargs='?')
    containerconsole_parser.set_defaults(func=console_container)

    create_desc = 'Create Object'
    create_parser = subparsers.add_parser('create', description=create_desc, help=create_desc, aliases=['add'])
    create_subparsers = create_parser.add_subparsers(metavar='', dest='subcommand_create')

    vmclone_desc = 'Clone Vm'
    vmclone_epilog = None
    vmclone_parser = subparsers.add_parser('clone', description=vmclone_desc, help=vmclone_desc, epilog=vmclone_epilog,
                                           formatter_class=rawhelp)
    vmclone_parser.add_argument('-b', '--base', help='Base VM', metavar='BASE')
    vmclone_parser.add_argument('-f', '--full', action='store_true', help='Full Clone')
    vmclone_parser.add_argument('-s', '--start', action='store_true', help='Start cloned VM')
    vmclone_parser.add_argument('name', metavar='VMNAME')
    vmclone_parser.set_defaults(func=clone_vm)

    vmconsole_desc = 'Vm Console (vnc/spice/serial)'
    vmconsole_epilog = "examples:\n%s" % vmconsole
    vmconsole_parser = argparse.ArgumentParser(add_help=False)
    vmconsole_parser.add_argument('-s', '--serial', action='store_true')
    vmconsole_parser.add_argument('name', metavar='VMNAME', nargs='?')
    vmconsole_parser.set_defaults(func=console_vm)
    subparsers.add_parser('console', parents=[vmconsole_parser], description=vmconsole_desc, help=vmconsole_desc,
                          epilog=vmconsole_epilog, formatter_class=rawhelp)

    delete_desc = 'Delete Object'
    delete_parser = subparsers.add_parser('delete', description=delete_desc, help=delete_desc, aliases=['remove'])
    delete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation', dest="yes_top")
    delete_subparsers = delete_parser.add_subparsers(metavar='', dest='subcommand_delete')

    disable_desc = 'Disable Host'
    disable_parser = subparsers.add_parser('disable', description=disable_desc, help=disable_desc)
    disable_subparsers = disable_parser.add_subparsers(metavar='', dest='subcommand_disable')

    download_desc = 'Download Assets like Image, plans or binaries'
    download_parser = subparsers.add_parser('download', description=download_desc, help=download_desc)
    download_subparsers = download_parser.add_subparsers(metavar='', dest='subcommand_download')

    enable_desc = 'Enable Host'
    enable_parser = subparsers.add_parser('enable', description=enable_desc, help=enable_desc)
    enable_subparsers = enable_parser.add_subparsers(metavar='', dest='subcommand_enable')

    vmexport_desc = 'Export Vm'
    vmexport_epilog = "examples:\n%s" % vmexport
    vmexport_parser = subparsers.add_parser('export', description=vmexport_desc, help=vmexport_desc,
                                            epilog=vmexport_epilog,
                                            formatter_class=rawhelp)
    vmexport_parser.add_argument('-i', '--image', help='Name for the generated image. Uses the vm name otherwise',
                                 metavar='IMAGE')
    vmexport_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmexport_parser.set_defaults(func=export_vm)

    expose_desc = 'Expose Object'
    expose_parser = subparsers.add_parser('expose', description=expose_desc, help=expose_desc)
    expose_subparsers = expose_parser.add_subparsers(metavar='', dest='subcommand_expose')

    hostlist_desc = 'List Hosts'

    info_desc = 'Info Host/Kube/Plan/Vm'
    info_parser = subparsers.add_parser('info', description=info_desc, help=info_desc, aliases=['show'])
    info_subparsers = info_parser.add_subparsers(metavar='', dest='subcommand_info')

    list_desc = 'List Object'
    list_epilog = "examples:\n%s" % _list
    list_parser = subparsers.add_parser('list', description=list_desc, help=list_desc, aliases=['get'],
                                        epilog=list_epilog,
                                        formatter_class=rawhelp)
    list_subparsers = list_parser.add_subparsers(metavar='', dest='subcommand_list')

    render_desc = 'Render file'
    render_parser = subparsers.add_parser('render', description=render_desc, help=render_desc)
    render_parser.add_argument('-f', '--inputfile', help='Input Plan/File', default='kcli_plan.yml')
    render_parser.add_argument('-i', '--ignore', action='store_true', help='Ignore missing variables')
    render_parser.add_argument('-P', '--param', action='append',
                               help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    render_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE', action='append')
    render_parser.set_defaults(func=render_file)

    restart_desc = 'Restart Vm/Plan/Container'
    restart_parser = subparsers.add_parser('restart', description=restart_desc, help=restart_desc)
    restart_subparsers = restart_parser.add_subparsers(metavar='', dest='subcommand_restart')

    revert_desc = 'Revert Vm/Plan Snapshot'
    revert_parser = subparsers.add_parser('revert', description=revert_desc, help=revert_desc)
    revert_subparsers = revert_parser.add_subparsers(metavar='', dest='subcommand_revert')

    scale_desc = 'Scale Kube'
    scale_parser = subparsers.add_parser('scale', description=scale_desc, help=scale_desc)
    scale_subparsers = scale_parser.add_subparsers(metavar='', dest='subcommand_scale')

    vmscp_desc = 'Scp Into Vm'
    vmscp_epilog = None
    vmscp_parser = argparse.ArgumentParser(add_help=False)
    vmscp_parser.add_argument('-i', '--identityfile', help='Identity file')
    vmscp_parser.add_argument('-r', '--recursive', help='Recursive', action='store_true')
    vmscp_parser.add_argument('-u', '-l', '--user', help='User for ssh')
    vmscp_parser.add_argument('-p', '-P', '--port', help='Port for ssh')
    vmscp_parser.add_argument('source', nargs=1)
    vmscp_parser.add_argument('destination', nargs=1)
    vmscp_parser.set_defaults(func=scp_vm)
    subparsers.add_parser('scp', parents=[vmscp_parser], description=vmscp_desc, help=vmscp_desc, epilog=vmscp_epilog,
                          formatter_class=rawhelp)

    vmssh_desc = 'Ssh Into Vm'
    vmssh_epilog = None
    vmssh_parser = argparse.ArgumentParser(add_help=False)
    vmssh_parser.add_argument('-D', help='Dynamic Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-L', help='Local Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-R', help='Remote Forwarding', metavar='REMOTE')
    vmssh_parser.add_argument('-X', action='store_true', help='Enable X11 Forwarding')
    vmssh_parser.add_argument('-Y', action='store_true', help='Enable X11 Forwarding(Insecure)')
    vmssh_parser.add_argument('-i', '--identityfile', help='Identity file')
    vmssh_parser.add_argument('-p', '--port', '--port', help='Port for ssh')
    vmssh_parser.add_argument('-u', '-l', '--user', help='User for ssh')
    vmssh_parser.add_argument('name', metavar='VMNAME', nargs='*')
    vmssh_parser.set_defaults(func=ssh_vm)
    subparsers.add_parser('ssh', parents=[vmssh_parser], description=vmssh_desc, help=vmssh_desc, epilog=vmssh_epilog,
                          formatter_class=rawhelp)

    start_desc = 'Start Vm/Plan/Container'
    start_epilog = "examples:\n%s" % start
    start_parser = subparsers.add_parser('start', description=start_desc, help=start_desc, epilog=start_epilog,
                                         formatter_class=rawhelp)
    start_subparsers = start_parser.add_subparsers(metavar='', dest='subcommand_start')

    stop_desc = 'Stop Vm/Plan/Container'
    stop_parser = subparsers.add_parser('stop', description=stop_desc, help=stop_desc)
    stop_subparsers = stop_parser.add_subparsers(metavar='', dest='subcommand_stop')

    switch_desc = 'Switch Host'
    switch_parser = subparsers.add_parser('switch', description=switch_desc, help=switch_desc)
    switch_subparsers = switch_parser.add_subparsers(metavar='', dest='subcommand_switch')

    sync_desc = 'Sync Host'
    sync_parser = subparsers.add_parser('sync', description=sync_desc, help=sync_desc)
    sync_subparsers = sync_parser.add_subparsers(metavar='', dest='subcommand_sync')

    update_desc = 'Update Vm/Plan/Repo'
    update_parser = subparsers.add_parser('update', description=update_desc, help=update_desc)
    update_subparsers = update_parser.add_subparsers(metavar='', dest='subcommand_update')

    version_desc = 'Version'
    version_epilog = None
    version_parser = argparse.ArgumentParser(add_help=False)
    version_parser.set_defaults(func=get_version)
    subparsers.add_parser('version', parents=[version_parser], description=version_desc, help=version_desc,
                          epilog=version_epilog, formatter_class=rawhelp)

    # sub subcommands
    createapp_desc = 'Create Kube Apps'
    createapp_parser = create_subparsers.add_parser('app', description=createapp_desc,
                                                    help=createapp_desc, aliases=['apps'])
    createapp_subparsers = createapp_parser.add_subparsers(metavar='', dest='subcommand_create_app')

    appgenericcreate_desc = 'Create Kube App Generic'
    appgenericcreate_epilog = None
    appgenericcreate_parser = createapp_subparsers.add_parser('generic', description=appgenericcreate_desc,
                                                              help=appgenericcreate_desc,
                                                              epilog=appgenericcreate_epilog, formatter_class=rawhelp)
    appgenericcreate_parser.add_argument('--outputdir', '-o', help='Output directory', metavar='OUTPUTDIR')
    appgenericcreate_parser.add_argument('-P', '--param', action='append',
                                         help='specify parameter or keyword for rendering (multiple can be specified)',
                                         metavar='PARAM')
    appgenericcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    appgenericcreate_parser.add_argument('apps', metavar='APPS', nargs='*')
    appgenericcreate_parser.set_defaults(func=create_app_generic)

    appopenshiftcreate_desc = 'Create Kube App Openshift'
    appopenshiftcreate_epilog = "examples:\n%s" % appopenshiftcreate
    appopenshiftcreate_parser = createapp_subparsers.add_parser('openshift', description=appopenshiftcreate_desc,
                                                                help=appopenshiftcreate_desc,
                                                                epilog=appopenshiftcreate_epilog,
                                                                formatter_class=rawhelp)
    appopenshiftcreate_parser.add_argument('--outputdir', '-o', help='Output directory', metavar='OUTPUTDIR')
    appopenshiftcreate_parser.add_argument('-P', '--param', action='append',
                                           help=PARAMETERS_HELP, metavar='PARAM')
    appopenshiftcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    appopenshiftcreate_parser.add_argument('apps', metavar='APPS', nargs='*')
    appopenshiftcreate_parser.set_defaults(func=create_app_openshift)

    deleteapp_desc = 'Delete Kube App'
    deleteapp_parser = delete_subparsers.add_parser('app', description=deleteapp_desc,
                                                    help=deleteapp_desc, aliases=['apps'])
    deleteapp_subparsers = deleteapp_parser.add_subparsers(metavar='', dest='subcommand_delete_app')

    appgenericdelete_desc = 'Delete Kube App Generic'
    appgenericdelete_epilog = None
    appgenericdelete_parser = deleteapp_subparsers.add_parser('generic', description=appgenericdelete_desc,
                                                              help=appgenericdelete_desc,
                                                              epilog=appgenericdelete_epilog, formatter_class=rawhelp)
    appgenericdelete_parser.add_argument('-P', '--param', action='append',
                                         help=PARAMETERS_HELP,
                                         metavar='PARAM')
    appgenericdelete_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    appgenericdelete_parser.add_argument('apps', metavar='APPS', nargs='*')
    appgenericdelete_parser.set_defaults(func=delete_app_generic)

    appopenshiftdelete_desc = 'Delete Kube App Openshift'
    appopenshiftdelete_epilog = None
    appopenshiftdelete_parser = deleteapp_subparsers.add_parser('openshift', description=appopenshiftdelete_desc,
                                                                help=appopenshiftdelete_desc,
                                                                epilog=appopenshiftdelete_epilog,
                                                                formatter_class=rawhelp)
    appopenshiftdelete_parser.add_argument('-P', '--param', action='append',
                                           help=PARAMETERS_HELP,
                                           metavar='PARAM')
    appopenshiftdelete_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    appopenshiftdelete_parser.add_argument('apps', metavar='APPS', nargs='*')
    appopenshiftdelete_parser.set_defaults(func=delete_app_openshift)

    appinfo_desc = 'Info App'
    appinfo_parser = info_subparsers.add_parser('app', description=appinfo_desc, help=appinfo_desc)
    appinfo_subparsers = appinfo_parser.add_subparsers(metavar='', dest='subcommand_info_app')

    appgenericinfo_desc = 'Info Generic App'
    appgenericinfo_parser = appinfo_subparsers.add_parser('generic', description=appgenericinfo_desc,
                                                          help=appgenericinfo_desc)

    appgenericinfo_parser.add_argument('app', metavar='APP')
    appgenericinfo_parser.set_defaults(func=info_generic_app)

    appopenshiftinfo_desc = 'Info Openshift App'
    appopenshiftinfo_parser = appinfo_subparsers.add_parser('openshift', description=appopenshiftinfo_desc,
                                                            help=appopenshiftinfo_desc)
    appopenshiftinfo_parser.add_argument('app', metavar='APP')
    appopenshiftinfo_parser.set_defaults(func=info_openshift_app)

    openshiftdisconnecterinfo_desc = 'Info Openshift Disonnecter'
    openshiftdisconnecterinfo_parser = info_subparsers.add_parser('disconnecter',
                                                                  description=openshiftdisconnecterinfo_desc,
                                                                  help=openshiftdisconnecterinfo_desc,
                                                                  aliases=['openshift-disconnecter'])
    openshiftdisconnecterinfo_parser.set_defaults(func=info_openshift_disconnecter)

    listapp_desc = 'List Available Kube Apps'
    listapp_parser = list_subparsers.add_parser('app', description=listapp_desc,
                                                help=listapp_desc, aliases=['apps'])
    listapp_subparsers = listapp_parser.add_subparsers(metavar='', dest='subcommand_list_app')

    appgenericlist_desc = 'List Available Kube Apps Generic'
    appgenericlist_parser = listapp_subparsers.add_parser('generic', description=appgenericlist_desc,
                                                          help=appgenericlist_desc)
    appgenericlist_parser.set_defaults(func=list_apps_generic)

    appopenshiftlist_desc = 'List Available Kube Components Openshift'
    appopenshiftlist_parser = listapp_subparsers.add_parser('openshift', description=appopenshiftlist_desc,
                                                            help=appopenshiftlist_desc)
    appopenshiftlist_parser.set_defaults(func=list_apps_openshift)

    bucketcreate_desc = 'Create Bucket'
    bucketcreate_epilog = None
    bucketcreate_parser = create_subparsers.add_parser('bucket', description=bucketcreate_desc,
                                                       help=bucketcreate_desc, epilog=bucketcreate_epilog,
                                                       formatter_class=rawhelp)
    bucketcreate_parser.add_argument('-p', '--public', action='store_true', help='Make the bucket public')
    bucketcreate_parser.add_argument('-P', '--param', action='append',
                                     help='specify parameter or keyword for rendering (multiple can be specified)',
                                     metavar='PARAM')
    bucketcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    bucketcreate_parser.add_argument('buckets', metavar='BUCKETS', nargs='+')
    bucketcreate_parser.set_defaults(func=create_bucket)

    bucketfilecreate_desc = 'Create Bucket file'
    bucketfilecreate_parser = argparse.ArgumentParser(add_help=False)
    bucketfilecreate_parser.add_argument('-p', '--public', action='store_true', help='Make the file public')
    bucketfilecreate_parser.add_argument('-t', '--temp', action='store_true', help='Get temp url')
    bucketfilecreate_parser.add_argument('bucket', metavar='BUCKET')
    bucketfilecreate_parser.add_argument('path', metavar='PATH')
    bucketfilecreate_parser.set_defaults(func=create_bucketfile)
    create_subparsers.add_parser('bucket-file', parents=[bucketfilecreate_parser],
                                 description=bucketfilecreate_desc, help=bucketfilecreate_desc)

    bucketfiledelete_desc = 'Delete Bucket file'
    bucketfiledelete_parser = argparse.ArgumentParser(add_help=False)
    bucketfiledelete_parser.add_argument('bucket', metavar='BUCKET')
    bucketfiledelete_parser.add_argument('path', metavar='PATH')
    bucketfiledelete_parser.set_defaults(func=delete_bucketfile)
    delete_subparsers.add_parser('bucket-file', parents=[bucketfiledelete_parser],
                                 description=bucketfiledelete_desc, help=bucketfiledelete_desc)

    bucketfiledownload_desc = 'Download Bucket file'
    bucketfiledownload_parser = argparse.ArgumentParser(add_help=False)
    bucketfiledownload_parser.add_argument('bucket', metavar='BUCKET')
    bucketfiledownload_parser.add_argument('path', metavar='PATH')
    bucketfiledownload_parser.set_defaults(func=download_bucketfile)
    download_subparsers.add_parser('bucket-file', parents=[bucketfiledownload_parser],
                                   description=bucketfiledownload_desc, help=bucketfiledownload_desc)

    bucketdelete_desc = 'Delete Bucket'
    bucketdelete_parser = delete_subparsers.add_parser('bucket', description=bucketdelete_desc, help=bucketdelete_desc)
    bucketdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    bucketdelete_parser.add_argument('buckets', metavar='BUCKETS', nargs='+')
    bucketdelete_parser.set_defaults(func=delete_bucket)

    bucketlist_desc = 'List Buckets'
    bucketlist_parser = list_subparsers.add_parser('bucket', description=bucketlist_desc, help=bucketlist_desc,
                                                   aliases=['buckets'])
    bucketlist_parser.set_defaults(func=list_bucket)

    bucketfileslist_desc = 'List Bucket files'
    bucketfileslist_parser = list_subparsers.add_parser('bucket-file', description=bucketfileslist_desc,
                                                        help=bucketfileslist_desc, aliases=['bucket-files'])
    bucketfileslist_parser.add_argument('bucket', metavar='BUCKET')
    bucketfileslist_parser.set_defaults(func=list_bucketfiles)

    cachedelete_desc = 'Delete Cache'
    cachedelete_parser = delete_subparsers.add_parser('cache', description=cachedelete_desc, help=cachedelete_desc)
    cachedelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    cachedelete_parser.set_defaults(func=delete_cache)

    containercreate_desc = 'Create Container'
    containercreate_epilog = None
    containercreate_parser = create_subparsers.add_parser('container', description=containercreate_desc,
                                                          help=containercreate_desc, epilog=containercreate_epilog,
                                                          formatter_class=rawhelp)
    containercreate_parser_group = containercreate_parser.add_mutually_exclusive_group(required=True)
    containercreate_parser_group.add_argument('-i', '--image', help='Image to use', metavar='Image')
    containercreate_parser_group.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    containercreate_parser.add_argument('-P', '--param', action='append',
                                        help='specify parameter or keyword for rendering (multiple can be specified)',
                                        metavar='PARAM')
    containercreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    containercreate_parser.add_argument('name', metavar='NAME', nargs='?')
    containercreate_parser.set_defaults(func=create_container)

    containerdelete_desc = 'Delete Container'
    containerdelete_parser = delete_subparsers.add_parser('container', description=containerdelete_desc,
                                                          help=containerdelete_desc)
    containerdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    containerdelete_parser.add_argument('names', metavar='CONTAINERIMAGES', nargs='+')
    containerdelete_parser.set_defaults(func=delete_container)

    containerimagelist_desc = 'List Container Images'
    containerimagelist_parser = list_subparsers.add_parser('container-image', description=containerimagelist_desc,
                                                           help=containerimagelist_desc,
                                                           aliases=['container-images'])
    containerimagelist_parser.set_defaults(func=list_containerimage)

    containerlist_desc = 'List Containers'
    containerlist_parser = list_subparsers.add_parser('container', description=containerlist_desc,
                                                      help=containerlist_desc, aliases=['containers'])
    containerlist_parser.add_argument('--filters', choices=('up', 'down'))
    containerlist_parser.set_defaults(func=list_container)

    containerprofilelist_desc = 'List Container Profiles'
    containerprofilelist_parser = list_subparsers.add_parser('container-profile', description=containerprofilelist_desc,
                                                             help=containerprofilelist_desc,
                                                             aliases=['container-profiles'])
    containerprofilelist_parser.add_argument('--short', action='store_true')
    containerprofilelist_parser.set_defaults(func=profilelist_container)

    containerrestart_desc = 'Restart Containers'
    containerrestart_parser = restart_subparsers.add_parser('container', description=containerrestart_desc,
                                                            help=containerrestart_desc)
    containerrestart_parser.add_argument('names', metavar='CONTAINERNAMES', nargs='*')
    containerrestart_parser.set_defaults(func=restart_container)

    containerstart_desc = 'Start Containers'
    containerstart_parser = start_subparsers.add_parser('container', description=containerstart_desc,
                                                        help=containerstart_desc)
    containerstart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    containerstart_parser.set_defaults(func=start_container)

    containerstop_desc = 'Stop Containers'
    containerstop_parser = stop_subparsers.add_parser('container', description=containerstop_desc,
                                                      help=containerstop_desc)
    containerstop_parser.add_argument('names', metavar='CONTAINERNAMES', nargs='*')
    containerstop_parser.set_defaults(func=stop_container)

    dnscreate_desc = 'Create Dns Entries'
    dnscreate_epilog = "examples:\n%s" % dnscreate
    dnscreate_parser = create_subparsers.add_parser('dns', description=dnscreate_desc, help=dnscreate_desc,
                                                    epilog=dnscreate_epilog,
                                                    formatter_class=rawhelp)
    dnscreate_parser.add_argument('-a', '--alias', action='append', help='specify alias (can specify multiple)',
                                  metavar='ALIAS')
    dnscreate_parser.add_argument('-d', '--domain', help='Domain where to create entry', metavar='DOMAIN')
    dnscreate_parser.add_argument('-n', '--net', help='Network where to create entry. Defaults to default',
                                  default='default', metavar='NET')
    dnscreate_parser.add_argument('-i', '--ip', help='Ip', metavar='IP')
    dnscreate_parser.add_argument('names', metavar='NAMES', nargs='*')
    dnscreate_parser.set_defaults(func=create_dns)

    dnsdelete_desc = 'Delete Dns Entries'
    dnsdelete_parser = delete_subparsers.add_parser('dns', description=dnsdelete_desc, help=dnsdelete_desc)
    dnsdelete_parser.add_argument('-a', '--all', action='store_true',
                                  help='Whether to delete the entire host block. Libvirt specific')
    dnsdelete_parser.add_argument('-d', '--domain', help='Domain of the entry', metavar='DOMAIN')
    dnsdelete_parser.add_argument('-n', '--net', help='Network where to delete entry. Defaults to default',
                                  default='default', metavar='NET')
    dnsdelete_parser.add_argument('names', metavar='NAMES', nargs='*')
    dnsdelete_parser.set_defaults(func=delete_dns)

    dnslist_desc = 'List Dns Entries'
    dnslist_parser = argparse.ArgumentParser(add_help=False)
    dnslist_parser.add_argument('--short', action='store_true')
    dnslist_parser.add_argument('domain', metavar='DOMAIN', help='Domain where to list entry (network for libvirt)')
    dnslist_parser.set_defaults(func=list_dns)
    list_subparsers.add_parser('dns', parents=[dnslist_parser], description=dnslist_desc, help=dnslist_desc)

    hostcreate_desc = 'Create Host'
    hostcreate_epilog = "examples:\n%s" % hostcreate
    hostcreate_parser = create_subparsers.add_parser('host', help=hostcreate_desc, description=hostcreate_desc,
                                                     aliases=['client'], epilog=hostcreate_epilog,
                                                     formatter_class=rawhelp)
    hostcreate_subparsers = hostcreate_parser.add_subparsers(metavar='', dest='subcommand_create_host')

    awshostcreate_desc = 'Create Aws Host'
    awshostcreate_parser = hostcreate_subparsers.add_parser('aws', help=awshostcreate_desc,
                                                            description=awshostcreate_desc)
    awshostcreate_parser.add_argument('--access_key_id', help='Access Key Id', metavar='ACCESS_KEY_ID', required=True)
    awshostcreate_parser.add_argument('--access_key_secret', help='Access Key Secret', metavar='ACCESS_KEY_SECRET',
                                      required=True)
    awshostcreate_parser.add_argument('-k', '--keypair', help='Keypair', metavar='KEYPAIR', required=True)
    awshostcreate_parser.add_argument('-r', '--region', help='Region', metavar='REGION', required=True)
    awshostcreate_parser.add_argument('name', metavar='NAME')
    awshostcreate_parser.set_defaults(func=create_host_aws)

    ibmhostcreate_desc = 'Create IBM Cloud Host'
    ibmhostcreate_parser = hostcreate_subparsers.add_parser('ibm', help=ibmhostcreate_desc,
                                                            description=ibmhostcreate_desc)
    ibmhostcreate_parser.add_argument('--iam_api_key', help='IAM API Key', metavar='IAM_API_KEY', required=True)
    ibmhostcreate_parser.add_argument('--access_key_id', help='Access Key Id', metavar='ACCESS_KEY_ID')
    ibmhostcreate_parser.add_argument('--access_key_secret', help='Access Key Secret', metavar='ACCESS_KEY_SECRET')
    ibmhostcreate_parser.add_argument('--vpc', help='VPC name', metavar='VPC')
    ibmhostcreate_parser.add_argument('--zone', help='Zone within the region', metavar='ZONE')
    ibmhostcreate_parser.add_argument('-r', '--region', help='Region', metavar='REGION', required=True)
    ibmhostcreate_parser.add_argument('name', metavar='NAME')
    ibmhostcreate_parser.set_defaults(func=create_host_ibm)

    gcphostcreate_desc = 'Create Gcp Host'
    gcphostcreate_parser = hostcreate_subparsers.add_parser('gcp', help=gcphostcreate_desc,
                                                            description=gcphostcreate_desc)
    gcphostcreate_parser.add_argument('--credentials', help='Path to credentials file', metavar='credentials')
    gcphostcreate_parser.add_argument('--project', help='Project', metavar='project', required=True)
    gcphostcreate_parser.add_argument('--zone', help='Zone', metavar='zone', required=True)
    gcphostcreate_parser.add_argument('name', metavar='NAME')
    gcphostcreate_parser.set_defaults(func=create_host_gcp)

    grouphostcreate_desc = 'Create Group Host'
    grouphostcreate_parser = hostcreate_subparsers.add_parser('group', help=grouphostcreate_desc,
                                                              description=grouphostcreate_desc)
    grouphostcreate_parser.add_argument('-a', '--algorithm', help='Algorithm. Defaults to random',
                                        metavar='ALGORITHM', default='random')
    grouphostcreate_parser.add_argument('-m', '--members', help='Members', metavar='MEMBERS', type=valid_members)
    grouphostcreate_parser.add_argument('name', metavar='NAME')
    grouphostcreate_parser.set_defaults(func=create_host_group)

    kvmhostcreate_desc = 'Create Kvm Host'
    kvmhostcreate_parser = hostcreate_subparsers.add_parser('kvm', help=kvmhostcreate_desc,
                                                            description=kvmhostcreate_desc)
    kvmhostcreate_parser_group = kvmhostcreate_parser.add_mutually_exclusive_group(required=True)
    kvmhostcreate_parser_group.add_argument('-H', '--host', help='Host. Defaults to localhost', metavar='HOST',
                                            default='localhost')
    kvmhostcreate_parser.add_argument('--pool', help='Pool. Defaults to default', metavar='POOL', default='default')
    kvmhostcreate_parser.add_argument('-p', '--port', help='Port', metavar='PORT')
    kvmhostcreate_parser.add_argument('-P', '--protocol', help='Protocol to use', default='ssh', metavar='PROTOCOL')
    kvmhostcreate_parser_group.add_argument('-U', '--url', help='URL to use', metavar='URL')
    kvmhostcreate_parser.add_argument('-u', '--user', help='User. Defaults to root', default='root', metavar='USER')
    kvmhostcreate_parser.add_argument('name', metavar='NAME')
    kvmhostcreate_parser.set_defaults(func=create_host_kvm)

    kubevirthostcreate_desc = 'Create Kubevirt Host'
    kubevirthostcreate_parser = hostcreate_subparsers.add_parser('kubevirt', help=kubevirthostcreate_desc,
                                                                 description=kubevirthostcreate_desc)
    kubevirthostcreate_parser.add_argument('--ca', help='Ca file', metavar='CA')
    kubevirthostcreate_parser.add_argument('--cdi', help='Cdi Support', action='store_true', default=True)
    kubevirthostcreate_parser.add_argument('-c', '--context', help='Context', metavar='CONTEXT')
    kubevirthostcreate_parser.add_argument('-H', '--host', help='Api Host', metavar='HOST')
    kubevirthostcreate_parser.add_argument('-p', '--pool', help='Storage Class', metavar='POOL')
    kubevirthostcreate_parser.add_argument('--port', help='Api Port', metavar='HOST')
    kubevirthostcreate_parser.add_argument('--token', help='Token', metavar='TOKEN')
    kubevirthostcreate_parser.add_argument('--multus', help='Multus Support', action='store_true', default=True)
    kubevirthostcreate_parser.add_argument('name', metavar='NAME')
    kubevirthostcreate_parser.set_defaults(func=create_host_kubevirt)

    openstackhostcreate_desc = 'Create Openstack Host'
    openstackhostcreate_parser = hostcreate_subparsers.add_parser('openstack', help=openstackhostcreate_desc,
                                                                  description=openstackhostcreate_desc)
    openstackhostcreate_parser.add_argument('--auth-url', help='Auth url', metavar='AUTH_URL', required=True)
    openstackhostcreate_parser.add_argument('--domain', help='Domain', metavar='DOMAIN', default='Default')
    openstackhostcreate_parser.add_argument('-p', '--password', help='Password', metavar='PASSWORD', required=True)
    openstackhostcreate_parser.add_argument('--project', help='Project', metavar='PROJECT', required=True)
    openstackhostcreate_parser.add_argument('-u', '--user', help='User', metavar='USER', required=True)
    openstackhostcreate_parser.add_argument('name', metavar='NAME')
    openstackhostcreate_parser.set_defaults(func=create_host_openstack)

    ovirthostcreate_desc = 'Create Ovirt Host'
    ovirthostcreate_parser = hostcreate_subparsers.add_parser('ovirt', help=ovirthostcreate_desc,
                                                              description=ovirthostcreate_desc)
    ovirthostcreate_parser.add_argument('--ca', help='Path to certificate file', metavar='CA')
    ovirthostcreate_parser.add_argument('-c', '--cluster', help='Cluster. Defaults to Default', default='Default',
                                        metavar='CLUSTER')
    ovirthostcreate_parser.add_argument('-d', '--datacenter', help='Datacenter. Defaults to Default', default='Default',
                                        metavar='DATACENTER')
    ovirthostcreate_parser.add_argument('-H', '--host', help='Host to use', metavar='HOST', required=True)
    ovirthostcreate_parser.add_argument('-o', '--org', help='Organization', metavar='ORGANIZATION', required=True)
    ovirthostcreate_parser.add_argument('-p', '--password', help='Password to use', metavar='PASSWORD', required=True)
    ovirthostcreate_parser.add_argument('--pool', help='Storage Domain', metavar='POOL')
    ovirthostcreate_parser.add_argument('-u', '--user', help='User. Defaults to admin@internal',
                                        metavar='USER', default='admin@internal')
    ovirthostcreate_parser.add_argument('name', metavar='NAME')
    ovirthostcreate_parser.set_defaults(func=create_host_ovirt)

    vspherehostcreate_desc = 'Create Vsphere Host'
    vspherehostcreate_parser = hostcreate_subparsers.add_parser('vsphere', help=vspherehostcreate_desc,
                                                                description=vspherehostcreate_desc)
    vspherehostcreate_parser.add_argument('-c', '--cluster', help='Cluster', metavar='CLUSTER', required=True)
    vspherehostcreate_parser.add_argument('-d', '--datacenter', help='Datacenter', metavar='DATACENTER', required=True)
    vspherehostcreate_parser.add_argument('-H', '--host', help='Vcenter Host', metavar='HOST', required=True)
    vspherehostcreate_parser.add_argument('-p', '--password', help='Password', metavar='PASSWORD', required=True)
    vspherehostcreate_parser.add_argument('-u', '--user', help='User', metavar='USER', required=True)
    vspherehostcreate_parser.add_argument('--pool', help='Pool', metavar='POOL')
    vspherehostcreate_parser.add_argument('name', metavar='NAME')
    vspherehostcreate_parser.set_defaults(func=create_host_vsphere)

    hostdelete_desc = 'Delete Host'
    hostdelete_parser = delete_subparsers.add_parser('host', description=hostdelete_desc, help=hostdelete_desc,
                                                     aliases=['client'])
    hostdelete_parser.add_argument('name', metavar='NAME')
    hostdelete_parser.set_defaults(func=delete_host)

    hostdisable_desc = 'Disable Host'
    hostdisable_parser = disable_subparsers.add_parser('host', description=hostdisable_desc, help=hostdisable_desc,
                                                       aliases=['client'])
    hostdisable_parser.add_argument('name', metavar='NAME')
    hostdisable_parser.set_defaults(func=disable_host)

    hostenable_desc = 'Enable Host'
    hostenable_parser = enable_subparsers.add_parser('host', description=hostenable_desc, help=hostenable_desc,
                                                     aliases=['client'])
    hostenable_parser.add_argument('name', metavar='NAME')
    hostenable_parser.set_defaults(func=enable_host)

    hostlist_parser = list_subparsers.add_parser('host', description=hostlist_desc, help=hostlist_desc,
                                                 aliases=['hosts', 'client', 'clients'])
    hostlist_parser.set_defaults(func=list_host)

    hostreport_desc = 'Report Info About Host'
    hostreport_parser = argparse.ArgumentParser(add_help=False)
    hostreport_parser.set_defaults(func=report_host)
    info_subparsers.add_parser('host', parents=[hostreport_parser], description=hostreport_desc, help=hostreport_desc,
                               aliases=['client'])

    hostswitch_desc = 'Switch Host'
    hostswitch_parser = argparse.ArgumentParser(add_help=False)
    hostswitch_parser.add_argument('name', help='NAME')
    hostswitch_parser.set_defaults(func=switch_host)
    switch_subparsers.add_parser('host', parents=[hostswitch_parser], description=hostswitch_desc, help=hostswitch_desc,
                                 aliases=['client'])

    hostsync_desc = 'Sync Host'
    hostsync_parser = sync_subparsers.add_parser('host', description=hostsync_desc, help=hostsync_desc,
                                                 aliases=['client'])
    hostsync_parser.add_argument('names', help='NAMES', nargs='*')
    hostsync_parser.set_defaults(func=sync_host)

    imagedelete_desc = 'Delete Image'
    imagedelete_help = "Image to delete"
    imagedelete_parser = argparse.ArgumentParser(add_help=False)
    imagedelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    imagedelete_parser.add_argument('-p', '--pool', help='Pool to use', metavar='POOL')
    imagedelete_parser.add_argument('images', help=imagedelete_help, metavar='IMAGES', nargs='*')
    imagedelete_parser.set_defaults(func=delete_image)
    delete_subparsers.add_parser('image', parents=[imagedelete_parser], description=imagedelete_desc,
                                 help=imagedelete_desc)
    delete_subparsers.add_parser('iso', parents=[imagedelete_parser], description=imagedelete_desc,
                                 help=imagedelete_desc)

    kubecreate_desc = 'Create Kube'
    kubecreate_parser = create_subparsers.add_parser('kube', description=kubecreate_desc, help=kubecreate_desc,
                                                     aliases=['cluster'])
    kubecreate_subparsers = kubecreate_parser.add_subparsers(metavar='', dest='subcommand_create_kube')

    kubegenericcreate_desc = 'Create Generic Kube'
    kubegenericcreate_epilog = "examples:\n%s" % kubegenericcreate
    kubegenericcreate_parser = argparse.ArgumentParser(add_help=False)
    kubegenericcreate_parser.add_argument('-f', '--force', action='store_true', help='Delete existing cluster first')
    kubegenericcreate_parser.add_argument('-P', '--param', action='append',
                                          help='specify parameter or keyword for rendering (multiple can be specified)',
                                          metavar='PARAM')
    kubegenericcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubegenericcreate_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubegenericcreate_parser.set_defaults(func=create_generic_kube)
    kubecreate_subparsers.add_parser('generic', parents=[kubegenericcreate_parser],
                                     description=kubegenericcreate_desc,
                                     help=kubegenericcreate_desc,
                                     epilog=kubegenericcreate_epilog,
                                     formatter_class=rawhelp, aliases=['kubeadm'])

    kubekindcreate_desc = 'Create Kind Kube'
    kubekindcreate_epilog = "examples:\n%s" % kubekindcreate
    kubekindcreate_parser = argparse.ArgumentParser(add_help=False)
    kubekindcreate_parser.add_argument('-f', '--force', action='store_true', help='Delete existing cluster first')
    kubekindcreate_parser.add_argument('-P', '--param', action='append',
                                       help='specify parameter or keyword for rendering (multiple can be specified)',
                                       metavar='PARAM')
    kubekindcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubekindcreate_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubekindcreate_parser.set_defaults(func=create_kind_kube)
    kubecreate_subparsers.add_parser('kind', parents=[kubekindcreate_parser],
                                     description=kubekindcreate_desc,
                                     help=kubekindcreate_desc,
                                     epilog=kubekindcreate_epilog,
                                     formatter_class=rawhelp)

    kubek3screate_desc = 'Create K3s Kube'
    kubek3screate_epilog = "examples:\n%s" % kubek3screate
    kubek3screate_parser = argparse.ArgumentParser(add_help=False)
    kubek3screate_parser.add_argument('-f', '--force', action='store_true', help='Delete existing cluster first')
    kubek3screate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (multiple can be specified)',
                                      metavar='PARAM')
    kubek3screate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubek3screate_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubek3screate_parser.set_defaults(func=create_k3s_kube)
    kubecreate_subparsers.add_parser('k3s', parents=[kubek3screate_parser],
                                     description=kubek3screate_desc,
                                     help=kubek3screate_desc,
                                     epilog=kubek3screate_epilog,
                                     formatter_class=rawhelp)

    parameterhelp = "specify parameter or keyword for rendering (multiple can be specified)"
    kubeopenshiftcreate_desc = 'Create Openshift Kube'
    kubeopenshiftcreate_epilog = "examples:\n%s" % kubeopenshiftcreate
    kubeopenshiftcreate_parser = argparse.ArgumentParser(add_help=False)
    kubeopenshiftcreate_parser.add_argument('-f', '--force', action='store_true', help='Delete existing cluster first')
    kubeopenshiftcreate_parser.add_argument('-P', '--param', action='append', help=parameterhelp, metavar='PARAM')
    kubeopenshiftcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubeopenshiftcreate_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubeopenshiftcreate_parser.set_defaults(func=create_openshift_kube)
    kubecreate_subparsers.add_parser('openshift', parents=[kubeopenshiftcreate_parser],
                                     description=kubeopenshiftcreate_desc,
                                     help=kubeopenshiftcreate_desc,
                                     epilog=kubeopenshiftcreate_epilog,
                                     formatter_class=rawhelp, aliases=['okd'])

    kubedelete_desc = 'Delete Kube'
    kubedelete_parser = argparse.ArgumentParser(add_help=False)
    kubedelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    kubedelete_parser.add_argument('-P', '--param', action='append',
                                   help='specify parameter or keyword for rendering (multiple can be specified)',
                                   metavar='PARAM')
    kubedelete_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubedelete_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubedelete_parser.set_defaults(func=delete_kube)
    delete_subparsers.add_parser('kube', parents=[kubedelete_parser], description=kubedelete_desc, help=kubedelete_desc,
                                 aliases=['cluster'])

    kubeinfo_desc = 'Info Kube'
    kubeinfo_parser = info_subparsers.add_parser('kube', description=kubeinfo_desc, help=kubeinfo_desc,
                                                 aliases=['cluster'])
    kubeinfo_subparsers = kubeinfo_parser.add_subparsers(metavar='', dest='subcommand_info_kube')

    kubegenericinfo_desc = 'Info Generic Kube'
    kubegenericinfo_parser = kubeinfo_subparsers.add_parser('generic', description=kubegenericinfo_desc,
                                                            help=kubegenericinfo_desc, aliases=['kubeadm'])
    kubegenericinfo_parser.set_defaults(func=info_generic_kube)

    kubekindinfo_desc = 'Info Kind Kube'
    kubekindinfo_parser = kubeinfo_subparsers.add_parser('kind', description=kubekindinfo_desc, help=kubekindinfo_desc)
    kubekindinfo_parser.set_defaults(func=info_kind_kube)

    kubek3sinfo_desc = 'Info K3s Kube'
    kubek3sinfo_parser = kubeinfo_subparsers.add_parser('k3s', description=kubek3sinfo_desc, help=kubek3sinfo_desc)
    kubek3sinfo_parser.set_defaults(func=info_k3s_kube)

    kubeopenshiftinfo_desc = 'Info Openshift Kube'
    kubeopenshiftinfo_parser = kubeinfo_subparsers.add_parser('openshift', description=kubeopenshiftinfo_desc,
                                                              help=kubeopenshiftinfo_desc, aliases=['okd'])
    kubeopenshiftinfo_parser.set_defaults(func=info_openshift_kube)

    kubelist_desc = 'List Kubes'
    kubelist_parser = list_subparsers.add_parser('kube', description=kubelist_desc, help=kubelist_desc,
                                                 aliases=['kubes', 'cluster', 'clusters'])
    kubelist_parser.set_defaults(func=list_kube)

    kubescale_desc = 'Scale Kube'
    kubescale_parser = scale_subparsers.add_parser('kube', description=kubescale_desc, help=kubescale_desc,
                                                   aliases=['cluster'])
    kubescale_subparsers = kubescale_parser.add_subparsers(metavar='', dest='subcommand_scale_kube')

    kubegenericscale_desc = 'Scale Generic Kube'
    kubegenericscale_parser = argparse.ArgumentParser(add_help=False)
    kubegenericscale_parser.add_argument('-P', '--param', action='append',
                                         help='specify parameter or keyword for rendering (multiple can be specified)',
                                         metavar='PARAM')
    kubegenericscale_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubegenericscale_parser.add_argument('-w', '--workers', help='Total number of workers', type=int, default=0)
    kubegenericscale_parser.add_argument('cluster', metavar='CLUSTER', type=valid_cluster, default='testk')
    kubegenericscale_parser.set_defaults(func=scale_generic_kube)
    kubescale_subparsers.add_parser('generic', parents=[kubegenericscale_parser], description=kubegenericscale_desc,
                                    help=kubegenericscale_desc, aliases=['kubeadm'])

    kubek3sscale_desc = 'Scale K3s Kube'
    kubek3sscale_parser = argparse.ArgumentParser(add_help=False)
    kubek3sscale_parser.add_argument('-P', '--param', action='append',
                                     help='specify parameter or keyword for rendering (multiple can be specified)',
                                     metavar='PARAM')
    kubek3sscale_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubek3sscale_parser.add_argument('-w', '--workers', help='Total number of workers', type=int, default=0)
    kubek3sscale_parser.add_argument('cluster', metavar='CLUSTER', type=valid_cluster, default='testk')
    kubek3sscale_parser.set_defaults(func=scale_k3s_kube)
    kubescale_subparsers.add_parser('k3s', parents=[kubek3sscale_parser], description=kubek3sscale_desc,
                                    help=kubek3sscale_desc)

    parameterhelp = "specify parameter or keyword for rendering (multiple can be specified)"
    kubeopenshiftscale_desc = 'Scale Openshift Kube'
    kubeopenshiftscale_parser = argparse.ArgumentParser(add_help=False)
    kubeopenshiftscale_parser.add_argument('-P', '--param', action='append', help=parameterhelp, metavar='PARAM')
    kubeopenshiftscale_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubeopenshiftscale_parser.add_argument('-w', '--workers', help='Total number of workers', type=int, default=0)
    kubeopenshiftscale_parser.add_argument('cluster', metavar='CLUSTER', type=valid_cluster, default='testk')
    kubeopenshiftscale_parser.set_defaults(func=scale_openshift_kube)
    kubescale_subparsers.add_parser('openshift', parents=[kubeopenshiftscale_parser],
                                    description=kubeopenshiftscale_desc,
                                    help=kubeopenshiftscale_desc, aliases=['okd'])

    kubeupdate_desc = 'Update Kube'
    kubeupdate_parser = update_subparsers.add_parser('kube', description=kubeupdate_desc, help=kubeupdate_desc,
                                                     aliases=['cluster'])
    kubeupdate_subparsers = kubeupdate_parser.add_subparsers(metavar='', dest='subcommand_update_kube')

    kubegenericupdate_desc = 'Update Generic Kube'
    kubegenericupdate_parser = argparse.ArgumentParser(add_help=False)
    kubegenericupdate_parser.add_argument('-P', '--param', action='append',
                                          help='specify parameter or keyword for rendering (multiple can be specified)',
                                          metavar='PARAM')
    kubegenericupdate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubegenericupdate_parser.add_argument('cluster', metavar='CLUSTER', type=valid_cluster, default='testk')
    kubegenericupdate_parser.set_defaults(func=update_generic_kube)
    kubeupdate_subparsers.add_parser('generic', parents=[kubegenericupdate_parser], description=kubegenericupdate_desc,
                                     help=kubegenericupdate_desc, aliases=['kubeadm'])

    kubek3supdate_desc = 'Update K3s Kube'
    kubek3supdate_parser = argparse.ArgumentParser(add_help=False)
    kubek3supdate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (multiple can be specified)',
                                      metavar='PARAM')
    kubek3supdate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubek3supdate_parser.add_argument('cluster', metavar='CLUSTER', type=valid_cluster, default='testk')
    kubek3supdate_parser.set_defaults(func=update_k3s_kube)
    kubeupdate_subparsers.add_parser('k3s', parents=[kubek3supdate_parser], description=kubek3supdate_desc,
                                     help=kubek3supdate_desc)

    parameterhelp = "specify parameter or keyword for rendering (multiple can be specified)"
    kubeopenshiftupdate_desc = 'Update Openshift Kube'
    kubeopenshiftupdate_parser = argparse.ArgumentParser(add_help=False)
    kubeopenshiftupdate_parser.add_argument('-P', '--param', action='append', help=parameterhelp, metavar='PARAM')
    kubeopenshiftupdate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubeopenshiftupdate_parser.add_argument('cluster', metavar='CLUSTER', type=valid_cluster, default='testk')
    kubeopenshiftupdate_parser.set_defaults(func=update_openshift_kube)
    kubeupdate_subparsers.add_parser('openshift', parents=[kubeopenshiftupdate_parser],
                                     description=kubeopenshiftupdate_desc,
                                     help=kubeopenshiftupdate_desc, aliases=['okd'])

    lbcreate_desc = 'Create Load Balancer'
    lbcreate_parser = create_subparsers.add_parser('lb', description=lbcreate_desc, help=lbcreate_desc,
                                                   aliases=['loadbalancer'])
    lbcreate_parser.add_argument('--checkpath', default='/index.html', help="Path to check. Defaults to /index.html")
    lbcreate_parser.add_argument('--checkport', default=80, help="Port to check. Defaults to 80")
    lbcreate_parser.add_argument('--domain', help='Domain to create a dns entry associated to the load balancer')
    lbcreate_parser.add_argument('-i', '--internal', action='store_true')
    lbcreate_parser.add_argument('-p', '--ports', default='443', help='Load Balancer Ports. Defaults to 443')
    lbcreate_parser.add_argument('-v', '--vms', help='Vms to add to the pool. Can also be a list of ips')
    lbcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    lbcreate_parser.set_defaults(func=create_lb)

    lbdelete_desc = 'Delete Load Balancer'
    lbdelete_parser = delete_subparsers.add_parser('lb', description=lbdelete_desc, help=lbdelete_desc,
                                                   aliases=['loadbalancer'])
    lbdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    lbdelete_parser.add_argument('name', metavar='NAME')
    lbdelete_parser.set_defaults(func=delete_lb)

    lblist_desc = 'List Load Balancers'
    lblist_parser = list_subparsers.add_parser('lb', description=lblist_desc, help=lblist_desc,
                                               aliases=['loadbalancers', 'lbs'])
    lblist_parser.add_argument('--short', action='store_true')
    lblist_parser.set_defaults(func=list_lb)

    keywordinfo_desc = 'Info Keyword'
    keywordinfo_parser = info_subparsers.add_parser('keyword', description=keywordinfo_desc, help=keywordinfo_desc,
                                                    aliases=['parameter'])
    keywordinfo_parser.add_argument('keyword', metavar='KEYWORD')
    keywordinfo_parser.set_defaults(func=info_keyword)

    profilecreate_desc = 'Create Profile'
    profilecreate_parser = argparse.ArgumentParser(add_help=False)
    profilecreate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (can specify multiple)',
                                      metavar='PARAM')
    profilecreate_parser.add_argument('profile', metavar='PROFILE')
    profilecreate_parser.set_defaults(func=create_profile)
    create_subparsers.add_parser('profile', parents=[profilecreate_parser], description=profilecreate_desc,
                                 help=profilecreate_desc)

    profileinfo_desc = 'Info Profile'
    profileinfo_parser = info_subparsers.add_parser('profile', description=profileinfo_desc, help=profileinfo_desc)
    profileinfo_parser.add_argument('profile', metavar='PROFILE')
    profileinfo_parser.set_defaults(func=info_profile)

    profilelist_desc = 'List Profiles'
    profilelist_parser = list_subparsers.add_parser('profile', description=profilelist_desc, help=profilelist_desc,
                                                    aliases=['profiles'])
    profilelist_parser.add_argument('--short', action='store_true')
    profilelist_parser.set_defaults(func=list_profile)

    profileupdate_desc = 'Update Profile'
    profileupdate_parser = update_subparsers.add_parser('profile', description=profileupdate_desc,
                                                        help=profileupdate_desc)
    profileupdate_parser.add_argument('-P', '--param', action='append',
                                      help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    profileupdate_parser.add_argument('profile', metavar='PROFILE', nargs='?')
    profileupdate_parser.set_defaults(func=update_profile)

    flavorlist_desc = 'List Flavors'
    flavorlist_parser = list_subparsers.add_parser('flavor', description=flavorlist_desc, help=flavorlist_desc,
                                                   aliases=['flavors'])
    flavorlist_parser.add_argument('--short', action='store_true')
    flavorlist_parser.set_defaults(func=list_flavor)

    isolist_desc = 'List Isos'
    isolist_parser = list_subparsers.add_parser('iso', description=isolist_desc, help=isolist_desc, aliases=['isos'])
    isolist_parser.set_defaults(func=list_iso)

    keywordlist_desc = 'List Keyword'
    keywordlist_parser = list_subparsers.add_parser('keyword', description=keywordlist_desc, help=keywordlist_desc,
                                                    aliases=['keywords', 'parameter', 'parameters'])
    keywordlist_parser.set_defaults(func=list_keyword)

    networkinfo_desc = 'Info Network'
    networkinfo_parser = info_subparsers.add_parser('network', description=networkinfo_desc, help=networkinfo_desc)
    networkinfo_parser.add_argument('name', metavar='NETWORK')
    networkinfo_parser.set_defaults(func=info_network)

    networklist_desc = 'List Networks'
    networklist_parser = list_subparsers.add_parser('network', description=networklist_desc, help=networklist_desc,
                                                    aliases=['networks'])
    networklist_parser.add_argument('--short', action='store_true')
    networklist_parser.add_argument('-s', '--subnets', action='store_true')
    networklist_parser.set_defaults(func=list_network)

    networkcreate_desc = 'Create Network'
    networkcreate_parser = create_subparsers.add_parser('network', description=networkcreate_desc,
                                                        help=networkcreate_desc)
    networkcreate_parser.add_argument('-i', '--isolated', action='store_true', help='Isolated Network')
    networkcreate_parser.add_argument('-c', '--cidr', help='Cidr of the net', metavar='CIDR')
    networkcreate_parser.add_argument('-d', '--dual', help='Cidr of dual net', metavar='DUAL')
    networkcreate_parser.add_argument('--nodhcp', action='store_true', help='Disable dhcp on the net')
    networkcreate_parser.add_argument('--domain', help='DNS domain. Defaults to network name')
    networkcreate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (can specify multiple)',
                                      metavar='PARAM')
    networkcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    networkcreate_parser.add_argument('name', metavar='NETWORK')
    networkcreate_parser.set_defaults(func=create_network)

    networkdelete_desc = 'Delete Network'
    networkdelete_parser = delete_subparsers.add_parser('network', description=networkdelete_desc,
                                                        help=networkdelete_desc)
    networkdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    networkdelete_parser.add_argument('names', metavar='NETWORKS', nargs='+')
    networkdelete_parser.set_defaults(func=delete_network)

    disconnectercreate_desc = 'Create a disconnecter vm for openshift'
    disconnectercreate_epilog = "examples:\n%s" % disconnectercreate
    disconnectercreate_parser = argparse.ArgumentParser(add_help=False)
    disconnectercreate_parser.add_argument('-P', '--param', action='append',
                                           help='specify parameter or keyword for rendering (can specify multiple)',
                                           metavar='PARAM')
    disconnectercreate_parser.add_argument('plan', metavar='PLAN', help='Plan', nargs='?')
    disconnectercreate_parser.set_defaults(func=create_openshift_disconnecter)
    create_subparsers.add_parser('openshift-disconnecter', parents=[disconnectercreate_parser],
                                 description=disconnectercreate_desc, help=disconnectercreate_desc,
                                 epilog=disconnectercreate_epilog, formatter_class=rawhelp)

    isocreate_desc = 'Create an iso ignition for baremetal install'
    isocreate_epilog = "examples:\n%s" % isocreate
    isocreate_parser = argparse.ArgumentParser(add_help=False)
    isocreate_parser.add_argument('-d', '--direct', action='store_true', help='Embed directly target ignition in iso')
    isocreate_parser.add_argument('-f', '--ignitionfile', help='Ignition file')
    isocreate_parser.add_argument('-P', '--param', action='append',
                                  help='specify parameter or keyword for rendering (can specify multiple)',
                                  metavar='PARAM')
    isocreate_parser.add_argument('cluster', metavar='CLUSTER', help='Cluster')
    isocreate_parser.set_defaults(func=create_openshift_iso)
    create_subparsers.add_parser('openshift-iso', parents=[isocreate_parser], description=isocreate_desc,
                                 help=isocreate_desc, epilog=isocreate_epilog, formatter_class=rawhelp)

    pipelinecreate_desc = 'Create Pipeline'
    pipelinecreate_parser = create_subparsers.add_parser('pipeline', description=pipelinecreate_desc,
                                                         help=pipelinecreate_desc)
    pipelinecreate_subparsers = pipelinecreate_parser.add_subparsers(metavar='', dest='subcommand_create_pipeline')

    githubpipelinecreate_desc = 'Create Github Pipeline'
    githubpipelinecreate_parser = pipelinecreate_subparsers.add_parser('github', description=githubpipelinecreate_desc,
                                                                       help=githubpipelinecreate_desc, aliases=['gha'])
    githubpipelinecreate_parser.add_argument('-f', '--inputfile', help='Input Plan (or script) file')
    githubpipelinecreate_parser.add_argument('-k', '--kube', action='store_true', help='Create kube pipeline')
    githubpipelinecreate_parser.add_argument('-s', '--script', action='store_true', help='Create script pipeline')
    githubpipelinecreate_parser.add_argument('-P', '--param', action='append',
                                             help='Define parameter for rendering (can specify multiple)',
                                             metavar='PARAM')
    githubpipelinecreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    githubpipelinecreate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    githubpipelinecreate_parser.set_defaults(func=create_pipeline_github)

    jenkinspipelinecreate_desc = 'Create Jenkins Pipeline'
    jenkinspipelinecreate_parser = pipelinecreate_subparsers.add_parser('jenkins',
                                                                        description=jenkinspipelinecreate_desc,
                                                                        help=jenkinspipelinecreate_desc)
    jenkinspipelinecreate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    jenkinspipelinecreate_parser.add_argument('-k', '--kube', action='store_true', help='Create kube pipeline')
    jenkinspipelinecreate_parser.add_argument('-P', '--param', action='append',
                                              help='Define parameter for rendering (can specify multiple)',
                                              metavar='PARAM')
    jenkinspipelinecreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    jenkinspipelinecreate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    jenkinspipelinecreate_parser.set_defaults(func=create_pipeline_jenkins)

    tektonpipelinecreate_desc = 'Create Tekton Pipeline'
    tektonpipelinecreate_parser = pipelinecreate_subparsers.add_parser('tekton',
                                                                       description=tektonpipelinecreate_desc,
                                                                       help=tektonpipelinecreate_desc)
    tektonpipelinecreate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    tektonpipelinecreate_parser.add_argument('-k', '--kube', action='store_true', help='Create kube pipeline')
    tektonpipelinecreate_parser.add_argument('-P', '--param', action='append',
                                             help='Define parameter for rendering (can specify multiple)',
                                             metavar='PARAM')
    tektonpipelinecreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    tektonpipelinecreate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    tektonpipelinecreate_parser.set_defaults(func=create_pipeline_tekton)

    plancreate_desc = 'Create Plan'
    plancreate_epilog = "examples:\n%s" % plancreate
    plancreate_parser = create_subparsers.add_parser('plan', description=plancreate_desc, help=plancreate_desc,
                                                     epilog=plancreate_epilog,
                                                     formatter_class=rawhelp)
    plancreate_parser.add_argument('-A', '--ansible', help='Generate ansible inventory', action='store_true')
    plancreate_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL', type=valid_url)
    plancreate_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan',
                                   metavar='PATH')
    plancreate_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    plancreate_parser.add_argument('--force', action='store_true', help='Delete existing vms first')
    plancreate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    plancreate_parser.add_argument('-k', '--skippre', action='store_true', help='Skip pre script')
    plancreate_parser.add_argument('-z', '--skippost', action='store_true', help='Skip post script')
    plancreate_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    plancreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    plancreate_parser.add_argument('-t', '--threaded', help='Run threaded', action='store_true')
    plancreate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plancreate_parser.set_defaults(func=create_plan)

    plandelete_desc = 'Delete Plan'
    plandelete_parser = delete_subparsers.add_parser('plan', description=plandelete_desc, help=plandelete_desc)
    plandelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    plandelete_parser.add_argument('plans', metavar='PLAN', nargs='*')
    plandelete_parser.set_defaults(func=delete_plan)

    plansnapshotdelete_desc = 'Delete Plan Snapshot'
    plansnapshotdelete_parser = delete_subparsers.add_parser('plan-snapshot', description=plansnapshotdelete_desc,
                                                             help=plansnapshotdelete_desc)
    plansnapshotdelete_parser.add_argument('-p', '--plan', help='plan name', required=True, metavar='PLAN')
    plansnapshotdelete_parser.add_argument('snapshot', metavar='SNAPSHOT')
    plansnapshotdelete_parser.set_defaults(func=delete_snapshot_plan)

    planexpose_desc = 'Expose plan'
    planexpose_epilog = None
    planexpose_parser = argparse.ArgumentParser(add_help=False)
    planexpose_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planexpose_parser.add_argument('-i', '--installermode', action='store_true', help='Filter by installervm')
    planexpose_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    planexpose_parser.add_argument('--port', help='Port where to listen', type=int, default=9000, metavar='PORT')
    planexpose_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planexpose_parser.set_defaults(func=expose_plan)
    expose_subparsers.add_parser('plan', parents=[planexpose_parser], description=vmssh_desc, help=planexpose_desc,
                                 epilog=planexpose_epilog, formatter_class=rawhelp)

    planinfo_desc = 'Info Plan'
    planinfo_epilog = "examples:\n%s" % planinfo
    planinfo_parser = info_subparsers.add_parser('plan', description=planinfo_desc, help=planinfo_desc,
                                                 epilog=planinfo_epilog,
                                                 formatter_class=rawhelp)
    planinfo_parser.add_argument('--doc', action='store_true', help='Render info as markdown table')
    planinfo_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planinfo_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan', metavar='PATH')
    planinfo_parser.add_argument('-q', '--quiet', action='store_true', help='Provide parameter file output')
    planinfo_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL', type=valid_url)
    planinfo_parser.set_defaults(func=info_plan)

    planlist_desc = 'List Plans'
    planlist_parser = list_subparsers.add_parser('plan', description=planlist_desc, help=planlist_desc,
                                                 aliases=['plans'])
    planlist_parser.set_defaults(func=list_plan)

    planrestart_desc = 'Restart Plan'
    planrestart_parser = restart_subparsers.add_parser('plan', description=planrestart_desc, help=planrestart_desc)
    planrestart_parser.add_argument('-s', '--soft', action='store_true', help='Do a soft stop')
    planrestart_parser.add_argument('plan', metavar='PLAN')
    planrestart_parser.set_defaults(func=restart_plan)

    plandatacreate_desc = 'Create Cloudinit/Ignition from plan file'
    plandatacreate_epilog = "examples:\n%s" % plandatacreate
    plandatacreate_parser = create_subparsers.add_parser('plan-data', description=plandatacreate_desc,
                                                         help=plandatacreate_desc, epilog=plandatacreate_epilog,
                                                         formatter_class=rawhelp)
    plandatacreate_parser.add_argument('-f', '--inputfile', help='Input Plan file', default='kcli_plan.yml')
    plandatacreate_parser.add_argument('-k', '--skippre', action='store_true', help='Skip pre script')
    plandatacreate_parser.add_argument('--outputdir', '-o', help='Output directory', metavar='OUTPUTDIR')
    plandatacreate_parser.add_argument('-P', '--param', action='append',
                                       help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    plandatacreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    plandatacreate_parser.add_argument('name', metavar='VMNAME', nargs='?', type=valid_fqdn)
    plandatacreate_parser.set_defaults(func=create_plandata)

    plantemplatecreate_desc = 'Create plan template'
    plantemplatecreate_epilog = "examples:\n%s" % plantemplatecreate
    plantemplatecreate_parser = create_subparsers.add_parser('plan-template', description=plantemplatecreate_desc,
                                                             help=plantemplatecreate_desc,
                                                             epilog=plantemplatecreate_epilog, formatter_class=rawhelp)
    plantemplatecreate_parser.add_argument('-P', '--param', action='append',
                                           help='Define parameter for rendering (can specify multiple)',
                                           metavar='PARAM')
    plantemplatecreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    plantemplatecreate_parser.add_argument('-x', '--skipfiles', action='store_true', help='Skip files in assets')
    plantemplatecreate_parser.add_argument('-y', '--skipscripts', action='store_true', help='Skip scripts in assets')
    plantemplatecreate_parser.add_argument('directory', metavar='DIR')
    plantemplatecreate_parser.set_defaults(func=create_plantemplate)

    planrevert_desc = 'Revert Snapshot Of Plan'
    planrevert_parser = revert_subparsers.add_parser('plan-snapshot', description=planrevert_desc, help=planrevert_desc,
                                                     aliases=['plan'])
    planrevert_parser.add_argument('-p', '--plan', help='Plan name', required=True, metavar='PLANNAME')
    planrevert_parser.add_argument('snapshot', metavar='SNAPSHOT')
    planrevert_parser.set_defaults(func=revert_snapshot_plan)

    plansnapshotcreate_desc = 'Create Plan Snapshot'
    plansnapshotcreate_parser = create_subparsers.add_parser('plan-snapshot', description=plansnapshotcreate_desc,
                                                             help=plansnapshotcreate_desc)

    plansnapshotcreate_parser.add_argument('-p', '--plan', help='plan name', required=True, metavar='PLAN')
    plansnapshotcreate_parser.add_argument('snapshot', metavar='SNAPSHOT')
    plansnapshotcreate_parser.set_defaults(func=create_snapshot_plan)

    planstart_desc = 'Start Plan'
    planstart_parser = start_subparsers.add_parser('plan', description=planstart_desc, help=planstart_desc)
    planstart_parser.add_argument('plan', metavar='PLAN')
    planstart_parser.set_defaults(func=start_plan)

    planstop_desc = 'Stop Plan'
    planstop_parser = stop_subparsers.add_parser('plan', description=planstop_desc, help=planstop_desc)
    planstop_parser.add_argument('-s', '--soft', action='store_true', help='Do a soft stop')
    planstop_parser.add_argument('plan', metavar='PLAN')
    planstop_parser.set_defaults(func=stop_plan)

    planupdate_desc = 'Update Plan'
    planupdate_parser = update_subparsers.add_parser('plan', description=planupdate_desc, help=planupdate_desc)
    planupdate_parser.add_argument('--autostart', action='store_true', help='Set autostart for vms of the plan')
    planupdate_parser.add_argument('--noautostart', action='store_true', help='Remove autostart for vms of the plan')
    planupdate_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL', type=valid_url)
    planupdate_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan',
                                   metavar='PATH')
    planupdate_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    planupdate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planupdate_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    planupdate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    planupdate_parser.add_argument('-r', '--remediate', action='store_true', help='Remediate files in the vms')
    planupdate_parser.add_argument('plan', metavar='PLAN')
    planupdate_parser.set_defaults(func=update_plan)

    playbookcreate_desc = 'Create playbook from plan'
    playbookcreate_parser = create_subparsers.add_parser('playbook', description=playbookcreate_desc,
                                                         help=playbookcreate_desc)
    playbookcreate_parser.add_argument('-f', '--inputfile', help='Input Plan/File', default='kcli_plan.yml')
    playbookcreate_parser.add_argument('-P', '--param', action='append',
                                       help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    playbookcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    playbookcreate_parser.add_argument('-s', '--store', action='store_true', help="Store results in files")
    playbookcreate_parser.set_defaults(func=create_playbook)

    poolcreate_desc = 'Create Pool'
    poolcreate_parser = create_subparsers.add_parser('pool', description=poolcreate_desc, help=poolcreate_desc)
    poolcreate_parser.add_argument('-f', '--full', action='store_true')
    poolcreate_parser.add_argument('-t', '--pooltype', help='Type of the pool', choices=('dir', 'lvm', 'zfs'),
                                   default='dir')
    poolcreate_parser.add_argument('-p', '--path', help='Path of the pool', metavar='PATH')
    poolcreate_parser.add_argument('--thinpool', help='Existing thin pool to use with lvm', metavar='THINPOOL')
    poolcreate_parser.add_argument('pool')
    poolcreate_parser.set_defaults(func=create_pool)

    pooldelete_desc = 'Delete Pool'
    pooldelete_parser = delete_subparsers.add_parser('pool', description=pooldelete_desc, help=pooldelete_desc)
    pooldelete_parser.add_argument('-d', '--delete', action='store_true')
    pooldelete_parser.add_argument('-f', '--full', action='store_true')
    pooldelete_parser.add_argument('-p', '--path', help='Path of the pool', metavar='PATH')
    pooldelete_parser.add_argument('--thinpool', help='Existing thin pool to use with lvm', metavar='THINPOOL')
    pooldelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    pooldelete_parser.add_argument('pool')
    pooldelete_parser.set_defaults(func=delete_pool)

    poollist_desc = 'List Pools'
    poollist_parser = list_subparsers.add_parser('pool', description=poollist_desc, help=poollist_desc,
                                                 aliases=['pools'])
    poollist_parser.add_argument('--short', action='store_true')
    poollist_parser.set_defaults(func=list_pool)

    profiledelete_desc = 'Delete Profile'
    profiledelete_help = "Profile to delete"
    profiledelete_parser = argparse.ArgumentParser(add_help=False)
    profiledelete_parser.add_argument('profile', help=profiledelete_help, metavar='PROFILE')
    profiledelete_parser.set_defaults(func=delete_profile)
    delete_subparsers.add_parser('profile', parents=[profiledelete_parser], description=profiledelete_desc,
                                 help=profiledelete_desc)

    productcreate_desc = 'Create Product'
    productcreate_parser = create_subparsers.add_parser('product', description=productcreate_desc,
                                                        help=productcreate_desc)
    productcreate_parser.add_argument('-g', '--group', help='Group to use as a name during deployment', metavar='GROUP')
    productcreate_parser.add_argument('-l', '--latest', action='store_true', help='Grab latest version of the plans')
    productcreate_parser.add_argument('-P', '--param', action='append',
                                      help='Define parameter for rendering within scripts.'
                                      'Can be repeated several times', metavar='PARAM')
    productcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    productcreate_parser.add_argument('-r', '--repo',
                                      help='Repo to use, if deploying a product present in several repos',
                                      metavar='REPO')
    productcreate_parser.add_argument('product', metavar='PRODUCT')
    productcreate_parser.set_defaults(func=create_product)

    productinfo_desc = 'Info Of Product'
    productinfo_epilog = "examples:\n%s" % productinfo
    productinfo_parser = argparse.ArgumentParser(add_help=False)
    productinfo_parser.set_defaults(func=info_product)
    productinfo_parser.add_argument('-g', '--group', help='Only Display products of the indicated group',
                                    metavar='GROUP')
    productinfo_parser.add_argument('-r', '--repo', help='Only Display products of the indicated repository',
                                    metavar='REPO')
    productinfo_parser.add_argument('product', metavar='PRODUCT')
    info_subparsers.add_parser('product', parents=[productinfo_parser], description=productinfo_desc,
                               help=productinfo_desc,
                               epilog=productinfo_epilog, formatter_class=rawhelp)

    productlist_desc = 'List Products'
    productlist_parser = list_subparsers.add_parser('product', description=productlist_desc, help=productlist_desc,
                                                    aliases=['products'])
    productlist_parser.add_argument('-g', '--group', help='Only Display products of the indicated group',
                                    metavar='GROUP')
    productlist_parser.add_argument('-r', '--repo', help='Only Display products of the indicated repository',
                                    metavar='REPO')
    productlist_parser.add_argument('-s', '--search', help='Search matching products')
    productlist_parser.set_defaults(func=list_product)

    repocreate_desc = 'Create Repo'
    repocreate_epilog = "examples:\n%s" % repocreate
    repocreate_parser = create_subparsers.add_parser('repo', description=repocreate_desc, help=repocreate_desc,
                                                     epilog=repocreate_epilog,
                                                     formatter_class=rawhelp)
    repocreate_parser.add_argument('-u', '--url', help='URL of the repo', metavar='URL', type=valid_url)
    repocreate_parser.add_argument('repo')
    repocreate_parser.set_defaults(func=create_repo)

    repodelete_desc = 'Delete Repo'
    repodelete_parser = delete_subparsers.add_parser('repo', description=repodelete_desc, help=repodelete_desc)
    repodelete_parser.add_argument('repo')
    repodelete_parser.set_defaults(func=delete_repo)

    repolist_desc = 'List Repos'
    repolist_parser = list_subparsers.add_parser('repo', description=repolist_desc, help=repolist_desc,
                                                 aliases=['repos'])
    repolist_parser.set_defaults(func=list_repo)

    repoupdate_desc = 'Update Repo'
    repoupdate_parser = update_subparsers.add_parser('repo', description=repoupdate_desc, help=repoupdate_desc)
    repoupdate_parser.add_argument('repo')
    repoupdate_parser.set_defaults(func=update_repo)

    coreosinstallerdownload_desc = 'Download Coreos Installer'
    coreosinstallerdownload_parser = argparse.ArgumentParser(add_help=False)
    coreosinstallerdownload_parser.add_argument('-P', '--param', action='append',
                                                help='Define parameter for rendering (can specify multiple)',
                                                metavar='PARAM')
    coreosinstallerdownload_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    coreosinstallerdownload_parser.set_defaults(func=download_coreos_installer)
    download_subparsers.add_parser('coreos-installer', parents=[coreosinstallerdownload_parser],
                                   description=coreosinstallerdownload_desc,
                                   help=coreosinstallerdownload_desc)

    imagedownload_desc = 'Download Cloud Image'
    imagedownload_help = "Image to download. Choose between \n%s" % '\n'.join(IMAGES.keys())
    imagedownload_parser = argparse.ArgumentParser(add_help=False)
    imagedownload_parser.add_argument('-a', '--arch', help='Target arch', choices=['x86_64', 'aarch64'],
                                      default='x86_64')
    imagedownload_parser.add_argument('-c', '--cmd', help='Extra command to launch after downloading', metavar='CMD')
    imagedownload_parser.add_argument('-o', '--openstack', help='Use openstack variant (kvm specific)',
                                      action='store_true')
    imagedownload_parser.add_argument('-p', '--pool', help='Pool to use. Defaults to default', metavar='POOL')
    imagedownload_parser.add_argument('-u', '--url', help='Url to use', metavar='URL', type=valid_url)
    imagedownload_parser.add_argument('--size', help='Disk size (kubevirt specific)', type=int, metavar='SIZE')
    imagedownload_parser.add_argument('-s', '--skip-profile', help='Skip Profile update', action='store_true')
    imagedownload_parser.add_argument('image', help=imagedownload_help, metavar='IMAGE')
    imagedownload_parser.set_defaults(func=download_image)
    download_subparsers.add_parser('image', parents=[imagedownload_parser], description=imagedownload_desc,
                                   help=imagedownload_desc)

    isodownload_desc = 'Download Iso'
    isodownload_help = "Iso name"
    isodownload_parser = argparse.ArgumentParser(add_help=False)
    isodownload_parser.add_argument('-p', '--pool', help='Pool to use. Defaults to default', metavar='POOL')
    isodownload_parser.add_argument('-u', '--url', help='Url to use', metavar='URL', required=True, type=valid_url)
    isodownload_parser.add_argument('iso', help=isodownload_help, metavar='ISO', nargs='?')
    isodownload_parser.set_defaults(func=download_iso)
    download_subparsers.add_parser('iso', parents=[isodownload_parser], description=isodownload_desc,
                                   help=isodownload_desc)

    okddownload_desc = 'Download Okd Installer'
    okddownload_parser = argparse.ArgumentParser(add_help=False)
    okddownload_parser.add_argument('-P', '--param', action='append',
                                          help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    okddownload_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    okddownload_parser.set_defaults(func=download_okd_installer)
    download_subparsers.add_parser('okd-installer', parents=[okddownload_parser],
                                   description=okddownload_desc,
                                   help=okddownload_desc, aliases=['okd-install'])

    openshiftdownload_desc = 'Download Openshift Installer'
    openshiftdownload_parser = argparse.ArgumentParser(add_help=False)
    openshiftdownload_parser.add_argument('-P', '--param', action='append',
                                          help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    openshiftdownload_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    openshiftdownload_parser.set_defaults(func=download_openshift_installer)
    download_subparsers.add_parser('openshift-installer', parents=[openshiftdownload_parser],
                                   description=openshiftdownload_desc,
                                   help=openshiftdownload_desc, aliases=['openshift-install'])

    helmdownload_desc = 'Download Helm'
    helmdownload_parser = argparse.ArgumentParser(add_help=False)
    helmdownload_parser.add_argument('-P', '--param', action='append',
                                     help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    helmdownload_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    helmdownload_parser.set_defaults(func=download_helm)
    download_subparsers.add_parser('helm', parents=[helmdownload_parser],
                                   description=helmdownload_desc,
                                   help=helmdownload_desc)

    kubectldownload_desc = 'Download Kubectl'
    kubectldownload_parser = argparse.ArgumentParser(add_help=False)
    kubectldownload_parser.add_argument('-P', '--param', action='append',
                                        help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    kubectldownload_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    kubectldownload_parser.set_defaults(func=download_kubectl)
    download_subparsers.add_parser('kubectl', parents=[kubectldownload_parser],
                                   description=kubectldownload_desc,
                                   help=kubectldownload_desc)

    ocdownload_desc = 'Download Oc'
    ocdownload_parser = argparse.ArgumentParser(add_help=False)
    ocdownload_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    ocdownload_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    ocdownload_parser.set_defaults(func=download_oc)
    download_subparsers.add_parser('oc', parents=[ocdownload_parser],
                                   description=ocdownload_desc,
                                   help=ocdownload_desc)

    plandownload_desc = 'Download Plan'
    plandownload_parser = argparse.ArgumentParser(add_help=False)
    plandownload_parser.add_argument('-u', '--url', help='Url to use', metavar='URL', required=True, type=valid_url)
    plandownload_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plandownload_parser.set_defaults(func=download_plan)
    download_subparsers.add_parser('plan', parents=[plandownload_parser], description=plandownload_desc,
                                   help=plandownload_desc)

    imagelist_desc = 'List Images'
    imagelist_parser = list_subparsers.add_parser('image', description=imagelist_desc, help=imagelist_desc,
                                                  aliases=['images'])
    imagelist_parser.set_defaults(func=list_image)

    vmcreate_desc = 'Create Vm'
    vmcreate_epilog = "examples:\n%s" % vmcreate
    vmcreate_parser = argparse.ArgumentParser(add_help=False)
    vmcreate_parser.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    vmcreate_parser.add_argument('--console', help='Directly switch to console after creation', action='store_true')
    vmcreate_parser.add_argument('-c', '--count', help='How many vms to create', type=int, default=1, metavar='COUNT')
    vmcreate_parser.add_argument('-i', '--image', help='Image to use', metavar='IMAGE')
    vmcreate_parser.add_argument('--profilefile', help='File to load profiles from', metavar='PROFILEFILE')
    vmcreate_parser.add_argument('-P', '--param', action='append',
                                 help='specify parameter or keyword for rendering (multiple can be specified)',
                                 metavar='PARAM')
    vmcreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    vmcreate_parser.add_argument('-s', '--serial', help='Directly switch to serial console after creation',
                                 action='store_true')
    vmcreate_parser.add_argument('-w', '--wait', action='store_true', help='Wait for cloudinit to finish')
    vmcreate_parser.add_argument('name', metavar='VMNAME', nargs='?', type=valid_fqdn)
    vmcreate_parser.set_defaults(func=create_vm)
    create_subparsers.add_parser('vm', parents=[vmcreate_parser], description=vmcreate_desc, help=vmcreate_desc,
                                 epilog=vmcreate_epilog, formatter_class=rawhelp)

    vmdelete_desc = 'Delete Vm'
    vmdelete_parser = argparse.ArgumentParser(add_help=False)
    vmdelete_parser.add_argument('-c', '--count', help='How many vms to delete', type=int, default=1, metavar='COUNT')
    vmdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    vmdelete_parser.add_argument('-s', '--snapshots', action='store_true', help='Remove snapshots if needed')
    vmdelete_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmdelete_parser.set_defaults(func=delete_vm)
    delete_subparsers.add_parser('vm', parents=[vmdelete_parser], description=vmdelete_desc, help=vmdelete_desc)

    vmdatacreate_desc = 'Create Cloudinit/Ignition for a single vm'
    vmdatacreate_epilog = "examples:\n%s" % vmdatacreate
    vmdatacreate_parser = create_subparsers.add_parser('vm-data', description=vmdatacreate_desc,
                                                       help=vmdatacreate_desc, epilog=vmdatacreate_epilog,
                                                       formatter_class=rawhelp)
    vmdatacreate_parser.add_argument('-i', '--image', help='Image to use', metavar='IMAGE')
    vmdatacreate_parser.add_argument('-P', '--param', action='append',
                                     help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    vmdatacreate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    vmdatacreate_parser.add_argument('name', metavar='VMNAME', nargs='?', type=valid_fqdn)
    vmdatacreate_parser.set_defaults(func=create_vmdata)

    vmdiskadd_desc = 'Add Disk To Vm'
    diskcreate_epilog = "examples:\n%s" % diskcreate
    vmdiskadd_parser = argparse.ArgumentParser(add_help=False)
    vmdiskadd_parser.add_argument('-s', '--size', type=int, help='Size of the disk to add, in GB', metavar='SIZE',
                                  default=10)
    vmdiskadd_parser.add_argument('-i', '--image', help='Name or Path of a Image', metavar='IMAGE')
    vmdiskadd_parser.add_argument('--interface', default='virtio', help='Disk Interface. Defaults to virtio',
                                  metavar='INTERFACE')
    vmdiskadd_parser.add_argument('-n', '--novm', action='store_true', help='Dont attach to any vm')
    vmdiskadd_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskadd_parser.add_argument('-P', '--param', action='append',
                                  help='specify parameter or keyword for rendering (can specify multiple)',
                                  metavar='PARAM')
    vmdiskadd_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    vmdiskadd_parser.add_argument('name', metavar='VMNAME')
    vmdiskadd_parser.set_defaults(func=create_vmdisk)
    create_subparsers.add_parser('vm-disk', parents=[vmdiskadd_parser], description=vmdiskadd_desc, help=vmdiskadd_desc,
                                 aliases=['disk'], epilog=diskcreate_epilog,
                                 formatter_class=rawhelp)

    vmdiskdelete_desc = 'Delete Vm Disk'
    diskdelete_epilog = "examples:\n%s" % diskdelete
    vmdiskdelete_parser = argparse.ArgumentParser(add_help=False)
    vmdiskdelete_parser.add_argument('-n', '--novm', action='store_true', help='Dont try to locate vm')
    vmdiskdelete_parser.add_argument('--vm', help='Name of the vm', metavar='VMNAME')
    vmdiskdelete_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    vmdiskdelete_parser.add_argument('diskname', metavar='DISKNAME')
    vmdiskdelete_parser.set_defaults(func=delete_vmdisk)
    delete_subparsers.add_parser('vm-disk', parents=[vmdiskdelete_parser], description=vmdiskdelete_desc,
                                 aliases=['disk'], help=vmdiskdelete_desc, epilog=diskdelete_epilog,
                                 formatter_class=rawhelp)

    vmdisklist_desc = 'List All Vm Disks'
    vmdisklist_parser = argparse.ArgumentParser(add_help=False)
    vmdisklist_parser.set_defaults(func=list_vmdisk)
    list_subparsers.add_parser('disk', parents=[vmdisklist_parser], description=vmdisklist_desc,
                               help=vmdisklist_desc, aliases=['disks'])

    vminfo_desc = 'Info Of Vms'
    vminfo_parser = argparse.ArgumentParser(add_help=False)
    vminfo_parser.add_argument('-f', '--fields', help='Display Corresponding list of fields,'
                               'separated by a comma', metavar='FIELDS')
    vminfo_parser.add_argument('-o', '--output', choices=['plain', 'yaml'], help='Format of the output')
    vminfo_parser.add_argument('-v', '--values', action='store_true', help='Only report values')
    vminfo_parser.add_argument('names', help='VMNAMES', nargs='*')
    vminfo_parser.set_defaults(func=info_vm)
    info_subparsers.add_parser('vm', parents=[vminfo_parser], description=vminfo_desc, help=vminfo_desc)

    vmlist_desc = 'List Vms'
    vmlist_parser = argparse.ArgumentParser(add_help=False)
    vmlist_parser.add_argument('--filters', choices=('up', 'down'))
    vmlist_parser.set_defaults(func=list_vm)
    list_subparsers.add_parser('vm', parents=[vmlist_parser], description=vmlist_desc, help=vmlist_desc,
                               aliases=['vms'])

    create_vmnic_desc = 'Add Nic To Vm'
    create_vmnic_epilog = "examples:\n%s" % niccreate
    create_vmnic_parser = argparse.ArgumentParser(add_help=False)
    create_vmnic_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    create_vmnic_parser.add_argument('name', metavar='VMNAME')
    create_vmnic_parser.set_defaults(func=create_vmnic)
    create_subparsers.add_parser('vm-nic', parents=[create_vmnic_parser], description=create_vmnic_desc,
                                 help=create_vmnic_desc, aliases=['nic'],
                                 epilog=create_vmnic_epilog, formatter_class=rawhelp)

    delete_vmnic_desc = 'Delete Nic From vm'
    delete_vmnic_epilog = "examples:\n%s" % nicdelete
    delete_vmnic_parser = argparse.ArgumentParser(add_help=False)
    delete_vmnic_parser.add_argument('-i', '--interface', help='Interface name', metavar='INTERFACE')
    delete_vmnic_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    delete_vmnic_parser.add_argument('name', metavar='VMNAME')
    delete_vmnic_parser.set_defaults(func=delete_vmnic)
    delete_subparsers.add_parser('vm-nic', parents=[delete_vmnic_parser], description=delete_vmnic_desc,
                                 help=delete_vmnic_desc, aliases=['nic'],
                                 epilog=delete_vmnic_epilog, formatter_class=rawhelp)

    vmrestart_desc = 'Restart Vms'
    vmrestart_parser = restart_subparsers.add_parser('vm', description=vmrestart_desc, help=vmrestart_desc)
    vmrestart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmrestart_parser.set_defaults(func=restart_vm)

    vmsnapshotcreate_desc = 'Create Snapshot Of Vm'
    vmsnapshotcreate_parser = create_subparsers.add_parser('vm-snapshot', description=vmsnapshotcreate_desc,
                                                           help=vmsnapshotcreate_desc, aliases=['snapshot'])
    vmsnapshotcreate_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotcreate_parser.add_argument('snapshot')
    vmsnapshotcreate_parser.set_defaults(func=snapshotcreate_vm)

    vmsnapshotdelete_desc = 'Delete Snapshot Of Vm'
    vmsnapshotdelete_parser = delete_subparsers.add_parser('vm-snapshot', description=vmsnapshotdelete_desc,
                                                           help=vmsnapshotdelete_desc)
    vmsnapshotdelete_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotdelete_parser.add_argument('snapshot')
    vmsnapshotdelete_parser.set_defaults(func=snapshotdelete_vm)

    vmsnapshotlist_desc = 'List Snapshots Of Vm'
    vmsnapshotlist_parser = list_subparsers.add_parser('vm-snapshot', description=vmsnapshotlist_desc,
                                                       help=vmsnapshotlist_desc, aliases=['vm-snapshots'])
    vmsnapshotlist_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotlist_parser.set_defaults(func=snapshotlist_vm)

    vmsnapshotrevert_desc = 'Revert Snapshot Of Vm'
    vmsnapshotrevert_parser = revert_subparsers.add_parser('vm-snapshot', description=vmsnapshotrevert_desc,
                                                           help=vmsnapshotrevert_desc, aliases=['vm'])
    vmsnapshotrevert_parser.add_argument('-n', '--name', help='vm name', required=True, metavar='VMNAME')
    vmsnapshotrevert_parser.add_argument('snapshot')
    vmsnapshotrevert_parser.set_defaults(func=snapshotrevert_vm)

    vmstart_desc = 'Start Vms'
    vmstart_parser = argparse.ArgumentParser(add_help=False)
    vmstart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstart_parser.set_defaults(func=start_vm)
    start_subparsers.add_parser('vm', parents=[vmstart_parser], description=vmstart_desc, help=vmstart_desc)

    vmstop_desc = 'Stop Vms'
    vmstop_parser = argparse.ArgumentParser(add_help=False)
    vmstop_parser.add_argument('-s', '--soft', action='store_true', help='Do a soft stop')
    vmstop_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstop_parser.set_defaults(func=stop_vm)
    stop_subparsers.add_parser('vm', parents=[vmstop_parser], description=vmstop_desc, help=vmstop_desc)

    vmupdate_desc = 'Update Vm\'s Ip, Memory Or Numcpus'
    vmupdate_parser = update_subparsers.add_parser('vm', description=vmupdate_desc, help=vmupdate_desc)
    vmupdate_parser.add_argument('-P', '--param', action='append',
                                 help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    vmupdate_parser.add_argument('--paramfile', '--pf', help='Parameters file', metavar='PARAMFILE')
    vmupdate_parser.add_argument('names', help='VMNAMES', nargs='*')
    vmupdate_parser.set_defaults(func=update_vm)

    argcomplete.autocomplete(parser)
    if len(sys.argv) == 1 or (len(sys.argv) == 3 and sys.argv[1] == '-C'):
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()
    if not hasattr(args, 'func'):
        for attr in dir(args):
            if attr.startswith('subcommand_') and getattr(args, attr) is None:
                split = attr.split('_')
                if len(split) == 2:
                    subcommand = split[1]
                    get_subparser_print_help(parser, subcommand)
                elif len(split) == 3:
                    subcommand = split[1]
                    subsubcommand = split[2]
                    subparser = get_subparser(parser, subcommand)
                    get_subparser_print_help(subparser, subsubcommand)
                sys.exit(0)
        sys.exit(0)
    elif args.func.__name__ == 'vmcreate' and args.client is not None and ',' in args.client:
        args.client = random.choice(args.client.split(','))
        pprint(f"Selecting {args.client} for creation")
    args.func(args)


if __name__ == '__main__':
    cli()
