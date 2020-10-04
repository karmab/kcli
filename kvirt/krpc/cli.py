#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# coding=utf-8

import atexit
import grpc
from kvirt.krpc import kcli_pb2
from kvirt.krpc import kcli_pb2_grpc
from kvirt.krpc.kcli_pb2 import empty


from distutils.spawn import find_executable
from kvirt.examples import hostcreate, _list, plancreate, planinfo, productinfo, repocreate, start
from kvirt.examples import kubegenericcreate, kubeopenshiftcreate
from kvirt.examples import dnscreate, diskcreate, diskdelete, vmcreate, vmconsole, vmexport, niccreate, nicdelete
from kvirt.containerconfig import Kcontainerconfig
from kvirt.defaults import IMAGES, VERSION
from kvirt import version
from prettytable import PrettyTable
import argcomplete
import argparse
from kvirt.krpc import commoncli as common
from kvirt import nameutils
import os
import random
import requests
import sys


class Kconfig():
    def __init__(self, client=None, debug=None, region=None, zone=None, namespace=None):
        self.k = kcli_pb2_grpc.KcliStub(channel)
        self.config = kcli_pb2_grpc.KconfigStub(channel)
        self.baseconfig = self.config
        clientinfo = self.config.get_config(empty())
        currentclient = clientinfo.client
        self.client = clientinfo.client
        self.extraclients = [c for c in clientinfo.extraclients]
        if client is not None:
            result = self.baseconfig.switch_host(kcli_pb2.client(client=client))
            if result.result != 'success':
                common.pprint("Couldn't switch to client %s..." % client, color='red')
                os._exit(1)
            self.client = client
            self.extraclients = []
            atexit.register(finalswitch, self.baseconfig, currentclient)


def finalswitch(baseconfig, client):
    result = baseconfig.switch_host(kcli_pb2.client(client=client))
    if result.result != 'success':
        common.pprint("Couldn't switch to client %s..." % client, color='red')
        os._exit(0)


def valid_fqdn(name):
    if name is not None and '/' in name:
        msg = "Vm name can't include /"
        raise argparse.ArgumentTypeError(msg)
    return name


def valid_cluster(name):
    if name is not None:
        if '/' in name:
            msg = "Cluster name can't include /"
            raise argparse.ArgumentTypeError(msg)
        elif '-' in name:
            msg = "Cluster name can't include -"
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
    git_version = open('%s/git' % versiondir).read().rstrip() if os.path.exists('%s/git' % versiondir) else 'N/A'
    full_version += " commit: %s" % git_version
    update = 'N/A'
    if git_version != 'N/A':
        try:
            upstream_version = requests.get("https://api.github.com/repos/karmab/kcli/commits/master").json()['sha'][:7]
            update = True if upstream_version != git_version else False
        except:
            pass
    full_version += " Available Updates: %s" % update
    print(full_version)


def start_vm(args):
    """Start vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    codes = []
    for name in names:
        common.pprint("Starting vm %s..." % name)
        result = k.start(kcli_pb2.vm(name=name))
        code = common.handle_response(result, name, element='', action='started')
        codes.append(code)
    os._exit(1 if 1 in codes else 0)


def start_container(args):
    """Start containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    for name in names:
        common.pprint("Starting container %s..." % name)
        config.config.start_container(kcli_pb2.container(container=name))


def stop_vm(args):
    """Stop vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    if config.extraclients:
        ks = config.extraclients
        ks.update({config.client: config.k})
    else:
        ks = {config.client: config.k}
    codes = []
    for cli in ks:
        k = ks[cli]
        for name in names:
            common.pprint("Stopping vm %s in %s..." % (name, cli))
            result = k.stop(kcli_pb2.vm(name=name))
            code = common.handle_response(result, name, element='', action='stopped')
            codes.append(code)
    os._exit(1 if 1 in codes else 0)


def stop_container(args):
    """Stop containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    if config.extraclients:
        ks = config.extraclients
        ks.update({config.client: config.k})
    else:
        ks = {config.client: config.k}
    for cli in ks:
        for name in names:
            common.pprint("Stopping container %s in %s..." % (name, cli))
            config.config.stop_container(kcli_pb2.container(container=name))


def restart_vm(args):
    """Restart vms"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    codes = []
    for name in names:
        common.pprint("Restarting vm %s..." % name)
        result = k.restart(kcli_pb2.vm(name=name))
        code = common.handle_response(result, name, element='', action='restarted')
        codes.append(code)
    os._exit(1 if 1 in codes else 0)


def restart_container(args):
    """Restart containers"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    for name in names:
        common.pprint("Restarting container %s..." % name)
        config.config.stop_container(kcli_pb2.container(container=name))
        config.config.start_container(kcli_pb2.container(container=name))


def console_vm(args):
    """Vnc/Spice/Serial Vm console"""
    serial = args.serial
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    name = k.get_lastvm(kcli_pb2.client(client=config.client)).name if args.name is None else args.name
    if serial:
        cmd = k.serial_console(kcli_pb2.vm(name=name)).cmd
        os.system(cmd)
    else:
        cmd = k.console(kcli_pb2.vm(name=name)).cmd
        os.popen("remote-viewer %s &" % cmd)


def console_container(args):
    """Container console"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    name = k.get_lastvm(kcli_pb2.client(client=config.client)).name if args.name is None else args.name
    cont = Kcontainerconfig(config, client=args.containerclient).cont
    cont.console_container(name)
    return


def delete_vm(args):
    """Delete vm"""
    snapshots = args.snapshots
    yes_top = args.yes_top
    yes = args.yes
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        names = args.names
        if not names:
            common.pprint("Can't delete vms on multiple hosts without specifying their names", color='red')
            os._exit(1)
    else:
        allclients = {config.client: config.k}
        names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    for cli in sorted(allclients):
        k = allclients[cli]
        if not yes and not yes_top:
            common.confirm("Are you sure?")
        codes = []
        for name in names:
            common.pprint("Deleting vm %s on %s" % (name, cli))
            # dnsclient, domain = k.dnsinfo(name)
            dnsclient, domain = None, None
            result = k.delete(kcli_pb2.vm(name=name, snapshots=snapshots))
            if result.result == 'success':
                common.pprint("%s deleted" % name)
                codes.append(0)
            else:
                reason = result.reason
                common.pprint("Could not delete %s because %s" % (name, reason), color='red')
                codes.append(1)
            if dnsclient is not None and domain is not None:
                z = Kconfig(client=dnsclient).k
                z.delete_dns(name, domain)
    os._exit(1 if 1 in codes else 0)


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
        for name in names:
            common.pprint("Deleting container %s on %s" % (name, cli))
            config.config.delete_container(kcli_pb2.container(container=name))
    os._exit(1 if 1 in codes else 0)


def download_image(args):
    """Download Image"""
    pool = args.pool
    image = args.image
    cmd = args.cmd
    url = args.url
    update_profile = not args.skip_profile
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(pool=pool, image=image, download=True, cmd=cmd, url=url, update_profile=update_profile)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def delete_image(args):
    images = args.images
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
            # clientprofile = "%s_%s" % (cli, image)
            common.pprint("Deleting image %s on %s" % (image, cli))
            result = k.delete_image(kcli_pb2.image(image=image))
            # if clientprofile in config.profiles and 'image' in config.profiles[clientprofile]:
            #     profileimage = config.profiles[clientprofile]['image']
            #     config.delete_profile(clientprofile, quiet=True)
            #     result = k.delete_image(kcli_pb2.image(image=profileimage))
            # else:
            #     result = k.delete_image(kcli_pb2.image(image=image))
            if result.result == 'success':
                common.pprint("%s deleted" % image)
                codes.append(0)
            else:
                reason = result.reason
                common.pprint("Could not delete image %s because %s" % (image, reason), color='red')
                codes.append(1)
    os._exit(1 if 1 in codes else 0)


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
    common.pprint("Deleting on %s" % baseconfig.client)
    result = baseconfig.baseconfig.delete_profile(kcli_pb2.profile(name=profile))
    code = common.handle_response(result, profile, element='Profile', action='deleted', client=baseconfig.client)
    return code
    # os._exit(0) if result['result'] == 'success' else os._exit(1)


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
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    if '' in names:
        common.pprint("Last vm not found", color='red')
        os._exit(1)
    for name in names:
        vm = k.info(kcli_pb2.vm(name=name, debug=args.debug))
        if vm is not None:
            data = {}
            data['name'] = vm.name
            data['autostart'] = vm.autostart
            data['status'] = vm.status
            data['creationdate'] = vm.creationdate
            if vm.ip != '':
                data['ip'] = vm.ip
            data['image'] = vm.image
            data['cpus'] = vm.cpus
            data['memory'] = vm.memory
            data['user'] = vm.user
            data['plan'] = vm.plan
            data['profile'] = vm.profile
            if vm.owner:
                data['owner'] = vm.owner
            if vm.nets:
                data['nets'] = [{'device': net.device, 'mac': net.mac, 'net': net.net, 'type': net.type}
                                for net in vm.nets]
            if vm.disks:
                data['disks'] = [{'device': disk.device, 'format': disk.format, 'path': disk.path, 'size': disk.size,
                                  'type': disk.type} for disk in vm.disks]
            if vm.snapshots:
                data['snapshots'] = [{'snapshot': snapshot.snapshot, 'current': snapshot.current} for
                                     snapshot in vm.snapshots]
            if vm.iso:
                data['iso'] = vm.iso
            if args.debug:
                data['debug'] = vm.debug
            print(common.print_info(data, output=output, fields=fields, values=values, pretty=True))


def enable_host(args):
    """Enable host"""
    host = args.name
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    result = baseconfig.enable_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def disable_host(args):
    """Disable host"""
    host = args.name
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    result = baseconfig.disable_host(host)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def delete_host(args):
    """Delete host"""
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    baseconfig.delete_host(kcli_pb2.client(client=args.name))
    common.pprint("Host %s deleted" % args.name)


def sync_host(args):
    """Handle host"""
    hosts = args.names
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.handle_host(sync=hosts)
    if result['result'] == 'success':
        os._exit(0)
    else:
        os._exit(1)


def list_vm(args):
    """List vms"""
    filters = args.filters
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.client != 'all':
        k = config.k
    if config.extraclients:
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        vms = PrettyTable(["Name", "Host", "Status", "Ips", "Source", "Plan", "Profile"])
        for cli in sorted(allclients):
            for vm in allclients[cli].list(empty()).vms:
                name = vm.name
                status = vm.status
                ip = vm.ip
                source = vm.image
                plan = vm.plan
                profile = vm.profile
                vminfo = [name, cli, status, ip, source, plan, profile]
                if filters:
                    if status == filters:
                        vms.add_row(vminfo)
                else:
                    vms.add_row(vminfo)
        print(vms)
    else:
        vms = PrettyTable(["Name", "Status", "Ips", "Source", "Plan", "Profile"])
        for vm in k.list(empty()).vms:
            name = vm.name
            status = vm.status
            ip = vm.ip
            source = vm.image
            plan = vm.plan
            profile = vm.profile
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
    common.pprint("Listing containers...")
    containers = PrettyTable(["Name", "Status", "Image", "Plan", "Command", "Ports", "Deploy"])
    for container in config.config.list_containers(empty()).containers:
        if filters:
            status = container.status
            if status == filters:
                containers.add_row([container.container, container.status, container.image, container.plan,
                                    container.command, container.ports, container.deploy])
        else:
            containers.add_row([container.container, container.status, container.image, container.plan,
                                container.command, container.ports, container.deploy])
    print(containers)
    return


def profilelist_container(args):
    """List container profiles"""
    short = args.short
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
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
    # if config.type != 'kvm':
    #     common.pprint("Operation not supported on this kind of client.Leaving...", color='red')
    #    os._exit(1)
    common.pprint("Listing container images...")
    images = PrettyTable(["Name"])
    for image in config.config.list_container_images(empty()).images:
        images.add_row([image])
    print(images)
    return


def list_host(args):
    """List hosts"""
    clientstable = PrettyTable(["Client", "Type", "Enabled", "Current"])
    clientstable.align["Client"] = "l"
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    clients = baseconfig.list_hosts(empty()).clients
    for entry in clients:
        client = entry.client
        enabled = entry.enabled
        _type = entry.type
        if entry.current:
            clientstable.add_row([client, _type, enabled, 'X'])
        else:
            clientstable.add_row([client, _type, enabled, ''])
    print(clientstable)
    return


def list_lb(args):
    """List lbs"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    loadbalancers = config.config.list_lbs(empty()).lbs
    if short:
        lbslist = []
        loadbalancerstable = PrettyTable(["Loadbalancer"])
        for lb in loadbalancers:
            lbslist.append(lb.lb)
        for lb in sorted(lbslist):
            loadbalancerstable.add_row([lb])
    else:
        loadbalancerstable = PrettyTable(["LoadBalancer", "IPAddress", "IPProtocol", "Ports", "Target"])
        lbslist = []
        for lb in loadbalancers:
            lbslist.append([lb.lb, lb.ip, lb.protocol, lb.ports, lb.target])
        for lb in sorted(lbslist):
            loadbalancerstable.add_row(lb)
    loadbalancerstable.align["Loadbalancer"] = "l"
    print(loadbalancerstable)
    return


