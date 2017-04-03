#!/usr/bin/env python

from defaults import NETS, POOL, CPUMODEL, NUMCPUS, MEMORY, DISKS, DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID, VNC, CLOUDINIT, RESERVEIP, RESERVEDNS, RESERVEHOST, START, TEMPLATES, NESTED, TUNNEL
from kvm import Kvirt
from prettytable import PrettyTable
from shutil import copyfile
from time import sleep
from vbox import Kbox
import ansibleutils
import click
import common
import dockerutils
import fileinput
import nameutils
import os
import webbrowser
import yaml

__version__ = '5.22'

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def handle_response(result, name, element='', action='deployed'):
    if result['result'] == 'success':
        click.secho("%s%s %s!" % (element, name, action), fg='green')
        return 0
    else:
        reason = result['reason']
        click.secho("%s%s not %s because %s" % (element, name, action, reason), fg='red')
        return 1


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()

_global_options = [
    click.option('--debug', '-d', 'debug', is_flag=True, help='Debug Mode'),
    click.option('-C', '--client', 'client', help='Use specific client'),
]


def global_options(func):
    for option in reversed(_global_options):
        func = option(func)
    return func


class Config():
    def load(self):
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            if os.path.exists('/Users'):
                _type = 'vbox'
            else:
                _type = 'kvm'
            ini = {'default': {'client': 'local'}, 'local': {'pool': 'default', 'type': _type}}
            click.secho("Using local hypervisor as no kcli.yml was found...", fg='green')
        else:
            with open(inifile, 'r') as entries:
                try:
                    ini = yaml.load(entries)
                except:
                    self.host = None
                    return
            if 'default' not in ini or 'client' not in ini['default']:
                click.secho("Missing default section in config file. Leaving...", fg='red')
                self.host = None
                return
        self.clients = [e for e in ini if e != 'default']
        defaults = {}
        default = ini['default']
        defaults['nets'] = default.get('nets', NETS)
        defaults['pool'] = default.get('pool', POOL)
        defaults['cpumodel'] = default.get('cpumodel', CPUMODEL)
        defaults['numcpus'] = int(default.get('numcpus', NUMCPUS))
        defaults['memory'] = int(default.get('memory', MEMORY))
        defaults['disks'] = default.get('disks', DISKS)
        defaults['disksize'] = default.get('disksize', DISKSIZE)
        defaults['diskinterface'] = default.get('diskinterface', DISKINTERFACE)
        defaults['diskthin'] = default.get('diskthin', DISKTHIN)
        defaults['guestid'] = default.get('guestid', GUESTID)
        defaults['vnc'] = bool(default.get('vnc', VNC))
        defaults['cloudinit'] = bool(default.get('cloudinit', CLOUDINIT))
        defaults['reserveip'] = bool(default.get('reserveip', RESERVEIP))
        defaults['reservedns'] = bool(default.get('reservedns', RESERVEDNS))
        defaults['reservehost'] = bool(default.get('reservehost', RESERVEHOST))
        defaults['nested'] = bool(default.get('nested', NESTED))
        defaults['start'] = bool(default.get('start', START))
        defaults['tunnel'] = default.get('tunnel', TUNNEL)
        self.default = defaults
        self.ini = ini
        profilefile = default.get('profiles', "%s/kcli_profiles.yml" % os.environ.get('HOME'))
        profilefile = os.path.expanduser(profilefile)
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                self.profiles = yaml.load(entries)

    def get(self, client=None):
        if client is None:
            self.client = self.ini['default']['client']
        else:
            self.client = client
        if self.client not in self.ini:
            click.secho("Missing section for client %s in config file. Leaving..." % self.client, fg='red')
            os._exit(1)
        options = self.ini[self.client]
        self.host = options.get('host', '127.0.0.1')
        self.port = options.get('port', 22)
        self.user = options.get('user', 'root')
        self.protocol = options.get('protocol', 'ssh')
        self.url = options.get('url', None)
        self.tunnel = bool(options.get('tunnel', self.default['tunnel']))
        self.type = options.get('type', 'kvm')
        if self.type == 'vbox':
            k = Kbox()
        else:
            if self.host is None:
                click.secho("Problem parsing your configuration file", fg='red')
                os._exit(1)
            k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url, debug=self.debug)
        if k.conn is None:
            click.secho("Couldnt connect to specify hypervisor %s. Leaving..." % self.host, fg='red')
            os._exit(1)
        return k

pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@global_options
@pass_config
def cli(config, debug, client):
    """Libvirt/VirtualBox wrapper on steroids. Check out https://github.com/karmab/kcli!"""
    config.load()
    config.debug = debug
    config.client = client


@cli.command()
@click.option('-c', '--container', is_flag=True)
@click.argument('name', metavar='VMNAME')
@pass_config
def start(config, container, name):
    """Start vm/container"""
    k = config.get(config.client)
    if container:
        click.secho("Started container %s..." % name, fg='green')
        dockerutils.start_container(k, name)
    else:
        click.secho("Started vm %s..." % name, fg='green')
        result = k.start(name)
        code = handle_response(result, name, element='', action='started')
        os._exit(code)


@cli.command()
@click.option('-c', '--container', is_flag=True)
@click.argument('name', metavar='VMNAME')
@pass_config
def stop(config, container, name):
    """Stop vm/container"""
    k = config.get(config.client)
    if container:
        click.secho("Stopped container %s..." % name, fg='green')
        dockerutils.stop_container(k, name)
    else:
        click.secho("Stopped vm %s..." % name, fg='green')
        result = k.stop(name)
        code = handle_response(result, name, element='', action='stopped')
        os._exit(code)


@cli.command()
@click.option('-s', '--serial', is_flag=True)
@click.argument('name', metavar='VMNAME')
@pass_config
def console(config, serial, name):
    """Vnc/Spice/Serial/Container console"""
    k = config.get(config.client)
    tunnel = config.tunnel
    if serial:
        k.serialconsole(name)
    else:
        k.console(name=name, tunnel=tunnel)


@cli.command()
@click.confirmation_option(help='Are you sure?')
@click.option('--container', is_flag=True)
@click.argument('name', metavar='VMNAME')
@pass_config
def delete(config, container, name):
    """Delete vm/container"""
    k = config.get(config.client)
    if container:
        click.secho("Deleted container %s..." % name, fg='red')
        dockerutils.delete_container(k, name)
    else:
        code = k.delete(name)
        if code == 0:
            click.secho("Deleted vm %s..." % name, fg='red')
        os._exit(code)


@cli.command()
@click.argument('name', metavar='VMNAME')
@pass_config
def info(config, name):
    """Info vm"""
    k = config.get(config.client)
    code = k.info(name)
    os._exit(code)


@cli.command()
@click.option('-s', '--switch', 'switch', help='Switch To indicated client', metavar='CLIENT')
@click.option('-r', '--report', 'report', help='Report Hypervisor Information', is_flag=True)
@click.option('-p', '--profiles', help='List Profiles', is_flag=True)
@click.option('-t', '--templates', help='List Templates', is_flag=True)
@click.option('-i', '--isos', help='List Isos', is_flag=True)
@click.option('-d', '--disks', help='List Disks', is_flag=True)
@click.option('-p', '--pool', default='default', help='Pool to use when downloading', metavar='POOL')
@click.option('--template', type=click.Choice(['arch', 'centos6', 'centos7', 'cirros', 'debian8', 'fedora24', 'fedora25', 'gentoo', 'opensuse', 'ubuntu1404', 'ubuntu1604']), help='Template/Image to download')
@click.option('--download', help='Download Template/Image', is_flag=True)
@pass_config
def host(config, switch, report, profiles, templates, isos, disks, pool, template, download):
    """List and Handle host"""
    if switch:
        if switch not in config.clients:
            click.secho("Client %s not found in config.Leaving...." % switch, fg='green')
            os._exit(1)
        click.secho("Switching to client %s..." % switch, fg='green')
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if os.path.exists(inifile):
            for line in fileinput.input(inifile, inplace=True):
                if 'client' in line:
                    print(" client: %s" % switch)
                else:
                    print(line.rstrip())
        return
    k = config.get(config.client)
    if report:
        k.report()
    elif profiles:
        for profile in sorted(config.profiles):
            print(profile)
    elif templates:
        for template in sorted(k.volumes()):
            print(template)
    elif isos:
        for iso in sorted(k.volumes(iso=True)):
            print(iso)
    elif disks:
        click.secho("Listing disks...", fg='green')
        diskstable = PrettyTable(["Name", "Pool", "Path"])
        diskstable.align["Name"] = "l"
        k = config.get()
        disks = k.list_disks()
        for disk in sorted(disks):
            path = disks[disk]['path']
            pool = disks[disk]['pool']
            diskstable.add_row([disk, pool, path])
        print diskstable
    elif download:
        if pool is None:
            click.secho("Missing pool.Leaving...", fg='red')
            os._exit(1)
        if template is None:
            click.secho("Missing template.Leaving...", fg='red')
            os._exit(1)
        click.secho("Grabbing template %s..." % template, fg='green')
        template = TEMPLATES[template]
        shortname = os.path.basename(template)
        result = k.add_image(template, pool)
        code = handle_response(result, shortname, element='Template ', action='Added')
        os._exit(code)


@cli.command()
@click.option('-H', '--hosts', is_flag=True)
@click.option('-c', '--clients', is_flag=True)
@click.option('-p', '--profiles', is_flag=True)
@click.option('-t', '--templates', is_flag=True)
@click.option('-i', '--isos', is_flag=True)
@click.option('-d', '--disks', is_flag=True)
@click.option('-P', '--pools', is_flag=True)
@click.option('-n', '--networks', is_flag=True)
@click.option('--containers', is_flag=True)
@click.option('--plans', is_flag=True)
@click.option('-f', '--filters', type=click.Choice(['up', 'down']))
@pass_config
def list(config, hosts, clients, profiles, templates, isos, disks, pools, networks, containers, plans, filters):
    """List clients, profiles, templates, isos, pools or vms"""
    if config.client == 'all':
        clis = []
        for cli in sorted(config.clients):
            clis.append(cli)
    else:
        k = config.get(config.client)
    # k = config.get(config.client)
    if pools:
        poolstable = PrettyTable(["Pool"])
        poolstable.align["Pool"] = "l"
        pools = k.list_pools()
        for pool in sorted(pools):
            poolstable.add_row([pool])
        print(poolstable)
        return
    if hosts:
        clientstable = PrettyTable(["Name", "Current"])
        clientstable.align["Name"] = "l"
        for client in sorted(config.clients):
            if client == config.client:
                clientstable.add_row([client, 'X'])
            else:
                clientstable.add_row([client, ''])
        print(clientstable)
        return
    if networks:
        networks = k.list_networks()
        click.secho("Listing Networks...", fg='green')
        networkstable = PrettyTable(["Name", "Type", "Cidr", "Dhcp", "Mode"])
        networkstable.align["Name"] = "l"
        for network in sorted(networks):
            networktype = networks[network]['type']
            cidr = networks[network]['cidr']
            dhcp = networks[network]['dhcp']
            mode = networks[network]['mode']
            networkstable.add_row([network, networktype, cidr, dhcp, mode])
        print networkstable
        return
    if clients:
        clientstable = PrettyTable(["Name", "Current"])
        clientstable.align["Name"] = "l"
        for client in sorted(config.clients):
            if client == config.client:
                clientstable.add_row([client, 'X'])
            else:
                clientstable.add_row([client, ''])
        print(clientstable)
    elif profiles:
        profilestable = PrettyTable(["Profile"])
        profilestable.align["Profile"] = "l"
        for profile in sorted(config.profiles):
                profilestable.add_row([profile])
        print(profilestable)
    elif templates:
        templatestable = PrettyTable(["Template"])
        templatestable.align["Template"] = "l"
        for template in sorted(k.volumes()):
                templatestable.add_row([template])
        print(templatestable)
    elif isos:
        isostable = PrettyTable(["Iso"])
        isostable.align["Iso"] = "l"
        for iso in sorted(k.volumes(iso=True)):
                isostable.add_row([iso])
        print(isostable)
    elif disks:
        click.secho("Listing disks...", fg='green')
        diskstable = PrettyTable(["Name", "Pool", "Path"])
        diskstable.align["Name"] = "l"
        k = config.get()
        disks = k.list_disks()
        for disk in sorted(disks):
            path = disks[disk]['path']
            pool = disks[disk]['pool']
            diskstable.add_row([disk, pool, path])
        print diskstable
    elif containers:
        click.secho("Listing containers...", fg='green')
        containers = PrettyTable(["Name", "Status", "Image", "Plan", "Command", "Ports"])
        for container in dockerutils.list_containers(k):
            if filters:
                status = container[1]
                if status == filters:
                    containers.add_row(container)
            else:
                containers.add_row(container)
        print containers
    elif plans:
        vms = {}
        plans = PrettyTable(["Name", "Vms"])
        for vm in sorted(k.list(), key=lambda x: x[4]):
                vmname = vm[0]
                plan = vm[4]
                if plan in vms:
                    vms[plan].append(vmname)
                else:
                    vms[plan] = [vmname]
        for plan in sorted(vms):
            planvms = ','.join(vms[plan])
            plans.add_row([plan, planvms])
        print(plans)
    else:
        if config.client == 'all':
            vms = PrettyTable(["Name", "Hypervisor", "Status", "Ips", "Source", "Description/Plan", "Profile"])
            for client in sorted(clis):
                k = config.get(client)
                for vm in sorted(k.list()):
                    vm.insert(1, client)
                    if filters:
                        status = vm[2]
                        if status == filters:
                            vms.add_row(vm)
                    else:
                        vms.add_row(vm)
            print(vms)
            return
        else:
            vms = PrettyTable(["Name", "Status", "Ips", "Source", "Description/Plan", "Profile"])
            for vm in sorted(k.list()):
                if filters:
                    status = vm[1]
                    if status == filters:
                        vms.add_row(vm)
                else:
                    vms.add_row(vm)
            print(vms)
            return