def list_profile(args):
    """List profiles"""
    short = args.short
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    profiles = baseconfig.list_profiles(empty()).profiles
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
        processed_profiles = []
        for profile in profiles:
            newprofile = [profile.name, profile.flavor, profile.pool, profile.disks, profile.image, profile.nets,
                          profile.cloudinit, profile.nested, profile.reservedns, profile.reservehost]
            processed_profiles.append(newprofile)
        for profile in sorted(processed_profiles):
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
    flavorslist = []
    flavors = k.list_flavors(empty()).flavors
    if short:
        flavorstable = PrettyTable(["Flavor"])
        for flavor in flavors:
            flavorslist.append(flavor.flavor)
        for flavor in sorted(flavorslist):
            flavorstable.add_row([flavor])
    else:
        flavorstable = PrettyTable(["Flavor", "Numcpus", "Memory"])
        for flavor in flavors:
            flavorslist.append([flavor.flavor, flavor.numcpus, flavor.memory])
        for flavor in sorted(flavorslist):
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
    for image in k.list_images(empty()).images:
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
    for iso in k.list_isos(empty()).isos:
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
        networks = k.list_networks(empty())
        common.pprint("Listing Networks...")
        if short:
            networkstable = PrettyTable(["Network"])
            networkslist = []
            for network in networks.networks:
                networkslist.append([network.network])
            for network in sorted(networkslist):
                networkstable.add_row(network)
        else:
            networkstable = PrettyTable(["Network", "Type", "Cidr", "Dhcp", "Domain", "Mode"])
            networkslist = []
            for network in networks.networks:
                domain = network.domain if network.domain != '' else 'N/A'
                networkslist.append([network.network, network.type, network.cidr, network.dhcp, domain, network.mode])
            for network in sorted(networkslist):
                networkstable.add_row(network)
        networkstable.align["Network"] = "l"
        print(networkstable)
        return
    else:
        subnets = k.list_subnets(empty())
        common.pprint("Listing Subnets...")
        if short:
            subnetstable = PrettyTable(["Subnets"])
            subnetslist = []
            for subnet in subnets.subnets:
                subnetslist.append(subnet.subnet)
            for subnet in sorted(subnetslist):
                subnetstable.add_row([subnet])
        else:
            subnetstable = PrettyTable(["Subnet", "Az", "Cidr", "Network"])
            subnetslist = []
            for subnet in subnets.subnets:
                network = subnet.network if subnet.network != '' else 'N/A'
                subnetslist.append([subnet.subnet, subnet.az, subnet.cidr, network])
            for subnet in sorted(subnetslist):
                subnetstable.add_row(subnet)
        subnetstable.align["Network"] = "l"
        print(subnetstable)
        return


def list_plan(args):
    """List plans"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                     namespace=args.namespace)
    if config.extraclients:
        plans = PrettyTable(["Plan", "Host", "Vms"])
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        for cli in sorted(allclients):
            currentconfig = Kconfig(client=cli, debug=args.debug, region=args.region, zone=args.zone,
                                    namespace=args.namespace)
            for plan in currentconfig.config.list_plans(empty()).plans:
                planname = plan.name
                planvms = plan.vms
                plans.add_row([planname, cli, planvms])
    else:
        plans = PrettyTable(["Plan", "Vms"])
        for plan in config.config.list_plans(empty()).plans:
            planname = plan.plan
            planvms = plan.vms
            plans.add_row([planname, planvms])
    print(plans)
    return


def list_kube(args):
    """List kube"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if config.extraclients:
        kubestable = PrettyTable(["Cluster", "Type", "Host", "Vms"])
        allclients = config.extraclients.copy()
        allclients.update({config.client: config.k})
        for cli in sorted(allclients):
            currentconfig = Kconfig(client=cli, debug=args.debug, region=args.region, zone=args.zone,
                                    namespace=args.namespace)
            kubes = currentconfig.config.list_kubes(empty())
            for kube in kubes.kubes:
                kubename = kube.kube
                kubetype = kube.type
                kubevms = kube.vms
                kubestable.add_row([kubename, kubetype, cli, kubevms])
    else:
        kubestable = PrettyTable(["Cluster", "Type", "Vms"])
        kubes = config.config.list_kubes(empty())
        for kube in kubes.kubes:
            kubename = kube.kube
            kubetype = kube.type
            kubevms = kube.vms
            kubestable.add_row([kubename, kubetype, kubevms])
    print(kubestable)
    return


def list_pool(args):
    """List pools"""
    short = args.short
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    pools = k.list_pools(empty()).pools
    poolslist = []
    if short:
        poolstable = PrettyTable(["Pool"])
        for pool in pools:
            poolslist.append([pool.pool])
        for pool in sorted(poolslist):
            poolstable.add_row(pool)
    else:
        poolstable = PrettyTable(["Pool", "Path"])
        for pool in pools:
            poolslist.append([pool.pool, pool.path])
        for pool in sorted(poolslist):
            poolstable.add_row(pool)
    poolstable.align["Pool"] = "l"
    print(poolstable)
    return


def list_product(args):
    """List products"""
    group = args.group
    repo = args.repo
    search = args.search
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    productslist = []
    productsinfo = baseconfig.list_products(kcli_pb2.product(repo=repo, group=group)).products
    for prod in productsinfo:
        newproduct = {'name': prod.product, 'repo': prod.repo, 'group': prod.group, 'numvms': prod.numvms,
                      'memory': prod.memory, 'description': prod.description}
        productslist.append(newproduct)
    if search is not None:
        baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
        products = PrettyTable(["Repo", "Product", "Group", "Description", "Numvms", "Memory"])
        products.align["Repo"] = "l"
        # productsinfo = baseconfig.list_products(kcli_pb2.product(repo=repo)).products
        for prod in sorted(productslist, key=lambda x: (x['repo'], x['group'], x['name'])):
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
        # productsinfo = baseconfig.list_products(group=group, repo=repo)
        for product in sorted(productslist, key=lambda x: (x['repo'], x['group'], x['name'])):
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
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    repos = PrettyTable(["Repo", "Url"])
    repos.align["Repo"] = "l"
    reposlist = []
    for repo in baseconfig.list_repos(empty()).repos:
        reposlist.append([repo.repo, repo.url])
    for repo in sorted(reposlist):
        repos.add_row(repo)
    print(repos)
    return


def list_vmdisk(args):
    """List vm disks"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Listing disks...")
    diskstable = PrettyTable(["Name", "Pool", "Path"])
    diskstable.align["Name"] = "l"
    finaldisks = []
    disks = k.list_disks(empty())
    for disk in disks.disks:
        path = disks.disk.path
        pool = disks.disk.pool
        finaldisks.append([disk, pool, path])
    for disk in sorted(finaldisks):
        diskstable.add_row(disk)
    print(diskstable)
    return


def create_vm(args):
    """Create vms"""
    name = args.name
    image = args.image
    profile = args.profile
    # profilefile = args.profilefile
    overrides = common.get_overrides(paramfile=args.paramfile, param=args.param)
    wait = args.wait
    customprofile = {}
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    for key in overrides:
        if key in vars(config) and vars(config)[key] is not None and type(overrides[key]) != type(vars(config)[key]):
            key_type = str(type(vars(config)[key]))
            common.pprint("The provided parameter %s has a wrong type, it should be %s" % (key, key_type), color='red')
            os._exit(1)
    wait = False
    vmfiles = []
    if 'files' in overrides:
        for _fil in overrides['files']:
            if isinstance(_fil, dict):
                origin = _fil.get('origin')
                if origin is None:
                    common.pprint("Missing origin field in files section. Leaving")
                    os._exit(1)
            else:
                origin = _fil
            with open(origin) as f:
                content = f.read()
                vmfiles.append(kcli_pb2.vmfile(origin=origin, content=content))
    if 'scripts' in overrides:
        for _fil in overrides['scripts']:
            origin = os.path.basename(_fil)
            with open(_fil) as f:
                content = f.read()
                vmfiles.append(kcli_pb2.vmfile(origin=origin, content=content))
    ignitionfile = None
    if os.path.exists("%s.ign" % name):
        with open("%s.ign" % name) as f:
            ignitionfile = f.read()
    profile = str(profile)
    customprofile = str(customprofile)
    overrides = str(overrides)
    vmprofile = kcli_pb2.vmprofile(name=name, image=image, profile=profile, overrides=overrides,
                                   customprofile=customprofile, wait=wait, vmfiles=vmfiles,
                                   ignitionfile=ignitionfile)
    result = config.config.create_vm(vmprofile)
    if name is None:
        name = result.vm
        common.pprint("Using %s as name of the vm" % name)
    if profile == '':
        profile = image
    common.pprint("Deploying vm %s from profile %s..." % (name, profile))
    code = common.handle_response(result, name, element='', action='created', client=config.client)
    return code


def clone_vm(args):
    """Clone existing vm"""
    name = args.name
    base = args.base
    full = args.full
    start = args.start
    common.pprint("Cloning vm %s from vm %s..." % (name, base))
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    k.clone(base, name, full=full, start=start)


def update_vm(args):
    """Update ip, memory or numcpus"""
    ip1 = args.ip1
    flavor = args.flavor
    numcpus = args.numcpus
    memory = args.memory
    plan = args.plan
    autostart = args.autostart
    noautostart = args.noautostart
    dns = args.dns
    host = args.host
    domain = args.domain
    cloudinit = args.cloudinit
    image = args.image
    net = args.network
    information = args.information
    iso = args.iso
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    for name in names:
        if dns:
            common.pprint("Creating Dns entry for %s..." % name)
            if net is not None:
                nets = [net]
            else:
                nets = k.vm_ports(name)
            if nets and domain is None:
                domain = nets[0]
            if not nets:
                return
            else:
                k.reserve_dns(name=name, nets=nets, domain=domain, ip=ip1)
        elif ip1 is not None:
            common.pprint("Updating ip of vm %s to %s..." % (name, ip1))
            k.update_metadata(name, 'ip', ip1)
        elif cloudinit:
            common.pprint("Removing cloudinit information of vm %s" % name)
            k.remove_cloudinit(name)
            return
        elif plan is not None:
            common.pprint("Updating plan of vm %s to %s..." % (name, plan))
            k.update_metadata(name, 'plan', plan)
        elif image is not None:
            common.pprint("Updating image of vm %s to %s..." % (name, image))
            k.update_metadata(name, 'image', image)
        elif memory is not None:
            common.pprint("Updating memory of vm %s to %s..." % (name, memory))
            k.update_memory(name, memory)
        elif numcpus is not None:
            common.pprint("Updating numcpus of vm %s to %s..." % (name, numcpus))
            k.update_cpus(name, numcpus)
        elif autostart:
            common.pprint("Setting autostart for vm %s..." % name)
            k.update_start(name, start=True)
        elif noautostart:
            common.pprint("Removing autostart for vm %s..." % name)
            k.update_start(name, start=False)
        elif information:
            common.pprint("Setting information for vm %s..." % name)
            k.update_descrmation(name, information)
        elif iso is not None:
            common.pprint("Switching iso for vm %s to %s..." % (name, iso))
            k.update_iso(name, iso)
        elif flavor is not None:
            common.pprint("Updating flavor of vm %s to %s..." % (name, flavor))
            k.update_flavor(name, flavor)
        elif host:
            common.pprint("Creating Host entry for vm %s..." % name)
            nets = k.vm_ports(name)
            if not nets:
                return
            if domain is None:
                domain = nets[0]
            k.reserve_host(name, nets, domain)


def create_vmdisk(args):
    """Add disk to vm"""
    name = args.name
    size = args.size
    image = args.image
    interface = args.interface
    if interface not in ['virtio', 'ide', 'scsi']:
        common.pprint("Incorrect disk interface. Choose betwen virtio, scsi or ide...", color='red')
        os._exit(1)
    pool = args.pool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if size is None:
        common.pprint("Missing size. Leaving...", color='red')
        os._exit(1)
    if pool is None:
        common.pprint("Missing pool. Leaving...", color='red')
        os._exit(1)
    if name is None:
        common.pprint("Missing name. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding disk to %s..." % name)
    k.add_disk(name=name, size=size, pool=pool, image=image, interface=interface)


def delete_vmdisk(args):
    """Delete disk of vm"""
    name = args.name
    diskname = args.diskname
    pool = args.pool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if diskname is None:
        common.pprint("Missing diskname. Leaving...", color='red')
        os._exit(1)
    common.pprint("Deleting disk %s from vm %s" % (diskname, name))
    k.delete_disk(name=name, diskname=diskname, pool=pool)
    return


def create_dns(args):
    """Create dns entries"""
    name = args.name
    net = args.net
    domain = net
    ip = args.ip
    alias = args.alias
    if alias is None:
        alias = []
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Creating dns entry for %s..." % name)
    k.reserve_dns(name=name, nets=[net], domain=domain, ip=ip, alias=alias)


def delete_dns(args):
    """Delete dns entries"""
    name = args.name
    net = args.net
    domain = net
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting Dns entry for %s..." % name)
    k.delete_dns(name, domain)


def export_vm(args):
    """Export a vm"""
    image = args.image
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    names = [k.get_lastvm(kcli_pb2.client(client=config.client)).name] if not args.names else args.names
    codes = []
    for name in names:
        result = k.export(name=name, image=image)
        if result['result'] == 'success':
            common.pprint("Exporting vm %s" % name)
            codes.append(0)
        else:
            reason = result['reason']
            common.pprint("Could not delete vm %s because %s" % (name, reason), color='red')
            codes.append(1)
    os._exit(1 if 1 in codes else 0)


def create_lb(args):
    """Create loadbalancer"""
    checkpath = args.checkpath
    checkport = args.checkport
    ports = args.ports
    domain = args.domain
    internal = args.internal
    vms = args.vms.split(',') if args.vms is not None else []
    ports = args.ports.split(',') if args.ports is not None else []
    name = nameutils.get_random_name().replace('_', '-') if args.name is None else args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.handle_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain, checkport=checkport,
                               internal=internal)
    return 0


def delete_lb(args):
    """Delete loadbalancer"""
    yes = args.yes
    yes_top = args.yes_top
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.config.delete_lb(kcli_pb2.lb(lb=args.name))
    return 0


def create_generic_kube(args):
    """Create Generic kube"""
    paramfile = args.paramfile
    force = args.force
    cluster = args.cluster if args.cluster is not None else 'testk'
    if os.path.exists("/i_am_a_container"):
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            common.pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        common.pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if force:
        config.delete_kube(cluster, overrides=overrides)
    config.create_kube_generic(cluster, overrides=overrides)


def create_openshift_kube(args):
    """Create Generic kube"""
    paramfile = args.paramfile
    force = args.force
    cluster = args.cluster if args.cluster is not None else 'testk'
    if os.path.exists("/i_am_a_container"):
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            common.pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        common.pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
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
    common.pprint("Deleting kube %s" % cluster)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.config.delete_kube(kcli_pb2.kube(kube=cluster))
    if result.result == 'success':
        common.pprint("Kube %s deleted!" % cluster)
    else:
        reason = result.reason
        common.pprint("Could not delete kube %s because %s" % (cluster, reason), color='red')


def scale_generic_kube(args):
    """Scale kube"""
    workers = args.workers
    paramfile = args.paramfile
    cluster = args.cluster if args.cluster is not None else 'testk'
    if os.path.exists("/i_am_a_container"):
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            common.pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        common.pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if workers > 0:
        overrides['workers'] = workers
    config.scale_kube_generic(cluster, overrides=overrides)


def scale_openshift_kube(args):
    """Scale openshift kube"""
    workers = args.workers
    paramfile = args.paramfile
    cluster = args.cluster if args.cluster is not None else 'testk'
    if os.path.exists("/i_am_a_container"):
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            common.pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        common.pprint("Using default parameter file kcli_parameters.yml")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    if workers > 0:
        overrides['workers'] = workers
    config.scale_kube_openshift(cluster, overrides=overrides)


def create_vmnic(args):
    """Add nic to vm"""
    name = args.name
    network = args.network
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if network is None:
        common.pprint("Missing network. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding nic to vm %s..." % name)
    k.add_nic(name=name, network=network)


def delete_vmnic(args):
    """Delete nic of vm"""
    name = args.name
    interface = args.interface
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting nic from vm %s..." % name)
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
        common.pprint("Missing path. Leaving...", color='red')
        os._exit(1)
    common.pprint("Creating pool %s..." % pool)
    k.create_pool(kcli_pb2.pool(pool=pool, path=path, type=pooltype, thinpool=thinpool))


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
    common.pprint("Deleting pool %s..." % pool)
    result = k.delete_pool(kcli_pb2.pool(pool=pool, full=full))
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
    paramfile = args.paramfile
    wait = args.wait
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if os.path.exists("/i_am_a_container"):
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            common.pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        common.pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    _type = config.ini[config.client].get('type', 'kvm')
    overrides.update({'type': _type})
    if plan is None:
        plan = nameutils.get_random_name()
        common.pprint("Using %s as name of the plan" % plan)
    elif force:
        config.plan(plan, delete=True)
    config.plan(plan, ansible=ansible, url=url, path=path,
                container=container, inputfile=inputfile,
                overrides=overrides, wait=wait)
    return 0


def update_plan(args):
    """Update plan"""
    autostart = args.autostart
    noautostart = args.noautostart
    plan = args.plan
    url = args.url
    path = args.path
    container = args.container
    inputfile = args.inputfile
    paramfile = args.paramfile
    if os.path.exists("/i_am_a_container"):
        inputfile = "/workdir/%s" % inputfile if inputfile is not None else "/workdir/kcli_plan.yml"
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    if autostart:
        common.pprint("Setting vms from plan %s to autostart" % plan)
        config.config.autostart_plan(kcli_pb2.plan(plan=plan))
        common.pprint("Plan %s set with autostart" % plan)
        return 0
    if noautostart:
        common.pprint("Setting vms from plan %s to noautostart" % plan)
        config.config.noautostart_plan(kcli_pb2.plan(plan=plan))
        common.pprint("Plan %s set with noautostart" % plan)
        return 0
    config.plan(plan, url=url, path=path, container=container, inputfile=inputfile, overrides=overrides, update=True)
    return 0


def delete_plan(args):
    """Delete plan"""
    plan = args.plan
    yes = args.yes
    yes_top = args.yes_top
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    result = config.config.delete_plan(kcli_pb2.plan(plan=plan))
    if result.result == 'success':
        common.pprint("Plan %s deleted!" % plan)
    else:
        reason = result.reason
        common.pprint("Could not delete plan %s because %s" % (plan, reason), color='red')


def start_plan(args):
    """Start plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    common.pprint("Starting vms from plan %s" % plan)
    config.config.start_plan(kcli_pb2.plan(plan=plan))
    common.pprint("Plan %s started" % plan)
    return 0