#    else:
#        vms = PrettyTable(["Name", "Status", "Ips", "Source", "Description/Plan", "Profile"])
#        for vm in sorted(k.list()):
#            if filters:
#                status = vm[1]
#                if status == filters:
#                    vms.add_row(vm)
#            else:
#                vms.add_row(vm)
#        print(vms)


@cli.command()
@click.option('-p', '--profile', help='Profile to use', metavar='PROFILE')
@click.option('-i', '--info', 'info', help='Info about Vm', is_flag=True)
@click.option('-f', '--filters', type=click.Choice(['up', 'down']))
@click.option('-s', '--start', 'start', help='Start Vm', is_flag=True)
@click.option('-w', '--stop', 'stop', help='Stop Vm', is_flag=True)
@click.option('-d', '--delete', 'delete', help='Delete vm', is_flag=True)
@click.option('--ssh', 'ssh', help='Ssh Vm', is_flag=True)
@click.option('-1', '--ip1', help='Optional Ip to assign to eth0. Netmask and gateway will be retrieved from profile', metavar='IP1')
@click.option('-2', '--ip2', help='Optional Ip to assign to eth1. Netmask and gateway will be retrieved from profile', metavar='IP2')
@click.option('-3', '--ip3', help='Optional Ip to assign to eth2. Netmask and gateway will be retrieved from profile', metavar='IP3')
@click.option('-4', '--ip4', help='Optional Ip to assign to eth3. Netmask and gateway will be retrieved from profile', metavar='IP4')
@click.option('-5', '--ip5', help='Optional Ip to assign to eth4. Netmask and gateway will be retrieved from profile', metavar='IP5')
@click.option('-6', '--ip6', help='Optional Ip to assign to eth5. Netmask and gateway will be retrieved from profile', metavar='IP6')
@click.option('-7', '--ip7', help='Optional Ip to assign to eth6. Netmask and gateway will be retrieved from profile', metavar='IP7')
@click.option('-8', '--ip8', help='Optional Ip to assign to eth8. Netmask and gateway will be retrieved from profile', metavar='IP8')
@click.option('-L', help='Local Forwarding')
@click.option('-R', help='Remote Forwarding')
@click.argument('name', required=False, metavar='VMNAME')
@pass_config
def vm(config, profile, info, filters, start, stop, delete, ssh, ip1, ip2, ip3, ip4, ip5, ip6, ip7, ip8, l, r, name):
    """Create/Delete/Start/Stop/List vms"""
    if config.client == 'all':
        clients = []
        for cli in sorted(config.clients):
            clients.append(cli)
    else:
        k = config.get(config.client)
        tunnel = config.tunnel
    if name is None:
        click.secho("Missing vm name", fg='red')
        os._exit(1)
    if info:
        code = k.info(name)
        os._exit(code)
    if start:
        click.secho("Started vm %s..." % name, fg='green')
        result = k.start(name)
        code = handle_response(result, name, element='', action='started')
        os._exit(code)
    if stop:
        click.secho("Stopped vm %s..." % name, fg='green')
        result = k.stop(name)
        code = handle_response(result, name, element='', action='stopped')
        os._exit(code)
    if delete:
        code = k.delete(name)
        if code == 0:
            click.secho("Deleted vm %s..." % name, fg='red')
        os._exit(code)
    if ssh:
        k.ssh(name, local=l, remote=r)
        return
    if profile is None:
        click.secho("Missing profile", fg='red')
        os._exit(1)
    default = config.default
    vmprofiles = {k: v for k, v in config.profiles.iteritems() if 'type' not in v or v['type'] == 'vm'}
    click.secho("Deploying vm %s from profile %s..." % (name, profile), fg='green')
    if profile not in vmprofiles:
        click.secho("profile %s not found. Trying to use the profile as template and default values..." % profile, fg='blue')
        result = k.create(name=name, memory=1024, template=profile)
        code = handle_response(result, name)
        os._exit(code)
        return
    title = profile
    profile = vmprofiles[profile]
    template = profile.get('template')
    description = 'kvirt'
    nets = profile.get('nets', default['nets'])
    cpumodel = profile.get('cpumodel', default['cpumodel'])
    cpuflags = profile.get('cpuflags', [])
    numcpus = profile.get('numcpus', default['numcpus'])
    memory = profile.get('memory', default['memory'])
    pool = profile.get('pool', default['pool'])
    disks = profile.get('disks', default['disks'])
    disksize = profile.get('disksize', default['disksize'])
    diskinterface = profile.get('diskinterface', default['diskinterface'])
    diskthin = profile.get('diskthin', default['diskthin'])
    guestid = profile.get('guestid', default['guestid'])
    iso = profile.get('iso')
    vnc = profile.get('vnc', default['vnc'])
    cloudinit = profile.get('cloudinit', default['cloudinit'])
    reserveip = profile.get('reserveip', default['reserveip'])
    reservedns = profile.get('reservedns', default['reservedns'])
    reservehost = profile.get('reservehost', default['reservehost'])
    nested = profile.get('nested', default['nested'])
    start = profile.get('start', default['start'])
    keys = profile.get('keys', None)
    cmds = profile.get('cmds', None)
    netmasks = profile.get('netmasks')
    gateway = profile.get('gateway')
    dns = profile.get('dns')
    domain = profile.get('domain')
    scripts = profile.get('scripts')
    files = profile.get('files', [])
    if scripts is not None:
        scriptcmds = []
        for script in scripts:
            script = os.path.expanduser(script)
            if not os.path.exists(script):
                click.secho("Script %s not found.Ignoring..." % script, fg='red')
                os._exit(1)
            else:
                scriptlines = [line.strip() for line in open(script).readlines() if line != '\n']
                if scriptlines:
                    scriptcmds.extend(scriptlines)
        if scriptcmds:
            if cmds is None:
                cmds = scriptcmds
            else:
                cmds = cmds + scriptcmds
    ips = [ip1, ip2, ip3, ip4, ip5, ip6, ip7, ip8]
    result = k.create(name=name, description=description, title=title, cpumodel=cpumodel, cpuflags=cpuflags, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain, nested=bool(nested), tunnel=tunnel, files=files)
    handle_response(result, name)
    if result['result'] != 'success':
        return
    ansible = profile.get('ansible')
    if ansible is not None:
        for element in ansible:
            if 'playbook' not in element:
                continue
            playbook = element['playbook']
            if 'variables' in element:
                variables = element['variables']
            if 'verbose' in element:
                verbose = element['verbose']
            else:
                verbose = False
            # k.play(name, playbook=playbook, variables=variables, verbose=verbose)
            with open("/tmp/%s.inv" % name, "w") as f:
                inventory = ansibleutils.inventory(k, name)
                if inventory is not None:
                    if variables is not None:
                        for variable in variables:
                            if not isinstance(variable, dict) or len(variable.keys()) != 1:
                                continue
                            else:
                                key, value = variable.keys()[0], variable[variable.keys()[0]]
                                inventory = "%s %s=%s" % (inventory, key, value)
                if config.tunnel:
                    inventory = "%s ansible_ssh_common_args='-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"'\n" % (inventory, config.port, config.user, config.host)
                f.write("%s\n" % inventory)
            ansiblecommand = "ansible-playbook"
            if verbose:
                ansiblecommand = "%s -vvv" % ansiblecommand
            ansibleconfig = os.path.expanduser('~/.ansible.cfg')
            with open(ansibleconfig, "w") as f:
                f.write("[ssh_connection]\nretries=10\n")
            print("Running: %s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))
            os.system("%s -i /tmp/%s.inv %s" % (ansiblecommand, name, playbook))


@cli.command()
@click.option('-b', '--base', help='Base VM', metavar='BASE')
@click.option('-f', '--full', is_flag=True, help='Full Clone')
@click.option('-s', '--start', is_flag=True, help='Start cloned VM')
@click.argument('name', metavar='VMNAME')
@pass_config
def clone(config, base, full, start, name):
    """Clone existing vm"""
    click.secho("Cloning vm %s from vm %s..." % (name, base), fg='green')
    k = config.get(config.client)
    k.clone(base, name, full=full, start=start)


@cli.command()
@click.option('-1', '--ip1', help='Ip to set', metavar='IP1')
@click.option('-m', '--memory', help='Memory to set', metavar='MEMORY')
@click.option('-c', '--numcpus', help='Number of cpus to set', metavar='NUMCPUS')
@click.option('-a', '--autostart', is_flag=True, help='Set VM to autostart')
@click.option('-n', '--noautostart', is_flag=True, help='Prevent VM from autostart')
@click.option('--dns', is_flag=True, help='Update Dns entry for the vm')
@click.option('--host', is_flag=True, help='Update Host entry for the vm')
@click.option('-d', '--domain', help='Domain', metavar='DOMAIN')
@click.argument('name', metavar='VMNAME')
@pass_config
def update(config, ip1, memory, numcpus, autostart, noautostart, dns, host, domain, name):
    """Update ip, memory or numcpus"""
    k = config.get(config.client)
    if ip1 is not None:
        click.secho("Updating ip of vm %s to %s..." % (name, ip1), fg='green')
        k.update_ip(name, ip1)
    elif memory is not None:
        click.secho("Updating memory of vm %s to %s..." % (name, memory), fg='green')
        k.update_memory(name, memory)
    elif numcpus is not None:
        click.secho("Updating numcpus of vm %s to %s..." % (name, numcpus), fg='green')
        k.update_cpu(name, numcpus)
    elif autostart:
        click.secho("Setting autostart for vm %s..." % (name), fg='green')
        k.update_start(name, start=True)
    elif noautostart:
        click.secho("Removing autostart for vm %s..." % (name), fg='green')
        k.update_start(name, start=False)
    elif host:
        click.secho("Creating Host entry for vm %s..." % (name), fg='green')
        nets = k.vm_ports(name)
        if domain is None:
            domain = nets[0]
        k.reserve_host(name, nets, domain)
    elif dns:
        click.secho("Creating Dns entry for vm %s..." % (name), fg='green')
        nets = k.vm_ports(name)
        if domain is None:
            domain = nets[0]
        code = k.reserve_dns(name, nets, domain)
        os._exit(code)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-s', '--size', help='Size of the disk to add, in GB', metavar='SIZE')
@click.option('-n', '--diskname', help='Name or Path of the disk, when deleting', metavar='DISKNAME')
@click.option('-t', '--template', help='Name or Path of a Template, when adding', metavar='TEMPLATE')
@click.option('-p', '--pool', default='default', help='Pool', metavar='POOL')
@click.argument('name')
@pass_config
def disk(config, delete, size, diskname, template, pool, name):
    """Add/Delete disk of vm"""
    if delete:
        if diskname is None:
            click.secho("Missing diskname. Leaving...", fg='red')
            os._exit(1)
        click.secho("Deleting disk %s from %s..." % (diskname, name), fg='green')
        k = config.get(config.client)
        k.delete_disk(name, diskname)
        return
    if size is None:
        click.secho("Missing size. Leaving...", fg='red')
        os._exit(1)
    if pool is None:
        click.secho("Missing pool. Leaving...", fg='red')
        os._exit(1)
    k = config.get()
    click.secho("Adding disk %s to %s..." % (diskname, name), fg='green')
    k.add_disk(name=name, size=size, pool=pool, template=template)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-i', '--interface', help='Name of the interface, when deleting', metavar='INTERFACE')
@click.option('-n', '--network', help='Network', metavar='NETWORK')
@click.argument('name', metavar='VMNAME')
@pass_config
def nic(config, delete, interface, network, name):
    """Add/Delete nic of vm"""
    if delete:
        click.secho("Deleting nic from %s..." % (name), fg='green')
        k = config.get(config.client)
        k.delete_nic(name, interface)
        return
    if network is None:
        click.secho("Missing network. Leaving...", fg='red')
        os._exit(1)
    k = config.get()
    click.secho("Adding Nic %s..." % (name), fg='green')
    k.add_nic(name=name, network=network)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-f', '--full', is_flag=True)
@click.option('-t', '--pooltype', help='Type of the pool', type=click.Choice(['dir', 'logical']), default='dir')
@click.option('-p', '--path', help='Path of the pool', metavar='PATH')
@click.argument('pool', required=False)
@pass_config
def pool(config, delete, full, pooltype, path, pool):
    """Create/Delete pool"""
    k = config.get(config.client)
    if pool is None:
        click.secho("Missing pool name", fg='red')
        os._exit(1)
    if delete:
        click.secho("Deleting pool %s..." % (pool), fg='green')
        k.delete_pool(name=pool, full=full)
        return
    if path is None:
        click.secho("Missing path. Leaving...", fg='red')
        os._exit(1)
    click.secho("Adding pool %s..." % (pool), fg='green')
    k.create_pool(name=pool, poolpath=path, pooltype=pooltype)


@cli.command()
@click.option('-A', '--ansible', 'ansible', help='Generate ansible inventory', is_flag=True)
@click.option('-g', '--get', 'get', help='Download specific plan(s). Use --path for specific directory', metavar='URL')
@click.option('-p', '--path', 'path', default='plans', help='Path where to download plans. Defaults to plan', metavar='PATH')
@click.option('-a', '--autostart', is_flag=True, help='Set all vms from plan to autostart')
@click.option('-c', '--container', is_flag=True, help='Handle container')
@click.option('-n', '--noautostart', is_flag=True, help='Prevent all vms from plan to autostart')
@click.option('-f', '--inputfile', help='Input file')
@click.option('-s', '--start', is_flag=True, help='start all vms from plan')
@click.option('-w', '--stop', is_flag=True)
@click.option('-d', '--delete', is_flag=True)
@click.option('-t', '--delay', default=0, help="Delay between each vm's creation", metavar='DELAY')
@click.argument('plan', required=False, metavar='PLAN')
@pass_config
def plan(config, ansible, get, path, autostart, container, noautostart, inputfile, start, stop, delete, delay, plan):
    """Create/Delete/Stop/Start vms from plan file"""
    newvms = []
    vmprofiles = {key: value for key, value in config.profiles.iteritems() if 'type' not in value or value['type'] == 'vm'}
    containerprofiles = {key: value for key, value in config.profiles.iteritems() if 'type' in value and value['type'] == 'container'}
    k = config.get(config.client)
    tunnel = config.tunnel
    if plan is None:
        plan = nameutils.get_random_name()
    if delete:
        networks = []
        if plan == '':
            click.secho("That would delete every vm...Not doing that", fg='red')
            os._exit(1)
        click.confirm('Are you sure about deleting plan %s' % plan, abort=True)
        found = False
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                vmnetworks = k.vm_ports(name)
                for network in vmnetworks:
                    if network != 'default' and network not in networks:
                        networks.append(network)
                k.delete(name)
                click.secho("VM %s deleted!" % name, fg='green')
                found = True
        if container:
            for cont in sorted(dockerutils.list_containers(k)):
                name = cont[0]
                container_plan = cont[3]
                if container_plan == plan:
                    dockerutils.delete_container(k, name)
                    click.secho("Container %s deleted!" % name, fg='green')
                    found = True
        for network in networks:
            k.delete_network(network)
            click.secho("Unused network %s deleted!" % network, fg='green')
            found = True
        if found:
            click.secho("Plan %s deleted!" % plan, fg='green')
        else:
            click.secho("Nothing to do for plan %s" % plan, fg='red')
            os._exit(1)
        return
    if autostart:
        click.secho("Set vms from plan %s to autostart" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.update_start(name, start=True)
                click.secho("%s set to autostart!" % name, fg='green')
        return
    if noautostart:
        click.secho("Preventing vms from plan %s to autostart" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.update_start(name, start=False)
                click.secho("%s prevented to autostart!" % name, fg='green')
        return
    if start:
        click.secho("Starting vms from plan %s" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.start(name)
                click.secho("VM %s started!" % name, fg='green')
        if container:
            for cont in sorted(dockerutils.list_containers(k)):
                name = cont[0]
                containerplan = cont[3]
                if containerplan == plan:
                    dockerutils.start_container(k, name)
                    click.secho("Container %s started!" % name, fg='green')
        click.secho("Plan %s started!" % plan, fg='green')
        return
    if stop:
        click.secho("Stopping vms from plan %s" % (plan), fg='green')
        for vm in sorted(k.list()):
            name = vm[0]
            description = vm[4]
            if description == plan:
                k.stop(name)
                click.secho("%s stopped!" % name, fg='green')
        if container:
            for cont in sorted(dockerutils.list_containers(k)):
                name = cont[0]
                containerplan = cont[3]
                if containerplan == plan:
                    dockerutils.stop_container(k, name)
                    click.secho("Container %s stopped!" % name, fg='green')
        click.secho("Plan %s stopped!" % plan, fg='green')
        return
    if get is not None:
        click.secho("Retrieving specified plan from %s to %s" % (get, path), fg='green')
        common.fetch(get, path)
        return
    if inputfile is None:
        inputfile = 'kcli_plan.yml'
        click.secho("using default input file kcli_plan.yml", fg='green')
    inputfile = os.path.expanduser(inputfile)
    if not os.path.exists(inputfile):
        click.secho("No input file found nor default kcli_plan.yml.Leaving....", fg='red')
        os._exit(1)
    default = config.default
    with open(inputfile, 'r') as entries:
        entries = yaml.load(entries)
        vmentries = [entry for entry in entries if 'type' not in entries[entry] or entries[entry]['type'] == 'vm']
        diskentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'disk']
        networkentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'network']
        containerentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'container']
        ansibleentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'ansible']
        profileentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'profile']
        templateentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'template']
        poolentries = [entry for entry in entries if 'type' in entries[entry] and entries[entry]['type'] == 'pool']
        for p in profileentries:
            vmprofiles[p] = entries[p]
        if networkentries:
            click.secho("Deploying Networks...", fg='green')
        for net in networkentries:
            netprofile = entries[net]
            if k.net_exists(net):
                click.secho("Network %s skipped!" % net, fg='blue')
                continue
            cidr = netprofile.get('cidr')
            nat = bool(netprofile.get('nat', True))
            if cidr is None:
                print "Missing Cidr for network %s. Not creating it..." % net
                continue
            dhcp = netprofile.get('dhcp', True)
            result = k.create_network(name=net, cidr=cidr, dhcp=dhcp, nat=nat)
            handle_response(result, net, element='Network ')
        if poolentries:
            click.secho("Deploying Pool...", fg='green')
            pools = k.list_pools()
            for pool in poolentries:
                if pool in pools:
                    click.secho("Pool %s skipped!" % pool, fg='blue')
                    continue
                else:
                    poolprofile = entries[pool]
                    poolpath = poolprofile.get('path')
                    if poolpath is None:
                        click.secho("Pool %s skipped as path is missing!" % pool, fg='blue')
                        continue
                    k.create_pool(pool, poolpath)
        if templateentries:
            click.secho("Deploying Templates...", fg='green')
            templates = [os.path.basename(t) for t in k.volumes()]
            for template in templateentries:
                if template in templates:
                    click.secho("Template %s skipped!" % template, fg='blue')
                    continue
                else:
                    templateprofile = entries[template]
                    pool = templateprofile.get('pool', default['pool'])
                    url = templateprofile.get('url')
                    if url is None:
                        click.secho("Template %s skipped as url is missing!" % template, fg='blue')
                        continue
                    if not url.endswith('qcow2') and not url.endswith('img'):
                        click.secho("Opening url %s for you to download %s" % (url, template), fg='blue')
                        webbrowser.open(url, new=2, autoraise=True)
                        continue
                    result = k.add_image(url, pool, short=template)
                    handle_response(result, template, element='Template ', action='Added')
        if vmentries:
            click.secho("Deploying Vms...", fg='green')
            for name in vmentries:
                profile = entries[name]
                if k.exists(name):
                    click.secho("VM %s skipped!" % name, fg='blue')
                    continue
                if 'profile' in profile and profile['profile'] in vmprofiles:
                    customprofile = vmprofiles[profile['profile']]
                    title = profile['profile']
                else:
                    customprofile = {}
                    title = plan
                description = plan
                pool = next((e for e in [profile.get('pool'), customprofile.get('pool'), default['pool']] if e is not None))
                template = next((e for e in [profile.get('template'), customprofile.get('template')] if e is not None), None)
                cpumodel = next((e for e in [profile.get('cpumodel'), customprofile.get('cpumodel'), default['cpumodel']] if e is not None))
                cpuflags = next((e for e in [profile.get('cpuflags'), customprofile.get('cpuflags'), []] if e is not None))
                numcpus = next((e for e in [profile.get('numcpus'), customprofile.get('numcpus'), default['numcpus']] if e is not None))
                memory = next((e for e in [profile.get('memory'), customprofile.get('memory'), default['memory']] if e is not None))
                disks = next((e for e in [profile.get('disks'), customprofile.get('disks'), default['disks']] if e is not None))
                disksize = next((e for e in [profile.get('disksize'), customprofile.get('disksize'), default['disksize']] if e is not None))
                diskinterface = next((e for e in [profile.get('diskinterface'), customprofile.get('diskinterface'), default['diskinterface']] if e is not None))
                diskthin = next((e for e in [profile.get('diskthin'), customprofile.get('diskthin'), default['diskthin']] if e is not None))
                guestid = next((e for e in [profile.get('guestid'), customprofile.get('guestid'), default['guestid']] if e is not None))
                vnc = next((e for e in [profile.get('vnc'), customprofile.get('vnc'), default['vnc']] if e is not None))
                cloudinit = next((e for e in [profile.get('cloudinit'), customprofile.get('cloudinit'), default['cloudinit']] if e is not None))
                reserveip = next((e for e in [profile.get('reserveip'), customprofile.get('reserveip'), default['reserveip']] if e is not None))
                reservedns = next((e for e in [profile.get('reservedns'), customprofile.get('reservedns'), default['reservedns']] if e is not None))
                reservehost = next((e for e in [profile.get('reservehost'), customprofile.get('reservehost'), default['reservehost']] if e is not None))
                nested = next((e for e in [profile.get('nested'), customprofile.get('nested'), default['nested']] if e is not None))
                start = next((e for e in [profile.get('start'), customprofile.get('start'), default['start']] if e is not None))
                nets = next((e for e in [profile.get('nets'), customprofile.get('nets'), default['nets']] if e is not None))
                iso = next((e for e in [profile.get('iso'), customprofile.get('iso')] if e is not None), None)
                keys = next((e for e in [profile.get('keys'), customprofile.get('keys')] if e is not None), None)
                cmds = next((e for e in [profile.get('cmds'), customprofile.get('cmds')] if e is not None), None)
                netmasks = next((e for e in [profile.get('netmasks'), customprofile.get('netmasks')] if e is not None), None)
                gateway = next((e for e in [profile.get('gateway'), customprofile.get('gateway')] if e is not None), None)
                dns = next((e for e in [profile.get('dns'), customprofile.get('dns')] if e is not None), None)
                domain = next((e for e in [profile.get('domain'), customprofile.get('domain')] if e is not None), None)
                ips = profile.get('ips')
                sharedkey = bool(profile.get('sharedkey', False))
                scripts = next((e for e in [profile.get('scripts'), customprofile.get('scripts')] if e is not None), None)
                missingscript = False
                if scripts is not None:
                    scriptcmds = []
                    for script in scripts:
                        script = os.path.expanduser(script)
                        if not os.path.exists(script):
                            click.secho("Script %s not found. Ignoring this vm..." % script, fg='red')
                            missingscript = True
                        else:
                            scriptlines = [line.strip() for line in open(script).readlines() if line != '\n']
                            if scriptlines:
                                scriptcmds.extend(scriptlines)
                    if scriptcmds:
                        if cmds is None:
                            cmds = scriptcmds
                        else:
                            cmds = cmds + scriptcmds
                if missingscript:
                    continue
                files = next((e for e in [profile.get('files'), customprofile.get('files')] if e is not None), [])
                if sharedkey:
                    if not os.path.exists("%s.key" % plan) or not os.path.exists("%s.key.pub" % plan):
                        os.popen("ssh-keygen -t rsa -N '' -f %s.key" % plan)
                    publickey = open("%s.key.pub" % plan).read().strip()
                    # privatekey = open("%s.key" % plan).readlines()
                    privatekey = open("%s.key" % plan).read().strip()
                    if keys is None:
                        keys = [publickey]
                    else:
                        keys.append(publickey)
                    # sharedkeycmd = "'echo %s >/root/.ssh/id_rsa'" % privatekey
                    # cmd1 = "'echo %s >/root/.ssh/id_rsa'" % privatekey
                    # cmd2 = "chmod 600 /root/.ssh/id_rsa"
                    # if cmds is None:
                    #    cmds = [cmd1, cmd2]
                    # else:
                    #    cmds.extend([cmd1, cmd2])
                    if files:
                        files.append({'path': '/root/.ssh/id_rsa', 'content': privatekey})
                    else:
                        files = [{'path': '/root/.ssh/id_rsa', 'content': privatekey}]
                result = k.create(name=name, description=description, title=title, cpumodel=cpumodel, cpuflags=cpuflags, numcpus=int(numcpus), memory=int(memory), guestid=guestid, pool=pool, template=template, disks=disks, disksize=disksize, diskthin=diskthin, diskinterface=diskinterface, nets=nets, iso=iso, vnc=bool(vnc), cloudinit=bool(cloudinit), reserveip=bool(reserveip), reservedns=bool(reservedns), reservehost=bool(reservehost), start=bool(start), keys=keys, cmds=cmds, ips=ips, netmasks=netmasks, gateway=gateway, dns=dns, domain=domain, nested=nested, tunnel=tunnel, files=files)
                handle_response(result, name)
                if result['result'] == 'success':
                    newvms.append(name)
                ansible = next((e for e in [profile.get('ansible'), customprofile.get('ansible')] if e is not None), None)
                if ansible is not None:
                    for element in ansible:
                        if 'playbook' not in element:
                            continue
                        playbook = element['playbook']
                        if 'variables' in element:
                            variables = element['variables']
                        if 'verbose' in element:
                            verbose = element['verbose']
                        else:
                            verbose = False
                        ansibleutils.play(k, name, playbook=playbook, variables=variables, verbose=verbose)
                if delay > 0:
                    sleep(delay)
        if diskentries:
            click.secho("Deploying Disks...", fg='green')
        for disk in diskentries:
            profile = entries[disk]
            pool = profile.get('pool')
            vms = profile.get('vms')
            template = profile.get('template')
            size = int(profile.get('size', 10))
            if pool is None:
                click.secho("Missing Key Pool for disk section %s. Not creating it..." % disk, fg='red')
                continue
            if vms is None:
                click.secho("Missing or Incorrect Key Vms for disk section %s. Not creating it..." % disk, fg='red')
                continue
            if k.disk_exists(pool, disk):
                click.secho("Disk %s skipped!" % disk, fg='blue')
                continue
            if len(vms) > 1:
                shareable = True
            else:
                shareable = False
            newdisk = k.create_disk(disk, size=size, pool=pool, template=template, thin=False)
            click.secho("Disk %s deployed!" % disk, fg='green')
            for vm in vms:
                k.add_disk(name=vm, size=size, pool=pool, template=template, shareable=shareable, existing=newdisk, thin=False)
        if containerentries:
            click.secho("Deploying Containers...", fg='green')
            label = "plan=%s" % (plan)
            for container in containerentries:
                if dockerutils.exists_container(k, container):
                    click.secho("Container %s skipped!" % container, fg='blue')
                    continue
                profile = entries[container]
                if 'profile' in profile and profile['profile'] in containerprofiles:
                    customprofile = containerprofiles[profile['profile']]
                else:
                    customprofile = {}
                image = next((e for e in [profile.get('image'), profile.get('template'), customprofile.get('image'), customprofile.get('template')] if e is not None), None)
                nets = next((e for e in [profile.get('nets'), customprofile.get('nets')] if e is not None), None)
                ports = next((e for e in [profile.get('ports'), customprofile.get('ports')] if e is not None), None)
                volumes = next((e for e in [profile.get('volumes'), profile.get('disks'), customprofile.get('volumes'), customprofile.get('disks')] if e is not None), None)
                environment = next((e for e in [profile.get('environment'), customprofile.get('environment')] if e is not None), None)
                cmd = next((e for e in [profile.get('cmd'), customprofile.get('cmd')] if e is not None), None)
                click.secho("Container %s deployed!" % container, fg='green')
                dockerutils.create_container(k, name=container, image=image, nets=nets, cmd=cmd, ports=ports, volumes=volumes, environment=environment, label=label)
                # handle_response(result, name)
        if ansibleentries:
            if not newvms:
                click.secho("Ansible skipped as no new vm within playbook provisioned", fg='blue')
                return
            for item, entry in enumerate(ansibleentries):
                ansible = entries[ansibleentries[item]]
                if 'playbook' not in ansible:
                    click.secho("Missing Playbook for ansible.Ignoring...", fg='red')
                    os._exit(1)
                playbook = ansible['playbook']
                if 'verbose' in ansible:
                    verbose = ansible['verbose']
                else:
                    verbose = False
                vms = []
                if 'vms' in ansible:
                    vms = ansible['vms']
                    for vm in vms:
                        if vm not in newvms:
                            vms.remove(vm)
                else:
                    vms = newvms
                if not vms:
                    click.secho("Ansible skipped as no new vm within playbook provisioned", fg='blue')
                    return
                ansibleutils.make_inventory(k, plan, newvms, tunnel=config.tunnel)
                # with open("/tmp/%s.inv" % plan, "w") as f:
                #    f.write("[%s]\n" % plan)
                #    for name in newvms:
                #        inventory = ansibleutils.inventory(k, name)
                #        if inventory is not None:
                #            f.write("%s\n" % inventory)
                #    if config.tunnel:
                #        f.write("[%s:vars]\n" % plan)
                #        f.write("ansible_ssh_common_args='-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"'\n" % (config.port, config.user, config.host))
                ansiblecommand = "ansible-playbook"
                if verbose:
                    ansiblecommand = "%s -vvv" % ansiblecommand
                ansibleconfig = os.path.expanduser('~/.ansible.cfg')
                with open(ansibleconfig, "w") as f:
                    f.write("[ssh_connection]\nretries=10\n")
                print("Running: %s -i /tmp/%s.inv %s" % (ansiblecommand, plan, playbook))
                os.system("%s -i /tmp/%s.inv %s" % (ansiblecommand, plan, playbook))
    if ansible:
        click.secho("Deploying Ansible Inventory...", fg='green')
        if os.path.exists("/tmp/%s.inv" % plan):
            click.secho("Inventory in /tmp/%s.inv skipped!" % (plan), fg='blue')
        else:
            click.secho("Creating ansible inventory for plan %s in /tmp/%s.inv" % (plan, plan), fg='green')
            vms = []
            for vm in sorted(k.list()):
                name = vm[0]
                description = vm[4]
                if description == plan:
                    vms.append(name)
            ansibleutils.make_inventory(k, plan, vms, tunnel=config.tunnel)
            return