def stop_plan(args):
    """Stop plan"""
    plan = args.plan
    common.pprint("Stopping vms from plan %s" % plan)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.config.stop_plan(kcli_pb2.plan(plan=plan))
    common.pprint("Plan %s stopped" % plan)
    return 0


def autostart_plan(args):
    """Autostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    common.pprint("Setting vms from plan %s to autostart" % plan)
    config.config.autostart_plan(kcli_pb2.plan(plan=plan))
    common.pprint("Plan %s set with autostart" % plan)
    return 0


def noautostart_plan(args):
    """Noautostart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    common.pprint("Setting vms from plan %s to noautostart" % plan)
    config.config.noautostart_plan(kcli_pb2.plan(plan=plan))
    common.pprint("Plan %s set with noautostart" % plan)
    return 0


def restart_plan(args):
    """Restart plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, restart=True)
    return 0


def info_plan(args):
    """Info plan """
    plan = args.plan
    doc = args.doc
    quiet = args.quiet
    url = args.url
    path = args.path
    inputfile = args.inputfile
    if os.path.exists("/i_am_a_container"):
        inputfile = "/workdir/%s" % inputfile if inputfile is not None else "/workdir/kcli_plan.yml"
    if url is None:
        inputfile = plan if inputfile is None and plan is not None else inputfile
        baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
        baseconfig.info_plan(inputfile, quiet=quiet, doc=doc)
    else:
        config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                         namespace=args.namespace)
        config.plan(plan, url=url, path=path, inputfile=inputfile, info=True, quiet=quiet, doc=doc)
    return 0


def info_generic_kube(args):
    """Info Generic kube"""
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    baseconfig.info_kube_generic(quiet=True)


def info_openshift_kube(args):
    """Info Openshift kube"""
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    baseconfig.info_kube_openshift(quiet=True)


def download_plan(args):
    """Download plan"""
    plan = args.plan
    url = args.url
    if plan is None:
        plan = nameutils.get_random_name()
        common.pprint("Using %s as name of the plan" % plan)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, url=url, download=True)
    return 0


def download_kubectl(args):
    """Download Kubectl"""
    common.get_kubectl()


def download_oc(args):
    """Download Oc"""
    common.get_oc()


def download_openshift_installer(args):
    """Download Openshift Installer"""
    paramfile = args.paramfile
    if os.path.exists("/i_am_a_container"):
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            common.pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        common.pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.download_openshift_installer(overrides)
    return 0


def create_pipeline(args):
    """Create Pipeline"""
    inputfile = args.inputfile
    kube = args.kube
    paramfile = args.paramfile
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
    if os.path.exists("/i_am_a_container"):
        inputfile = "/workdir/%s" % inputfile
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    if not kube and not os.path.exists(inputfile):
        common.pprint("File %s not found" % inputfile, color='red')
        return 0
    renderfile = baseconfig.create_pipeline(inputfile, overrides=overrides, kube=kube)
    print(renderfile)
    return 0


def render_file(args):
    """Render file"""
    plan = None
    inputfile = args.inputfile
    paramfile = args.paramfile
    ignore = args.ignore
    if os.path.exists("/i_am_a_container"):
        inputfile = "/workdir/%s" % inputfile if inputfile is not None else "/workdir/kcli_plan.yml"
        if paramfile is not None:
            paramfile = "/workdir/%s" % paramfile
        elif os.path.exists("/workdir/kcli_parameters.yml"):
            paramfile = "/workdir/kcli_parameters.yml"
            # common.pprint("Using default parameter file kcli_parameters.yml")
    elif paramfile is None and os.path.exists("kcli_parameters.yml"):
        paramfile = "kcli_parameters.yml"
        # common.pprint("Using default parameter file kcli_parameters.yml")
    overrides = common.get_overrides(paramfile=paramfile, param=args.param)
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    config_data = {'config_%s' % k: baseconfig.ini[baseconfig.client][k] for k in baseconfig.ini[baseconfig.client]}
    config_data['config_type'] = config_data.get('config_type', 'kvm')
    overrides.update(config_data)
    if not os.path.exists(inputfile):
        common.pprint("File %s not found" % inputfile, color='red')
        return 0
    renderfile = baseconfig.process_inputfile(plan, inputfile, overrides=overrides, onfly=False, ignore=ignore)
    print(renderfile)
    return 0


def snapshot_plan(args):
    """Snapshot plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, snapshot=True)
    return 0


def revert_plan(args):
    """Revert snapshot of plan"""
    plan = args.plan
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    config.plan(plan, revert=True)
    return 0


def create_repo(args):
    """Create repo"""
    repo = args.repo
    url = args.url
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    if repo is None:
        common.pprint("Missing repo. Leaving...", color='red')
        os._exit(1)
    if url is None:
        common.pprint("Missing url. Leaving...", color='red')
        os._exit(1)
    common.pprint("Adding repo %s..." % repo)
    baseconfig.create_repo(repo, url)
    return 0


def delete_repo(args):
    """Delete repo"""
    repo = args.repo
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    if repo is None:
        common.pprint("Missing repo. Leaving...", color='red')
        os._exit(1)
    common.pprint("Deleting repo %s..." % repo)
    baseconfig.delete_repo(kcli_pb2.repo(repo=repo))
    return


def update_repo(args):
    """Update repo"""
    repo = args.repo
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    if repo is None:
        common.pprint("Updating all repos...", color='blue')
        repos = baseconfig.list_repos()
        for repo in repos:
            common.pprint("Updating repo %s..." % repo)
            baseconfig.update_repo(repo)
    else:
        common.pprint("Updating repo %s..." % repo)
        baseconfig.update_repo(repo)
    return


def info_product(args):
    """Info product"""
    repo = args.repo
    product = args.product
    group = args.group
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    common.pprint("Providing information on product %s..." % product)
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
    common.pprint("Creating product %s..." % product)
    config.create_product(product, repo=repo, group=group, plan=plan, latest=latest, overrides=overrides)
    return 0


def ssh_vm(args):
    """Ssh into vm"""
    l = args.L
    r = args.R
    D = args.D
    X = args.X
    Y = args.Y
    user = args.user
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if len(args.name) > 1:
        cmd = ' '.join(args.name[1:])
    else:
        cmd = None
    name = k.get_lastvm(kcli_pb2.client(client=config.client)).name if not args.name else args.name
    if not args.name:
        name = k.get_lastvm(kcli_pb2.client(client=config.client)).name
        common.pprint("Using %s from %s as vm" % (name, config.client))
    else:
        name = args.name[0]
    sshcommand = k.ssh(kcli_pb2.vm(name=name, user=user, l=l, r=r, X=X, Y=Y, D=D, cmd=cmd)).sshcmd
    if sshcommand != '':
        if args.debug:
            print(sshcommand)
        if find_executable('ssh') is not None:
            os.system(sshcommand)
        else:
            print(sshcommand)
    else:
        common.pprint("Couldn't run ssh", color='red')


def scp_vm(args):
    """Scp into vm"""
    recursive = args.recursive
    source = args.source[0]
    source = source if not os.path.exists("/i_am_a_container") else "/workdir/%s" % source
    destination = args.destination[0]
    user = args.user
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    if len(source.split(':')) == 2:
        name, source = source.split(':')
        download = True
    elif len(destination.split(':')) == 2:
        name, destination = destination.split(':')
        download = False
    else:
        common.pprint("Couldn't run scp", color='red')
        return
    if '@' in name and len(name.split('@')) == 2:
        user, name = name.split('@')
    if download:
        common.pprint("Retrieving file %s from %s" % (source, name), color='green')
    else:
        common.pprint("Copying file %s to %s" % (source, name), color='green')
    scpdetails = kcli_pb2.scpdetails(name=name, user=user, source=source, destination=destination, download=download,
                                     recursive=recursive)
    scpcommand = k.scp(scpdetails).sshcmd
    if scpcommand != '':
        if find_executable('scp') is not None:
            os.system(scpcommand)
        else:
            print(scpcommand)
    else:
        common.pprint("Couldn't run scp", color='red')


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
        common.pprint("Missing Network", color='red')
        os._exit(1)
    if isolated:
        nat = False
    else:
        nat = True
    dhcp = str(not nodhcp)
    network = kcli_pb2.network(network=name, cidr=cidr, dhcp=dhcp, nat=nat, domain=domain, overrides=str(overrides))
    result = k.create_network(network)
    common.handle_response(result, name, element='Network')


def delete_network(args):
    """Delete Network"""
    name = args.name
    yes = args.yes
    yes_top = args.yes_top
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                     namespace=args.namespace)
    k = config.k
    if name is None:
        common.pprint("Missing Network", color='red')
        os._exit(1)
    if not yes and not yes_top:
        common.confirm("Are you sure?")
    result = k.delete_network(kcli_pb2.network(network=name))
    common.handle_response(result, name, element='Network', action='deleted')


def create_host_kvm(args):
    """Generate Kvm Host"""
    data = {}
    data['type'] = 'kvm'
    data['name'] = args.name
    data['host'] = args.host
    data['port'] = args.port
    data['user'] = args.user
    data['protocol'] = args.protocol
    data['url'] = args.url
    data['pool'] = args.pool
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone,
                     namespace=args.namespace)
    config.config.create_host(kcli_pb2.client(**data))
    common.pprint("Host %s created" % args.name)
    # baseconfig = Kconfig(client=args.client, debug=args.debug, quiet=True).baseconfig
    # if len(baseconfig.clients) == 1:
    #    baseconfig.set_defaults()


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
    baseconfig = Kconfig(client=args.client, debug=args.debug, quiet=True).baseconfig
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
    baseconfig = Kconfig(client=args.client, debug=args.debug, quiet=True).baseconfig
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
    baseconfig = Kconfig(client=args.client, debug=args.debug, quiet=True).baseconfig
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
    baseconfig = Kconfig(client=args.client, debug=args.debug, quiet=True).baseconfig
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
    if args.ca_file is not None:
        data['ca_file'] = args.ca
    data['multus'] = args.multus
    data['cdi'] = args.cdi
    if args.host is not None:
        data['host'] = args.host
    if args.port is not None:
        data['port'] = args.port
    common.create_host(data)
    baseconfig = Kconfig(client=args.client, debug=args.debug, quiet=True).baseconfig
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
    common.create_host(kcli_pb2.client(**data))
    baseconfig = Kconfig(client=args.client, debug=args.debug, quiet=True).baseconfig
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
            common.pprint("Using %s as a profile" % image)
        else:
            containerprofiles[image] = {'image': image}
    # cont.create_container(name, profile, overrides=overrides)
    common.pprint("Deploying container %s from profile %s..." % (name, profile))
    profile = containerprofiles[profile]
    image = next((e for e in [profile.get('image'), profile.get('image')] if e is not None), None)
    if image is None:
        common.pprint("Missing image in profile %s. Leaving..." % profile, color='red')
        os._exit(1)
    cmd = profile.get('cmd')
    ports = profile.get('ports')
    environment = profile.get('environment')
    volumes = next((e for e in [profile.get('volumes'), profile.get('disks')] if e is not None), None)
    profile.update(overrides)
    cont.create_container(name, image, nets=None, cmd=cmd, ports=ports, volumes=volumes, environment=environment,
                          overrides=overrides)
    common.pprint("container %s created" % name)
    return


def snapshotcreate_vm(args):
    """Create snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Creating snapshot of %s named %s..." % (name, snapshot))
    result = k.snapshot(snapshot, name)
    code = common.handle_response(result, name, element='', action='snapshotted')
    return code


def snapshotdelete_vm(args):
    """Delete snapshot"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Deleting snapshot %s of vm %s..." % (snapshot, name))
    result = k.snapshot(snapshot, name, delete=True)
    code = common.handle_response(result, name, element='', action='snapshot deleted')
    return code


def snapshotrevert_vm(args):
    """Revert snapshot of vm"""
    snapshot = args.snapshot
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Reverting snapshot %s of vm %s..." % (snapshot, name))
    result = k.snapshot(snapshot, name, revert=True)
    code = common.handle_response(result, name, element='', action='snapshot reverted')
    return code


def snapshotlist_vm(args):
    """List snapshots of vm"""
    name = args.name
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    common.pprint("Listing snapshots of %s..." % name)
    snapshots = k.snapshot('', name, listing=True)
    if isinstance(snapshots, dict):
        common.pprint("Vm %s not found" % name, color='red')
        return
    else:
        for snapshot in snapshots:
            print(snapshot)
    return


def report_host(args):
    """Report info about host"""
    config = Kconfig(client=args.client, debug=args.debug, region=args.region, zone=args.zone, namespace=args.namespace)
    k = config.k
    k.report()


def switch_host(args):
    """Handle host"""
    host = args.name
    common.pprint("Switching to client %s..." % host)
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    result = baseconfig.switch_host(kcli_pb2.client(client=host))
    if result.result == 'success':
        os._exit(0)
    else:
        os._exit(1)


def list_keyword(args):
    """List keywords"""
    baseconfig = Kconfig(client=args.client, debug=args.debug).baseconfig
    keywordstable = PrettyTable(["Keyword", "Default Value"])
    keywordstable.align["Client"] = "l"
    keywordslist = []
    keywords = baseconfig.list_keywords(empty()).keywords
    for keyword in keywords:
        keywordslist.append([keyword.keyword, keyword.value])
    for keyword in sorted(keywordslist):
        keywordstable.add_row(keyword)
    print(keywordstable)
    return