@cli.command()
@click.option('-L', help='Local Forwarding', metavar='LOCAL')
@click.option('-R', help='Remote Forwarding', metavar='REMOTE')
@click.argument('name', metavar='VMNAME')
@pass_config
def ssh(config, l, r, name):
    """Ssh into vm"""
    k = config.get(config.client)
    tunnel = config.tunnel
    k.ssh(name, local=l, remote=r, tunnel=tunnel)


@cli.command()
@click.option('-r', '--recursive', 'recursive', help='Recursive', is_flag=True)
@click.argument('source', nargs=1)
@click.argument('destination', nargs=1)
@pass_config
def scp(config, recursive, source, destination):
    """Scp into vm"""
    k = config.get(config.client)
    tunnel = config.tunnel
    if len(source.split(':')) == 2:
        name = source.split(':')[0]
        source = source.split(':')[1]
        k.scp(name, source=source, destination=destination, tunnel=tunnel, download=True, recursive=recursive)
    elif len(destination.split(':')) == 2:
        name = destination.split(':')[0]
        destination = destination.split(':')[1]
        k.scp(name, source=source, destination=destination, tunnel=tunnel, download=False, recursive=recursive)


@cli.command()
@click.option('-d', '--delete', is_flag=True)
@click.option('-i', '--isolated', is_flag=True, help='Isolated Network')
@click.option('-c', '--cidr', help='Cidr of the net', metavar='CIDR')
@click.option('--nodhcp', is_flag=True, help='Disable dhcp on the net')
@click.argument('name', required=False, metavar='NETWORK')
@pass_config
def network(config, delete, isolated, cidr, nodhcp, name):
    """Create/Delete/List Network"""
    k = config.get(config.client)
    if name is None:
        click.secho("Missing Network", fg='red')
        os._exit(1)
    if delete:
        result = k.delete_network(name=name)
        handle_response(result, name, element='Network ', action='deleted')
    else:
        if isolated:
            nat = False
        else:
            nat = True
        dhcp = not nodhcp
        result = k.create_network(name=name, cidr=cidr, dhcp=dhcp, nat=nat)
        handle_response(result, name, element='Network ')