def cli():
    """

    """
    parser = argparse.ArgumentParser(description='Libvirt/Ovirt/Vsphere/Gcp/Aws/Openstack/Kubevirt Wrapper')
    parser.add_argument('-C', '--client')
    parser.add_argument('-G', '--grpcserver', default='localhost')
    parser.add_argument('--containerclient', help='Containerclient to use')
    parser.add_argument('--dnsclient', help='Dnsclient to use')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-n', '--namespace', help='Namespace to use. specific to kubevirt')
    parser.add_argument('-r', '--region', help='Region to use. specific to aws/gcp')
    parser.add_argument('-z', '--zone', help='Zone to use. specific to gcp')

    subparsers = parser.add_subparsers(metavar='', title='Available Commands')

    containerconsole_desc = 'Attach To Container'
    containerconsole_parser = subparsers.add_parser('attach', description=containerconsole_desc,
                                                    help=containerconsole_desc)
    containerconsole_parser.add_argument('name', metavar='CONTAINERNAME', nargs='?')
    containerconsole_parser.set_defaults(func=console_container)

    create_desc = 'Create Object'
    create_parser = subparsers.add_parser('create', description=create_desc, help=create_desc)
    create_subparsers = create_parser.add_subparsers(metavar='', dest='subcommand_create')

    vmclone_desc = 'Clone Vm'
    vmclone_epilog = None
    vmclone_parser = subparsers.add_parser('clone', description=vmclone_desc, help=vmclone_desc, epilog=vmclone_epilog,
                                           formatter_class=argparse.RawDescriptionHelpFormatter)
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
                          epilog=vmconsole_epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

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
                                            formatter_class=argparse.RawDescriptionHelpFormatter)
    vmexport_parser.add_argument('-i', '--image', help='Name for the generated image. Uses the vm name otherwise',
                                 metavar='IMAGE')
    vmexport_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmexport_parser.set_defaults(func=export_vm)

    hostlist_desc = 'List Hosts'

    info_desc = 'Info Host/Kube/Plan/Vm'
    info_parser = subparsers.add_parser('info', description=info_desc, help=info_desc)
    info_subparsers = info_parser.add_subparsers(metavar='', dest='subcommand_info')

    list_desc = 'List Object'
    list_epilog = "examples:\n%s" % _list
    list_parser = subparsers.add_parser('list', description=list_desc, help=list_desc, aliases=['get'],
                                        epilog=list_epilog,
                                        formatter_class=argparse.RawDescriptionHelpFormatter)
    list_subparsers = list_parser.add_subparsers(metavar='', dest='subcommand_list')

    render_desc = 'Render Plan/file'
    render_parser = subparsers.add_parser('render', description=render_desc, help=render_desc)
    render_parser.add_argument('-f', '--inputfile', help='Input Plan/File', default='kcli_plan.yml')
    render_parser.add_argument('-i', '--ignore', action='store_true', help='Ignore missing variables')
    render_parser.add_argument('-P', '--param', action='append',
                               help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    render_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
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
    vmscp_parser.add_argument('-r', '--recursive', help='Recursive', action='store_true')
    vmscp_parser.add_argument('-u', '-l', '--user', help='User for ssh')
    vmscp_parser.add_argument('source', nargs=1)
    vmscp_parser.add_argument('destination', nargs=1)
    vmscp_parser.set_defaults(func=scp_vm)
    subparsers.add_parser('scp', parents=[vmscp_parser], description=vmscp_desc, help=vmscp_desc, epilog=vmscp_epilog,
                          formatter_class=argparse.RawDescriptionHelpFormatter)

    snapshot_desc = 'Snapshot Vm/Plan'
    snapshot_parser = subparsers.add_parser('snapshot', description=snapshot_desc, help=snapshot_desc)
    snapshot_subparsers = snapshot_parser.add_subparsers(metavar='', dest='subcommand_snapshot')

    vmssh_desc = 'Ssh Into Vm'
    vmssh_epilog = None
    vmssh_parser = argparse.ArgumentParser(add_help=False)
    vmssh_parser.add_argument('-D', help='Dynamic Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-L', help='Local Forwarding', metavar='LOCAL')
    vmssh_parser.add_argument('-R', help='Remote Forwarding', metavar='REMOTE')
    vmssh_parser.add_argument('-X', action='store_true', help='Enable X11 Forwarding')
    vmssh_parser.add_argument('-Y', action='store_true', help='Enable X11 Forwarding(Insecure)')
    vmssh_parser.add_argument('-u', '-l', '--user', help='User for ssh')
    vmssh_parser.add_argument('name', metavar='VMNAME', nargs='*')
    vmssh_parser.set_defaults(func=ssh_vm)
    subparsers.add_parser('ssh', parents=[vmssh_parser], description=vmssh_desc, help=vmssh_desc, epilog=vmssh_epilog,
                          formatter_class=argparse.RawDescriptionHelpFormatter)

    start_desc = 'Start Vm/Plan/Container'
    start_epilog = "examples:\n%s" % start
    start_parser = subparsers.add_parser('start', description=start_desc, help=start_desc, epilog=start_epilog,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
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
                          epilog=version_epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

    # sub subcommands

    containercreate_desc = 'Create Container'
    containercreate_epilog = None
    containercreate_parser = create_subparsers.add_parser('container', description=containercreate_desc,
                                                          help=containercreate_desc, epilog=containercreate_epilog,
                                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    containercreate_parser_group = containercreate_parser.add_mutually_exclusive_group(required=True)
    containercreate_parser_group.add_argument('-i', '--image', help='Image to use', metavar='Image')
    containercreate_parser_group.add_argument('-p', '--profile', help='Profile to use', metavar='PROFILE')
    containercreate_parser.add_argument('-P', '--param', action='append',
                                        help='specify parameter or keyword for rendering (multiple can be specified)',
                                        metavar='PARAM')
    containercreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    containercreate_parser.add_argument('name', metavar='NAME', nargs='?')
    containercreate_parser.set_defaults(func=create_container)

    containerdelete_desc = 'Delete Container'
    containerdelete_parser = delete_subparsers.add_parser('container', description=containerdelete_desc,
                                                          help=containerdelete_desc)
    containerdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    containerdelete_parser.add_argument('names', metavar='CONTAINERNAMES', nargs='+')
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
                                                    formatter_class=argparse.RawDescriptionHelpFormatter)
    dnscreate_parser.add_argument('-a', '--alias', action='append', help='specify alias (can specify multiple)',
                                  metavar='ALIAS')
    dnscreate_parser.add_argument('-n', '--net', help='Domain where to create entry', metavar='NET')
    dnscreate_parser.add_argument('-i', '--ip', help='Ip', metavar='IP')
    dnscreate_parser.add_argument('name', metavar='NAME', nargs='?')
    dnscreate_parser.set_defaults(func=create_dns)

    dnsdelete_desc = 'Delete Dns Entries'
    dnsdelete_parser = delete_subparsers.add_parser('dns', description=dnsdelete_desc, help=dnsdelete_desc)
    dnsdelete_parser.add_argument('-n', '--net', help='Domain where to create entry', metavar='NET')
    dnsdelete_parser.add_argument('name', metavar='NAME', nargs='?')
    dnsdelete_parser.set_defaults(func=delete_dns)

    dnslist_desc = 'List Dns Entries'
    dnslist_parser = argparse.ArgumentParser(add_help=False)
    dnslist_parser.add_argument('--short', action='store_true')
    dnslist_parser.add_argument('domain', metavar='DOMAIN')
    dnslist_parser.set_defaults(func=list_dns)
    list_subparsers.add_parser('dns', parents=[dnslist_parser], description=dnslist_desc, help=dnslist_desc)

    hostcreate_desc = 'Create Host'
    hostcreate_epilog = "examples:\n%s" % hostcreate
    hostcreate_parser = create_subparsers.add_parser('host', help=hostcreate_desc, description=hostcreate_desc,
                                                     aliases=['client'], epilog=hostcreate_epilog,
                                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    hostcreate_subparsers = hostcreate_parser.add_subparsers(metavar='', dest='subcommand_create_host')

    awshostcreate_desc = 'Create Aws Host'
    awshostcreate_parser = hostcreate_subparsers.add_parser('aws', help=awshostcreate_desc,
                                                            description=awshostcreate_desc)
    awshostcreate_parser.add_argument('--access_key_id', help='Access Key Id', metavar='ACCESS_KEY_ID', required=True)
    awshostcreate_parser.add_argument('--access_key_secret', help='Access Key Secret', metavar='ACCESS_KEY_SECRET',
                                      required=True)
    awshostcreate_parser.add_argument('-k', '--keypair', help='Keypair', metavar='KEYPAIR', required=True)
    awshostcreate_parser.add_argument('-r', '--region', help='Region', metavar='REGION', required=True)
    awshostcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    awshostcreate_parser.set_defaults(func=create_host_aws)

    gcphostcreate_desc = 'Create Gcp Host'
    gcphostcreate_parser = hostcreate_subparsers.add_parser('gcp', help=gcphostcreate_desc,
                                                            description=gcphostcreate_desc)
    gcphostcreate_parser.add_argument('--credentials', help='Path to credentials file', metavar='credentials')
    gcphostcreate_parser.add_argument('--project', help='Project', metavar='project', required=True)
    gcphostcreate_parser.add_argument('--zone', help='Zone', metavar='zone', required=True)
    gcphostcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    gcphostcreate_parser.set_defaults(func=create_host_gcp)

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
    kvmhostcreate_parser.add_argument('name', metavar='NAME', nargs='?')
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
    kubevirthostcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    kubevirthostcreate_parser.set_defaults(func=create_host_kubevirt)

    openstackhostcreate_desc = 'Create Openstack Host'
    openstackhostcreate_parser = hostcreate_subparsers.add_parser('openstack', help=openstackhostcreate_desc,
                                                                  description=openstackhostcreate_desc)
    openstackhostcreate_parser.add_argument('-auth-url', help='Auth url', metavar='AUTH_URL', required=True)
    openstackhostcreate_parser.add_argument('-domain', help='Domain', metavar='DOMAIN', default='Default')
    openstackhostcreate_parser.add_argument('-p', '--password', help='Password', metavar='PASSWORD', required=True)
    openstackhostcreate_parser.add_argument('-project', help='Project', metavar='PROJECT', required=True)
    openstackhostcreate_parser.add_argument('-u', '--user', help='User', metavar='USER', required=True)
    openstackhostcreate_parser.add_argument('name', metavar='NAME', nargs='?')
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
    ovirthostcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    ovirthostcreate_parser.set_defaults(func=create_host_ovirt)

    vspherehostcreate_desc = 'Create Vsphere Host'
    vspherehostcreate_parser = hostcreate_subparsers.add_parser('vsphere', help=vspherehostcreate_desc,
                                                                description=vspherehostcreate_desc)
    vspherehostcreate_parser.add_argument('-c', '--cluster', help='Cluster', metavar='CLUSTER', required=True)
    vspherehostcreate_parser.add_argument('-d', '--datacenter', help='Datacenter', metavar='DATACENTER', required=True)
    vspherehostcreate_parser.add_argument('-H', '--host', help='Vcenter Host', metavar='HOST', required=True)
    vspherehostcreate_parser.add_argument('-p', '--password', help='Password', metavar='PASSWORD', required=True)
    vspherehostcreate_parser.add_argument('-u', '--user', help='User', metavar='USER', required=True)
    vspherehostcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    vspherehostcreate_parser.set_defaults(func=create_host_vsphere)

    hostdelete_desc = 'Delete Host'
    hostdelete_parser = delete_subparsers.add_parser('host', description=hostdelete_desc, help=hostdelete_desc,
                                                     aliases=['client'])
    hostdelete_parser.add_argument('name', metavar='NAME', nargs='?')
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

    kubecreate_desc = 'Create Kube'
    kubecreate_parser = create_subparsers.add_parser('kube', description=kubecreate_desc, help=kubecreate_desc)
    kubecreate_subparsers = kubecreate_parser.add_subparsers(metavar='', dest='subcommand_create_kube')

    kubegenericcreate_desc = 'Create Generic Kube'
    kubegenericcreate_epilog = "examples:\n%s" % kubegenericcreate
    kubegenericcreate_parser = argparse.ArgumentParser(add_help=False)
    kubegenericcreate_parser.add_argument('-f', '--force', action='store_true', help='Delete existing cluster first')
    kubegenericcreate_parser.add_argument('-P', '--param', action='append',
                                          help='specify parameter or keyword for rendering (multiple can be specified)',
                                          metavar='PARAM')
    kubegenericcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    kubegenericcreate_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubegenericcreate_parser.set_defaults(func=create_generic_kube)
    kubecreate_subparsers.add_parser('generic', parents=[kubegenericcreate_parser],
                                     description=kubegenericcreate_desc,
                                     help=kubegenericcreate_desc,
                                     epilog=kubegenericcreate_epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parameterhelp = "specify parameter or keyword for rendering (multiple can be specified)"
    kubeopenshiftcreate_desc = 'Create Openshift Kube'
    kubeopenshiftcreate_epilog = "examples:\n%s" % kubeopenshiftcreate
    kubeopenshiftcreate_parser = argparse.ArgumentParser(add_help=False)
    kubeopenshiftcreate_parser.add_argument('-f', '--force', action='store_true', help='Delete existing cluster first')
    kubeopenshiftcreate_parser.add_argument('-P', '--param', action='append', help=parameterhelp, metavar='PARAM')
    kubeopenshiftcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    kubeopenshiftcreate_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubeopenshiftcreate_parser.set_defaults(func=create_openshift_kube)
    kubecreate_subparsers.add_parser('openshift', parents=[kubeopenshiftcreate_parser],
                                     description=kubeopenshiftcreate_desc,
                                     help=kubeopenshiftcreate_desc,
                                     epilog=kubeopenshiftcreate_epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    kubedelete_desc = 'Delete Kube'
    kubedelete_parser = argparse.ArgumentParser(add_help=False)
    kubedelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    kubedelete_parser.add_argument('-P', '--param', action='append',
                                   help='specify parameter or keyword for rendering (multiple can be specified)',
                                   metavar='PARAM')
    kubedelete_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    kubedelete_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubedelete_parser.set_defaults(func=delete_kube)
    delete_subparsers.add_parser('kube', parents=[kubedelete_parser], description=kubedelete_desc, help=kubedelete_desc)

    kubeinfo_desc = 'Info Kube'
    kubeinfo_parser = info_subparsers.add_parser('kube', description=kubeinfo_desc, help=kubeinfo_desc)
    kubeinfo_subparsers = kubeinfo_parser.add_subparsers(metavar='', dest='subcommand_info_kube')

    kubegenericinfo_desc = 'Info Generic Kube'
    kubegenericinfo_parser = kubeinfo_subparsers.add_parser('generic', description=kubegenericinfo_desc,
                                                            help=kubegenericinfo_desc)
    kubegenericinfo_parser.set_defaults(func=info_generic_kube)

    kubeopenshiftinfo_desc = 'Info Openshift Kube'
    kubeopenshiftinfo_parser = kubeinfo_subparsers.add_parser('openshift', description=kubeopenshiftinfo_desc,
                                                              help=kubeopenshiftinfo_desc)
    kubeopenshiftinfo_parser.set_defaults(func=info_openshift_kube)

    kubelist_desc = 'List Kubes'
    kubelist_parser = list_subparsers.add_parser('kube', description=kubelist_desc, help=kubelist_desc,
                                                 aliases=['kubes'])
    kubelist_parser.set_defaults(func=list_kube)

    kubescale_desc = 'Scale Kube'
    kubescale_parser = scale_subparsers.add_parser('kube', description=kubescale_desc, help=kubescale_desc)
    kubescale_subparsers = kubescale_parser.add_subparsers(metavar='', dest='subcommand_scale_kube')

    kubegenericscale_desc = 'Scale Generic Kube'
    kubegenericscale_parser = argparse.ArgumentParser(add_help=False)
    kubegenericscale_parser.add_argument('-P', '--param', action='append',
                                         help='specify parameter or keyword for rendering (multiple can be specified)',
                                         metavar='PARAM')
    kubegenericscale_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    kubegenericscale_parser.add_argument('-w', '--workers', help='Total number of workers', type=int, default=0)
    kubegenericscale_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubegenericscale_parser.set_defaults(func=scale_generic_kube)
    kubescale_subparsers.add_parser('generic', parents=[kubegenericscale_parser], description=kubegenericscale_desc,
                                    help=kubegenericscale_desc)

    parameterhelp = "specify parameter or keyword for rendering (multiple can be specified)"
    kubeopenshiftscale_desc = 'Scale Openshift Kube'
    kubeopenshiftscale_parser = argparse.ArgumentParser(add_help=False)
    kubeopenshiftscale_parser.add_argument('-P', '--param', action='append', help=parameterhelp, metavar='PARAM')
    kubeopenshiftscale_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    kubeopenshiftscale_parser.add_argument('-w', '--workers', help='Total number of workers', type=int, default=0)
    kubeopenshiftscale_parser.add_argument('cluster', metavar='CLUSTER', nargs='?', type=valid_cluster)
    kubeopenshiftscale_parser.set_defaults(func=scale_openshift_kube)
    kubescale_subparsers.add_parser('openshift', parents=[kubeopenshiftscale_parser],
                                    description=kubeopenshiftscale_desc,
                                    help=kubeopenshiftscale_desc)

    lbcreate_desc = 'Create Load Balancer'
    lbcreate_parser = create_subparsers.add_parser('lb', description=lbcreate_desc, help=lbcreate_desc)
    lbcreate_parser.add_argument('--checkpath', default='/index.html', help="Path to check. Defaults to /index.html")
    lbcreate_parser.add_argument('--checkport', default=80, help="Port to check. Defaults to 80")
    lbcreate_parser.add_argument('--domain', help='Domain to create a dns entry associated to the load balancer')
    lbcreate_parser.add_argument('-i', '--internal', action='store_true')
    lbcreate_parser.add_argument('-p', '--ports', default='443', help='Load Balancer Ports. Defaults to 443')
    lbcreate_parser.add_argument('-v', '--vms', help='Vms to add to the pool')
    lbcreate_parser.add_argument('name', metavar='NAME', nargs='?')
    lbcreate_parser.set_defaults(func=create_lb)

    lbdelete_desc = 'Delete Load Balancer'
    lbdelete_parser = delete_subparsers.add_parser('lb', description=lbdelete_desc, help=lbdelete_desc)
    lbdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    lbdelete_parser.add_argument('name', metavar='NAME')
    lbdelete_parser.set_defaults(func=delete_lb)

    lblist_desc = 'List Load Balancers'
    lblist_parser = list_subparsers.add_parser('lb', description=lblist_desc, help=lblist_desc, aliases=['lbs'])
    lblist_parser.add_argument('--short', action='store_true')
    lblist_parser.set_defaults(func=list_lb)

    profilecreate_desc = 'Create Profile'
    profilecreate_parser = argparse.ArgumentParser(add_help=False)
    profilecreate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (can specify multiple)',
                                      metavar='PARAM')
    profilecreate_parser.add_argument('profile', metavar='PROFILE')
    profilecreate_parser.set_defaults(func=create_profile)
    create_subparsers.add_parser('profile', parents=[profilecreate_parser], description=profilecreate_desc,
                                 help=profilecreate_desc)

    profilelist_desc = 'List Profiles'
    profilelist_parser = list_subparsers.add_parser('profile', description=profilelist_desc, help=profilelist_desc,
                                                    aliases=['profiles'])
    profilelist_parser.add_argument('--short', action='store_true')
    profilelist_parser.set_defaults(func=list_profile)

    profiledelete_desc = 'Delete Profile'
    profiledelete_help = "Profile to delete"
    profiledelete_parser = argparse.ArgumentParser(add_help=False)
    profiledelete_parser.add_argument('profile', help=profiledelete_help, metavar='PROFILE')
    profiledelete_parser.set_defaults(func=delete_profile)
    delete_subparsers.add_parser('profile', parents=[profiledelete_parser], description=profiledelete_desc,
                                 help=profiledelete_desc)

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
                                                    aliases=['keywords'])
    keywordlist_parser.set_defaults(func=list_keyword)

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
    networkcreate_parser.add_argument('--nodhcp', action='store_true', help='Disable dhcp on the net')
    networkcreate_parser.add_argument('--domain', help='DNS domain. Defaults to network name')
    networkcreate_parser.add_argument('-P', '--param', action='append',
                                      help='specify parameter or keyword for rendering (can specify multiple)',
                                      metavar='PARAM')
    networkcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    networkcreate_parser.add_argument('name', metavar='NETWORK')
    networkcreate_parser.set_defaults(func=create_network)

    networkdelete_desc = 'Delete Network'
    networkdelete_parser = delete_subparsers.add_parser('network', description=networkdelete_desc,
                                                        help=networkdelete_desc)
    networkdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    networkdelete_parser.add_argument('name', metavar='NETWORK')
    networkdelete_parser.set_defaults(func=delete_network)

    pipelinecreate_desc = 'Create Pipeline'
    pipelinecreate_parser = create_subparsers.add_parser('pipeline', description=pipelinecreate_desc,
                                                         help=pipelinecreate_desc)
    pipelinecreate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    pipelinecreate_parser.add_argument('-k', '--kube', action='store_true', help='Create kube pipeline')
    pipelinecreate_parser.add_argument('-P', '--param', action='append',
                                       help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    pipelinecreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    pipelinecreate_parser.set_defaults(func=create_pipeline)

    plancreate_desc = 'Create Plan'
    plancreate_epilog = "examples:\n%s" % plancreate
    plancreate_parser = create_subparsers.add_parser('plan', description=plancreate_desc, help=plancreate_desc,
                                                     epilog=plancreate_epilog,
                                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    plancreate_parser.add_argument('-A', '--ansible', help='Generate ansible inventory', action='store_true')
    plancreate_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    plancreate_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan',
                                   metavar='PATH')
    plancreate_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    plancreate_parser.add_argument('--force', action='store_true', help='Delete existing vms first')
    plancreate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    plancreate_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    plancreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    plancreate_parser.add_argument('-w', '--wait', action='store_true', help='Wait for cloudinit to finish')
    plancreate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plancreate_parser.set_defaults(func=create_plan)

    plandelete_desc = 'Delete Plan'
    plandelete_parser = delete_subparsers.add_parser('plan', description=plandelete_desc, help=plandelete_desc)
    plandelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    plandelete_parser.add_argument('plan', metavar='PLAN')
    plandelete_parser.set_defaults(func=delete_plan)

    planinfo_desc = 'Info Plan'
    planinfo_epilog = "examples:\n%s" % planinfo
    planinfo_parser = info_subparsers.add_parser('plan', description=planinfo_desc, help=planinfo_desc,
                                                 epilog=planinfo_epilog,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    planinfo_parser.add_argument('--doc', action='store_true', help='Render info as markdown table')
    planinfo_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planinfo_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan', metavar='PATH')
    planinfo_parser.add_argument('-q', '--quiet', action='store_true', help='Provide parameter file output')
    planinfo_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    planinfo_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planinfo_parser.set_defaults(func=info_plan)

    planlist_desc = 'List Plans'
    planlist_parser = list_subparsers.add_parser('plan', description=planlist_desc, help=planlist_desc,
                                                 aliases=['plans'])
    planlist_parser.set_defaults(func=list_plan)

    planrestart_desc = 'Restart Plan'
    planrestart_parser = restart_subparsers.add_parser('plan', description=planrestart_desc, help=planrestart_desc)
    planrestart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planrestart_parser.set_defaults(func=restart_plan)

    planrevert_desc = 'Revert Snapshot Of Plan'
    planrevert_parser = revert_subparsers.add_parser('plan', description=planrevert_desc, help=planrevert_desc)
    planrevert_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planrevert_parser.set_defaults(func=revert_plan)

    plansnapshot_desc = 'Snapshot Plan'
    plansnapshot_parser = snapshot_subparsers.add_parser('plan', description=plansnapshot_desc, help=plansnapshot_desc)
    plansnapshot_parser.add_argument('plan', metavar='PLAN', nargs='?')
    plansnapshot_parser.set_defaults(func=snapshot_plan)

    planstart_desc = 'Start Plan'
    planstart_parser = start_subparsers.add_parser('plan', description=planstart_desc, help=planstart_desc)
    planstart_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planstart_parser.set_defaults(func=start_plan)

    planstop_desc = 'Stop Plan'
    planstop_parser = stop_subparsers.add_parser('plan', description=planstop_desc, help=planstop_desc)
    planstop_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planstop_parser.set_defaults(func=stop_plan)

    planupdate_desc = 'Update Plan'
    planupdate_parser = update_subparsers.add_parser('plan', description=planupdate_desc, help=planupdate_desc)
    planupdate_parser.add_argument('--autostart', action='store_true', help='Set autostart for vms of the plan')
    planupdate_parser.add_argument('--noautostart', action='store_true', help='Remove autostart for vms of the plan')
    planupdate_parser.add_argument('-u', '--url', help='Url for plan', metavar='URL')
    planupdate_parser.add_argument('-p', '--path', help='Path where to download plans. Defaults to plan',
                                   metavar='PATH')
    planupdate_parser.add_argument('-c', '--container', action='store_true', help='Handle container')
    planupdate_parser.add_argument('-f', '--inputfile', help='Input Plan file')
    planupdate_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    planupdate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    planupdate_parser.add_argument('plan', metavar='PLAN', nargs='?')
    planupdate_parser.set_defaults(func=update_plan)

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

    productcreate_desc = 'Create Product'
    productcreate_parser = create_subparsers.add_parser('product', description=productcreate_desc,
                                                        help=productcreate_desc)
    productcreate_parser.add_argument('-g', '--group', help='Group to use as a name during deployment', metavar='GROUP')
    productcreate_parser.add_argument('-l', '--latest', action='store_true', help='Grab latest version of the plans')
    productcreate_parser.add_argument('-P', '--param', action='append',
                                      help='Define parameter for rendering within scripts.'
                                      'Can be repeated several times', metavar='PARAM')
    productcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
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
                               epilog=productinfo_epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

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
                                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    repocreate_parser.add_argument('-u', '--url', help='URL of the repo', metavar='URL')
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

    imagedelete_desc = 'Delete Image'
    imagedelete_help = "Image to delete"
    imagedelete_parser = argparse.ArgumentParser(add_help=False)
    imagedelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    imagedelete_parser.add_argument('images', help=imagedelete_help, metavar='IMAGES', nargs='*')
    imagedelete_parser.set_defaults(func=delete_image)
    delete_subparsers.add_parser('image', parents=[imagedelete_parser], description=imagedelete_desc,
                                 help=imagedelete_desc)

    imagedownload_desc = 'Download Cloud Image'
    imagedownload_help = "Image to download. Choose between \n%s" % '\n'.join(IMAGES.keys())
    imagedownload_parser = argparse.ArgumentParser(add_help=False)
    imagedownload_parser.add_argument('-c', '--cmd', help='Extra command to launch after downloading', metavar='CMD')
    imagedownload_parser.add_argument('-p', '--pool', help='Pool to use. Defaults to default', metavar='POOL')
    imagedownload_parser.add_argument('-u', '--url', help='Url to use', metavar='URL')
    imagedownload_parser.add_argument('-s', '--skip-profile', help='Skip Profile update', action='store_true')
    imagedownload_parser.add_argument('image', help=imagedownload_help, metavar='IMAGE')
    imagedownload_parser.set_defaults(func=download_image)
    download_subparsers.add_parser('image', parents=[imagedownload_parser], description=imagedownload_desc,
                                   help=imagedownload_desc)

    openshiftdownload_desc = 'Download Openshift Installer'
    openshiftdownload_parser = argparse.ArgumentParser(add_help=False)
    openshiftdownload_parser.add_argument('-P', '--param', action='append',
                                          help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    openshiftdownload_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    openshiftdownload_parser.set_defaults(func=download_openshift_installer)
    download_subparsers.add_parser('openshift-installer', parents=[openshiftdownload_parser],
                                   description=openshiftdownload_desc,
                                   help=openshiftdownload_desc)

    kubectldownload_desc = 'Download Kubectl'
    kubectldownload_parser = argparse.ArgumentParser(add_help=False)
    kubectldownload_parser.add_argument('-P', '--param', action='append',
                                        help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    kubectldownload_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    kubectldownload_parser.set_defaults(func=download_kubectl)
    download_subparsers.add_parser('kubectl', parents=[kubectldownload_parser],
                                   description=kubectldownload_desc,
                                   help=kubectldownload_desc)

    ocdownload_desc = 'Download Oc'
    ocdownload_parser = argparse.ArgumentParser(add_help=False)
    ocdownload_parser.add_argument('-P', '--param', action='append',
                                   help='Define parameter for rendering (can specify multiple)', metavar='PARAM')
    ocdownload_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    ocdownload_parser.set_defaults(func=download_oc)
    download_subparsers.add_parser('oc', parents=[ocdownload_parser],
                                   description=ocdownload_desc,
                                   help=ocdownload_desc)

    plandownload_desc = 'Download Plan'
    plandownload_parser = argparse.ArgumentParser(add_help=False)
    plandownload_parser.add_argument('-u', '--url', help='Url to use', metavar='URL', required=True)
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
    vmcreate_parser.add_argument('-i', '--image', help='Image to use', metavar='IMAGE')
    vmcreate_parser.add_argument('--profilefile', help='File to load profiles from', metavar='PROFILEFILE')
    vmcreate_parser.add_argument('-P', '--param', action='append',
                                 help='specify parameter or keyword for rendering (multiple can be specified)',
                                 metavar='PARAM')
    vmcreate_parser.add_argument('--paramfile', help='Parameters file', metavar='PARAMFILE')
    vmcreate_parser.add_argument('-w', '--wait', action='store_true', help='Wait for cloudinit to finish')
    vmcreate_parser.add_argument('name', metavar='VMNAME', nargs='?', type=valid_fqdn)
    vmcreate_parser.set_defaults(func=create_vm)
    create_subparsers.add_parser('vm', parents=[vmcreate_parser], description=vmcreate_desc, help=vmcreate_desc,
                                 epilog=vmcreate_epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

    vmdelete_desc = 'Delete Vm'
    vmdelete_parser = argparse.ArgumentParser(add_help=False)
    vmdelete_parser.add_argument('-y', '--yes', action='store_true', help='Dont ask for confirmation')
    vmdelete_parser.add_argument('--snapshots', action='store_true', help='Remove snapshots if needed')
    vmdelete_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmdelete_parser.set_defaults(func=delete_vm)
    delete_subparsers.add_parser('vm', parents=[vmdelete_parser], description=vmdelete_desc, help=vmdelete_desc)

    vmdiskadd_desc = 'Add Disk To Vm'
    diskcreate_epilog = "examples:\n%s" % diskcreate
    vmdiskadd_parser = argparse.ArgumentParser(add_help=False)
    vmdiskadd_parser.add_argument('-s', '--size', type=int, help='Size of the disk to add, in GB', metavar='SIZE',
                                  default=10)
    vmdiskadd_parser.add_argument('-i', '--image', help='Name or Path of a Image', metavar='IMAGE')
    vmdiskadd_parser.add_argument('--interface', default='virtio', help='Disk Interface. Defaults to virtio',
                                  metavar='INTERFACE')
    vmdiskadd_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskadd_parser.add_argument('name', metavar='VMNAME')
    vmdiskadd_parser.set_defaults(func=create_vmdisk)
    create_subparsers.add_parser('disk', parents=[vmdiskadd_parser], description=vmdiskadd_desc, help=vmdiskadd_desc,
                                 aliases=['vm-disk'], epilog=diskcreate_epilog,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)

    vmdiskdelete_desc = 'Delete Vm Disk'
    diskdelete_epilog = "examples:\n%s" % diskdelete
    vmdiskdelete_parser = argparse.ArgumentParser(add_help=False)
    vmdiskdelete_parser.add_argument('-n', '--diskname', help='Name or Path of the disk', metavar='DISKNAME')
    vmdiskdelete_parser.add_argument('-p', '--pool', default='default', help='Pool', metavar='POOL')
    vmdiskdelete_parser.add_argument('name', metavar='VMNAME')
    vmdiskdelete_parser.set_defaults(func=delete_vmdisk)
    delete_subparsers.add_parser('disk', parents=[vmdiskdelete_parser], description=vmdiskdelete_desc,
                                 aliases=['vm-disk'], help=vmdiskdelete_desc, epilog=diskdelete_epilog,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)

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
    create_subparsers.add_parser('nic', parents=[create_vmnic_parser], description=create_vmnic_desc,
                                 help=create_vmnic_desc, aliases=['vm-nic'],
                                 epilog=create_vmnic_epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

    delete_vmnic_desc = 'Delete Nic From vm'
    delete_vmnic_epilog = "examples:\n%s" % nicdelete
    delete_vmnic_parser = argparse.ArgumentParser(add_help=False)
    delete_vmnic_parser.add_argument('-i', '--interface', help='Interface name', metavar='INTERFACE')
    delete_vmnic_parser.add_argument('-n', '--network', help='Network', metavar='NETWORK')
    delete_vmnic_parser.add_argument('name', metavar='VMNAME')
    delete_vmnic_parser.set_defaults(func=delete_vmnic)
    delete_subparsers.add_parser('nic', parents=[delete_vmnic_parser], description=delete_vmnic_desc,
                                 help=delete_vmnic_desc, aliases=['vm-nic'],
                                 epilog=delete_vmnic_epilog, formatter_class=argparse.RawDescriptionHelpFormatter)

    vmrestart_desc = 'Restart Vms'
    vmrestart_parser = restart_subparsers.add_parser('vm', description=vmrestart_desc, help=vmrestart_desc)
    vmrestart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmrestart_parser.set_defaults(func=restart_vm)

    vmsnapshotcreate_desc = 'Create Snapshot Of Vm'
    vmsnapshotcreate_parser = create_subparsers.add_parser('vm-snapshot', description=vmsnapshotcreate_desc,
                                                           help=vmsnapshotcreate_desc)
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
                                                           help=vmsnapshotrevert_desc)
    vmsnapshotrevert_parser.add_argument('-n', '--name', help='Use vm name for creation/revert/delete',
                                         required=True, metavar='VMNAME')
    vmsnapshotrevert_parser.add_argument('snapshot')
    vmsnapshotrevert_parser.set_defaults(func=snapshotrevert_vm)

    vmstart_desc = 'Start Vms'
    vmstart_parser = argparse.ArgumentParser(add_help=False)
    vmstart_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstart_parser.set_defaults(func=start_vm)
    start_subparsers.add_parser('vm', parents=[vmstart_parser], description=vmstart_desc, help=vmstart_desc)

    vmstop_desc = 'Stop Vms'
    vmstop_parser = argparse.ArgumentParser(add_help=False)
    vmstop_parser.add_argument('names', metavar='VMNAMES', nargs='*')
    vmstop_parser.set_defaults(func=stop_vm)
    stop_subparsers.add_parser('vm', parents=[vmstop_parser], description=vmstop_desc, help=vmstop_desc)

    vmupdate_desc = 'Update Vm\'s Ip, Memory Or Numcpus'
    vmupdate_parser = update_subparsers.add_parser('vm', description=vmupdate_desc, help=vmupdate_desc)
    vmupdate_parser.add_argument('-1', '--ip1', help='Ip to set', metavar='IP1')
    vmupdate_parser.add_argument('--information', '--info', help='Information to set', metavar='INFORMATION')
    vmupdate_parser.add_argument('--network', '--net', help='Network to update', metavar='NETWORK')
    vmupdate_parser.add_argument('-f', '--flavor', help='Flavor to set', metavar='Flavor')
    vmupdate_parser.add_argument('-m', '--memory', help='Memory to set', metavar='MEMORY')
    vmupdate_parser.add_argument('-c', '--numcpus', type=int, help='Number of cpus to set', metavar='NUMCPUS')
    vmupdate_parser.add_argument('-p', '--plan', help='Plan Name to set', metavar='PLAN')
    vmupdate_parser.add_argument('-a', '--autostart', action='store_true', help='Set VM to autostart')
    vmupdate_parser.add_argument('-n', '--noautostart', action='store_true', help='Prevent VM from autostart')
    vmupdate_parser.add_argument('--dns', action='store_true', help='Update Dns entry for the vm')
    vmupdate_parser.add_argument('--host', action='store_true', help='Update Host entry for the vm')
    vmupdate_parser.add_argument('-d', '--domain', help='Domain', metavar='DOMAIN')
    vmupdate_parser.add_argument('-i', '--image', help='Image to set', metavar='IMAGE')
    vmupdate_parser.add_argument('--iso', help='Iso to set', metavar='ISO')
    vmupdate_parser.add_argument('--cloudinit', action='store_true', help='Remove Cloudinit Information from vm')
    vmupdate_parser.add_argument('names', help='VMNAMES', nargs='*')
    vmupdate_parser.set_defaults(func=update_vm)

    argcomplete.autocomplete(parser)
    if len(sys.argv) == 1 or (len(sys.argv) == 3 and sys.argv[1] == '-C'):
        parser.print_help()
        os._exit(0)
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
                os._exit(0)
        os._exit(0)
    elif args.func.__name__ == 'vmcreate' and args.client is not None and ',' in args.client:
        args.client = random.choice(args.client.split(','))
        common.pprint("Selecting %s for creation" % args.client)
    global channel
    channel = grpc.insecure_channel('%s:50051' % args.grpcserver)
    try:
        grpc.channel_ready_future(channel).result(timeout=2)
    except grpc.FutureTimeoutError:
        common.pprint("RPC remote host %s not connected. Leaving" % args.grpcserver, color='red')
        os._exit(1)
    args.func(args)


if __name__ == '__main__':
    cli()