@cli.command()
@click.option('-f', '--genfile', is_flag=True)
@click.option('-a', '--auto', is_flag=True, help="Don't ask for anything")
@click.option('-n', '--name', help='Name to use', metavar='CLIENT')
@click.option('-H', '--host', help='Host to use', metavar='HOST')
@click.option('-p', '--port', help='Port to use', metavar='PORT')
@click.option('-u', '--user', help='User to use', default='root', metavar='USER')
@click.option('-P', '--protocol', help='Protocol to use', default='ssh', metavar='PROTOCOL')
@click.option('-U', '--url', help='URL to use', metavar='URL')
@click.option('--pool', help='Pool to use', metavar='POOL')
@click.option('--poolpath', help='Pool Path to use', metavar='POOLPATH')
@click.option('-t', '--template', is_flag=True, help="Grab Centos Cloud Image")
def bootstrap(genfile, auto, name, host, port, user, protocol, url, pool, poolpath, template):
    """Handle hypervisor, reporting or bootstrapping by creating config file and optionally pools and network"""
    click.secho("Bootstrapping env", fg='green')
    if genfile or auto:
        if host is None and url is None:
            url = 'qemu:///system'
            host = '127.0.0.1'
        if pool is None:
            pool = 'default'
        if poolpath is None:
            poolpath = '/var/lib/libvirt/images'
        if '/dev' in poolpath:
            pooltype = 'logical'
        else:
            pooltype = 'dir'
        if template:
            template = TEMPLATES['centos']
        else:
            template = None
        nets = {'default': {'cidr': '192.168.122.0/24'}}
        # disks = [{'size': 10}]
        if host == '127.0.0.1':
            ini = {'default': {'client': 'local'}, 'local': {'pool': pool, 'nets': ['default']}}
        else:
            if name is None:
                name = host
            ini = {'default': {'client': name}}
            ini[name] = {'host': host, 'pool': pool, 'nets': ['default']}
            if protocol is not None:
                ini[name]['protocol'] = protocol
            if user is not None:
                ini[name]['user'] = user
            if port is not None:
                ini[name]['port'] = port
            if url is not None:
                ini[name]['url'] = url
    else:
        ini = {'default': {}}
        default = ini['default']
        click.secho("We will configure kcli together !", fg='blue')
        if name is None:
            name = raw_input("Enter your default client name[local]: ") or 'local'
        if pool is None:
            pool = raw_input("Enter your default pool[default]: ") or 'default'
        default['pool'] = pool
        size = raw_input("Enter your client first disk size[10]: ") or '10'
        default['disks'] = [{'size': size}]
        net = raw_input("Enter your client first network[default]: ") or 'default'
        default['nets'] = [net]
        cloudinit = raw_input("Use cloudinit[True]: ") or 'True'
        default['cloudinit'] = cloudinit
        diskthin = raw_input("Use thin disks[True]: ") or 'True'
        default['diskthin'] = diskthin
        ini['default']['client'] = name
        ini[name] = {}
        client = ini[name]
        if host is None:
            host = raw_input("Enter your client hostname/ip[localhost]: ") or 'localhost'
        client['host'] = host
        if url is None:
            url = raw_input("Enter your client url: ") or None
            if url is not None:
                client['url'] = url
            else:
                if protocol is None:
                    protocol = raw_input("Enter your client protocol[ssh]: ") or 'ssh'
                client['protocol'] = protocol
                if port is None:
                    port = raw_input("Enter your client port: ") or None
                    if port is not None:
                        client['port'] = port
                user = raw_input("Enter your client user[root]: ") or 'root'
                client['user'] = user
        pool = raw_input("Enter your client pool[%s]: " % default['pool']) or default['pool']
        client['pool'] = pool
        poolcreate = raw_input("Create pool if not there[Y]: ") or 'Y'
        if poolcreate == 'Y':
            poolpath = raw_input("Enter yourpool path[/var/lib/libvirt/images]: ") or '/var/lib/libvirt/images'
        else:
            poolpath = None
        if poolpath is None:
            pooltype = None
        elif '/dev' in poolpath:
            pooltype = 'logical'
        else:
            pooltype = 'dir'
        client['pool'] = pool
        templatecreate = raw_input("Download centos7 image for you?[N]: ") or 'N'
        if templatecreate == 'Y':
            template = TEMPLATES['centos']
        else:
            template = None
        size = raw_input("Enter your client first disk size[%s]: " % default['disks'][0]['size']) or default['disks'][0]['size']
        client['disks'] = [{'size': size}]
        net = raw_input("Enter your client first network[%s]: " % default['nets'][0]) or default['nets'][0]
        client['nets'] = [net]
        nets = {}
        netcreate = raw_input("Create net if not there[Y]: ") or 'Y'
        if netcreate == 'Y':
            cidr = raw_input("Enter cidr [192.168.122.0/24]: ") or '192.168.122.0/24'
            nets[net] = {'cidr': cidr, 'dhcp': True}
        cloudinit = raw_input("Use cloudinit for this client[%s]: " % default['cloudinit']) or default['cloudinit']
        client['cloudinit'] = cloudinit
        diskthin = raw_input("Use thin disks for this client[%s]: " % default['diskthin']) or default['diskthin']
        client['diskthin'] = diskthin
    k = Kvirt(host=host, port=port, user=user, protocol=protocol, url=url)
    if k.conn is None:
        click.secho("Couldnt connect to specify hypervisor %s. Leaving..." % host, fg='red')
        os._exit(1)
    k.bootstrap(pool=pool, poolpath=poolpath, pooltype=pooltype, nets=nets, image=template)
    # TODO:
    # DOWNLOAD CIRROS ( AND CENTOS7? ) IMAGES TO POOL ?
    path = os.path.expanduser('~/kcli.yml')
    if os.path.exists(path):
        copyfile(path, "%s.bck" % path)
    with open(path, 'w') as conf_file:
        yaml.safe_dump(ini, conf_file, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    click.secho("Environment bootstrapped!", fg='green')


@cli.command()
@click.option('-p', '--profile', help='Profile to use', metavar='PROFILE')
@click.option('-s', '--start', 'start', help='Start Container', is_flag=True)
@click.option('-w', '--stop', 'stop', help='Stop Container', is_flag=True)
@click.option('-c', '--console', help='Console of the Container', is_flag=True)
@click.argument('name', required=False, metavar='NAME')
@pass_config
def container(config, profile, start, stop, console, name):
    """Create/Delete/List containers"""
    k = config.get(config.client)
    if name is None:
        click.secho("Missing container name", fg='red')
        os._exit(1)
    if start:
        click.secho("Started container %s..." % name, fg='green')
        dockerutils.start_container(k, name)
        return
    if stop:
        click.secho("Stopped container %s..." % name, fg='green')
        dockerutils.stop_container(k, name)
        return
    if console:
        dockerutils.console_container(k, name)
        return
    if profile is None:
        click.secho("Missing profile", fg='red')
        os._exit(1)
    containerprofiles = {k: v for k, v in config.profiles.iteritems() if 'type' in v and v['type'] == 'container'}
    if profile not in containerprofiles:
        click.secho("profile %s not found. Trying to use the profile as image and default values..." % profile, fg='blue')
        dockerutils.create_container(k, name, profile)
        return
    else:
        click.secho("Deploying vm %s from profile %s..." % (name, profile), fg='green')
        profile = containerprofiles[profile]
        image = next((e for e in [profile.get('image'), profile.get('template')] if e is not None), None)
        if image is None:
            click.secho("Missing image in profile %s. Leaving..." % profile, fg='red')
            os._exit(1)
        cmd = profile.get('cmd', None)
        ports = profile.get('ports', None)
        environment = profile.get('environment', None)
        volumes = next((e for e in [profile.get('volumes'), profile.get('disks')] if e is not None), None)
        dockerutils.create_container(k, name, image, nets=None, cmd=cmd, ports=ports, volumes=volumes, environment=environment)
        return


@cli.command()
@click.option('-n', '--name', help='Use vm name for creation/revert/delete', metavar='VMNAME')
@click.option('-r', '--revert', 'revert', help='Revert to indicated snapshot', is_flag=True)
@click.option('-d', '--delete', 'delete', help='Delete indicated snapshot', is_flag=True)
@click.option('-l', '--listing', 'listing', help='List snapshots', is_flag=True)
@click.argument('snapshot')
@pass_config
def snapshot(config, name, revert, delete, listing, snapshot):
    """Create/Delete/Revert snapshot"""
    k = config.get(config.client)
    if revert:
        click.secho("Reverting snapshot of %s named %s..." % (name, snapshot), fg='green')
    elif delete:
        click.secho("Deleting snapshot of %s named %s..." % (name, snapshot), fg='green')
    elif listing:
        click.secho("Listing snapshots of %s..." % (name), fg='green')
        k.snapshot(snapshot, name, listing=True)
        return 0
    elif snapshot is None:
        click.secho("Missing snapshot name", fg='red')
        return 1
    else:
        click.secho("Creating snapshot of %s named %s..." % (name, snapshot), fg='green')
    result = k.snapshot(snapshot, name, revert=revert, delete=delete)
    code = handle_response(result, name, element='', action='snapshotted')
    os._exit(code)


if __name__ == '__main__':
    cli()
