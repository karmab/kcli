#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Kvirt serving as interface for the virtualisation providers
"""

# general notes
# most functions should either return
# return {'result': 'success'}
# or
# return {'result': 'failure', 'reason': reason}
# for instance
# return {'result': 'failure', 'reason': "VM %s not found" % name}


# your base class __init__ needs to define conn attribute and set it to None
# when backend cannot be reached
# it should also set debug from the debug variable passed in kcli client

import json
from kvirt import common
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests


class Kforeman(object):
    """

    """
    def __init__(self, host='127.0.0.1', port=443, user='root', password=None, debug=False, secure=True,
                 filtervms=False, filteruser=False):
        self.conn = 'foreman'
        self.debug = debug
        self.user = user
        self.password = password
        self.host = host.encode
        self.port = str(port)
        if port == 443 and secure:
            self.url = "https://%s/api" % (host)
        else:
            protocol = 'https' if secure else 'http'
            self.url = "%s://%s:%s/api" % (protocol, host, port)
        self.filteruser = filteruser
        self.filtervms = filtervms
        return

# should cleanly close your connection, if needed
    def close(self):
        """

        :return:
        """
        print("not implemented")
        return

    def exists(self, name):
        """

        :param name:
        :return:
        """
        dns = None
        if dns:
            name = "%s.%s" % (name, dns)
        res = self.self._foremando()
        for r in res['results']:
            currentname = r['name']
            if currentname == name:
                return True
        return False

    def net_exists(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

    def disk_exists(self, pool, name):
        """

        :param pool:
        :param name:
        """
        print("not implemented")

    def create(self, name, virttype='kvm', profile='', flavor=None, plan='kvirt',
               cpumodel='Westmere', cpuflags=[], numcpus=2, memory=512,
               guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True,
               diskinterface='virtio', nets=['default'], iso=None, vnc=False,
               cloudinit=True, reserveip=False, reservedns=False,
               reservehost=False, start=True, keys=None, cmds=[], ips=None,
               netmasks=None, gateway=None, nested=True, dns=None, domain=None,
               tunnel=False, files=[], enableroot=True, alias=[], overrides={},
               tags={}, dnsclient=None, storemetadata=False, sharedfolders=[], kernel=None, initrd=None,
               cmdline=None, cpuhotplug=False, memoryhotplug=False):
        """

        :param name:
        :param virttype:
        :param profile:
        :param flavor:
        :param plan:
        :param cpumodel:
        :param cpuflags:
        :param numcpus:
        :param memory:
        :param guestid:
        :param pool:
        :param image:
        :param disks:
        :param disksize:
        :param diskthin:
        :param diskinterface:
        :param nets:
        :param iso:
        :param vnc:
        :param cloudinit:
        :param reserveip:
        :param reservedns:
        :param reservehost:
        :param start:
        :param keys:
        :param cmds:
        :param ips:
        :param netmasks:
        :param gateway:
        :param nested:
        :param dns:
        :param domain:
        :param tunnel:
        :param files:
        :param enableroot:
        :param alias:
        :param overrides:
        :param tags:
        :return:
        """
        print("not implemented")
        ip = None
        mac = None
        operatingsystem = None
        environment = None
        arch = "x86_64"
        ptable = None
        powerup = None
        memory = None
        core = None
        compute = None
        hostgroup = None
        host, port, user, password, protocol = self.host, self.port, self.user, self.password, self.protocol
        name = name.encode('ascii')
        dns = dns.encode('ascii')
        if environment is None:
            environment = "production"
        if ip:
            ip = ip.encode('ascii')
        if mac:
            mac = mac.encode('ascii')
        if operatingsystem:
            operatingsystem = operatingsystem.encode('ascii')
        if environment:
            environment = environment.encode('ascii')
        if arch:
            arch = arch.encode('ascii')
        if ptable:
            ptable = ptable.encode('ascii')
        if powerup:
            powerup = powerup.encode('ascii')
        if memory:
            memory = memory.encode('ascii')
        if core:
            core = core.encode('ascii')
        if compute:
            compute = compute.encode('ascii')
        if hostgroup:
            hostgroup = hostgroup.encode('ascii')
        postdata = {}
        if dns:
            name = "%s.%s" % (name, dns)
        postdata['host'] = {'name': name}
        if operatingsystem:
            osid = self._foremangetid(protocol, host, port, user, password, 'operatingsystems', operatingsystem)
            postdata['host']['operatingsystem_id'] = osid
        envid = self._foremangetid(protocol, host, port, user, password, 'environments', environment)
        postdata['host']['environment_id'] = envid
        if arch:
            archid = self._foremangetid(protocol, host, port, user, password, 'architectures', arch)
            postdata['host']['architecture_id'] = archid
        if ptable:
            ptableid = self._foremangetid(protocol, host, port, user, password, 'partitiontables', ptable)
            postdata['host']['partitiontable_id'] = ptableid
        if not ip or not mac or not ptableid or not osid:
            postdata['host']['managed'] = False
        if ip:
            postdata['host']['ip'] = ip
        if mac:
            postdata['host']['mac'] = mac
        if compute:
            computeid = self._foremangetid(protocol, host, port, user, password, 'compute_resources', compute)
            postdata['host']['compute_resource_id'] = computeid
        if hostgroup:
            hostgroupid = self._foremangetid(protocol, host, port, user, password, 'hostgroups', hostgroup)
            postdata['host']['hostgroup_id'] = hostgroupid
        if ptable:
            ptableid = self._foremangetid(protocol, host, port, user, password, 'ptables', ptable)
            postdata['host']['ptable_id'] = ptableid
        result = self._foremando(where='hosts', actiontype="POST", postdata=postdata)
        if 'errors' not in result:
            print("%s created in Foreman" % name)
        else:
            print("%s not created in Foreman because %s" % (name, result["errors"][0]))
        return {'result': 'success'}

    def start(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def stop(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def snapshot(self, name, base, revert=False, delete=False, listing=False):
        """

        :param name:
        :param base:
        :param revert:
        :param delete:
        :param listing:
        :return:
        """
        print("not implemented")
        return

    def restart(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def report(self):
        """

        :return:
        """
        print("not implemented")
        return

    def status(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

# should return a sorted list of name, state, ip, source, plan, profile, report
    def list(self):
        """

        :return:
        """
        vms = []
        _filter = "owner_name=%" % self.user if self.filteruser else None
        res = self._foremando(_filter=_filter)
        for vm in res['results']:
            name = vm['name']
            vms.append(self.info(name, vm=vm))
        return vms

    def console(self, name, tunnel=False, web=False):
        """

        :param name:
        :param tunnel:
        :return:
        """
        print("not implemented")
        return

    def serialconsole(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

# should generate info in a dict and then pass it to
# print_info(yamlinfo, output=output, fields=fields, values=values)
# from kvirt.common where:
# yamlinfo is the dict
# with the following keys (you can omit the ones you want)
# name
# autostart
# plan
# profile
# image
# ip
# memory
# cpus
# creationdate
# nets list  of
# {'device': device, 'mac': mac, 'net': network, 'type': network_type}
# disks list of
# {'device': device, 'size': disksize, 'format': diskformat,
# 'type': drivertype, 'path': path}
# snapshots list of {'snapshot': snapshot, current: current}
# fields should be split with fields.split(',')
    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        """

        :param name:
        :param output:
        :param fields:
        :param values:
        :return:
        """
        if vm is None:
            vm = self._foremando(who=name)
        if self.debug:
            print(vars(vm))
        yamlinfo = {'name': name}
        plan, profile = 'N/A', 'N/A'
        state = 'up'
        cpus = 2
        memory = 1024
        image = vm['hostgroup_name']
        yamlinfo = {'name': name, 'image': image, 'plan': plan, 'profile': profile, 'status': state, 'cpus': cpus,
                    'memory': memory}
        yamlinfo['created_at'] = vm['created_at']
        yamlinfo['owner_name'] = vm['owner_name']
        yamlinfo['id'] = vm['id']
        nets = []
        if 'interfaces' in vm:
            for interface in vm['interfaces']:
                device = interface['identifier']
                mac = interface['mac']
                network = interface.get('subnet_name', 'N/A')
                network_type = interface.get('type', 'N/A')
                if 'ip' in interface:
                    yamlinfo['ip'] = vm['ip']
                nets.append({'device': device, 'mac': mac, 'net': network, 'type': network_type})
        if nets:
            yamlinfo['nets'] = nets
        return yamlinfo

# should return ip string
    def ip(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return None

# should return a list of available images, or isos ( if iso is set to True
    def volumes(self, iso=False):
        """

        :param iso:
        :return:
        """
        print("not implemented")
        return

    def delete(self, name, snapshots=False):
        """

        :param name:
        :param snapshots:
        :return:
        """
        print("not implemented")
        dns = None
        name = name.encode('ascii')
        if dns:
            dns = dns.encode('ascii')
            name = "%s.%s" % (name, dns)
        result = self._foremando(who=name, actiontype='DELETE')
        if result:
            print("%s deleted in Foreman" % name)
        else:
            print("Nothing to do in foreman")
        return {'result': 'success'}

# should return dnsclient, domain for the given vm
    def dnsinfo(self, name):
        """

        :param name:
        :return:
        """
        return None, None

    def clone(self, old, new, full=False, start=False):
        """

        :param old:
        :param new:
        :param full:
        :param start:
        :return:
        """
        print("not implemented")
        return

    def update_metadata(self, name, metatype, metavalue, append=False):
        """

        :param name:
        :param metatype:
        :param metavalue:
        :return:
        """
        print("not implemented")
        return

    def update_memory(self, name, memory):
        """

        :param name:
        :param memory:
        :return:
        """
        print("not implemented")
        return

    def update_cpus(self, name, numcpus):
        """

        :param name:
        :param numcpus:
        :return:
        """
        print("not implemented")
        return

    def update_start(self, name, start=True):
        """

        :param name:
        :param start:
        :return:
        """
        print("not implemented")
        return

    def update_information(self, name, information):
        """

        :param name:
        :param information:
        :return:
        """
        self.update_metadata(name, 'information', information)
        return

    def update_iso(self, name, iso):
        """

        :param name:
        :param iso:
        :return:
        """
        print("not implemented")
        return

    def update_flavor(self, name, flavor):
        """

        :param name:
        :param flavor:
        :return:
        """
        print("Not implemented")
        return {'result': 'success'}

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param image:
        :return:
        """
        print("not implemented")
        return

    def add_disk(self, name, size, pool=None, thin=True, image=None,
                 shareable=False, existing=None):
        """

        :param name:
        :param size:
        :param pool:
        :param thin:
        :param image:
        :param shareable:
        :param existing:
        :return:
        """
        print("not implemented")
        return

    def delete_disk(self, name, diskname, pool=None):
        """

        :param name:
        :param diskname:
        :param pool:
        :return:
        """
        print("not implemented")
        return

# should return a dict of {'pool': poolname, 'path': name}
    def list_disks(self):
        """

        :return:
        """
        print("not implemented")
        return

    def add_nic(self, name, network):
        """

        :param name:
        :param network:
        :return:
        """
        print("not implemented")
        return

    def delete_nic(self, name, interface):
        """

        :param name:
        :param interface:
        :return:
        """
        print("not implemented")
        return

# should return (user, ip)
    def _ssh_credentials(self, name):
        ip, user = None, 'root'
        vm = self._foremando(who=name)
        image = vm['hostgroup_name']
        if image is not None:
            user = common.get_user(image)
        for interface in vm['interfaces']:
            if 'ip' in interface:
                ip = vm['ip']
                break
        return user, ip

    def ssh(self, name, user=None, local=None, remote=None, tunnel=False,
            insecure=False, cmd=None, X=False, Y=False, D=None):
        """

        :param name:
        :param user:
        :param local:
        :param remote:
        :param tunnel:
        :param insecure:
        :param cmd:
        :param X:
        :param Y:
        :param D:
        :return:
        """
        u, ip = self._ssh_credentials(name)
        if user is None:
            user = u
        sshcommand = common.ssh(name, ip=ip, user=user, local=local, remote=remote, tunnel=tunnel, insecure=insecure,
                                cmd=cmd, X=X, Y=Y, D=D, debug=self.debug)
        return sshcommand

    def scp(self, name, user=None, source=None, destination=None, tunnel=False,
            download=False, recursive=False):
        """

        :param name:
        :param user:
        :param source:
        :param destination:
        :param tunnel:
        :param download:
        :param recursive:
        :return:
        """
        u, ip = self._ssh_credentials(name)
        if ip is None:
            return None
        if user is None:
            user = u
        scpcommand = common.scp(name, ip=ip, user=user, source=source, destination=destination, recursive=recursive,
                                tunnel=tunnel, debug=self.debug, download=False)
        return scpcommand

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        """

        :param name:
        :param poolpath:
        :param pooltype:
        :param user:
        :param thinpool:
        :return:
        """
        print("not implemented")
        return

    def delete_image(self, image):
        """

        :param image:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def add_image(self, image, pool, short=None, cmd=None, name=None, size=1):
        """

        :param image:
        :param pool:
        :param short:
        :param cmd:
        :param name:
        :param size:
        :return:
        """
        print("not implemented")
        return {'result': 'success'}

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None,
                       plan='kvirt', pxe=None, vlan=None):
        """

        :param name:
        :param cidr:
        :param dhcp:
        :param nat:
        :param domain:
        :param plan:
        :param pxe:
        :param vlan:
        :return:
        """
        print("not implemented")
        return

    def delete_network(self, name=None):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

# should return a dict of pool strings
    def list_pools(self):
        """

        :return:
        """
        print("not implemented")
        return

    def list_networks(self):
        """

        :return:
        """
        print("not implemented")
        return {}

    def list_subnets(self):
        """

        :return:
        """
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        """

        :param name:
        :param full:
        :return:
        """
        print("not implemented")
        return

    def network_ports(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return

    def vm_ports(self, name):
        """

        :param name:
        :return:
        """
        print("not implemented")
        return ['default']

# returns the path of the pool, if it makes sense. used by kcli list --pools
    def get_pool_path(self, pool):
        """

        :param pool:
        :return:
        """
        print("not implemented")
        return

# return a list of [name, numcpus, memory] for each flavor, if the platform has this concept
    def flavors(self):
        """

        :return:
        """
        return []

# export the primary disk of the corresponding instance so it's available as a image
    def export(name, image=None):
        """

        :param image:
        :return:
        """
        return

    def _foremando(self, where='hosts', who=None, actiontype=None, postdata=None, _filter=None):
        # url = "%s://%s:%s/api/v2/puppetclasses?search=environment+=+%s" % (protocol, host, port, environment)
        url = "%s/%s" % (self.url, where)
        url += "/%s" % who if who is not None else "?per_page=10000"
        if _filter is not None:
            url += _filter
        user = self.user
        password = self.password
        headers = {'content-type': 'application/json', 'Accept': 'application/json'}
        # get environments
        # if user and password:
        #    user = user.encode('ascii')
        #    password = password.encode('ascii')
        if actiontype == 'POST':
            r = requests.post(url, verify=False, headers=headers, auth=(user, password), data=json.dumps(postdata))
        elif actiontype == 'DELETE':
            r = requests.delete(url, verify=False, headers=headers, auth=(user, password), data=postdata)
        elif actiontype == 'PUT':
            r = requests.put(url, verify=False, headers=headers, auth=(user, password), data=postdata)
        else:
            r = requests.get(url, verify=False, headers=headers, auth=(user, password))
        try:
            result = r.json()
            result = eval(str(result))
            return result
        except:
            return None

    def _foremangetid(self, searchtype, searchname):
        if searchtype == 'puppet':
            # url = "%s/apismart_proxies?type=%s" % (url, searchtype)
            result = self._foremando(where='apismart_proxies', searchtype=searchtype)
            return result[0]['smart_proxy']['id']
        else:
            # url = "%s/api/v2/%s/%s" % (url, searchtype, searchname)
            result = self._foremando(where=searchtype, who=searchname)
        if searchtype == 'ptables':
            shortname = 'ptable'
        elif searchtype.endswith('es') and searchtype != 'architectures':
            shortname = searchtype[:-2]
        else:
            shortname = searchtype[:-1]
        try:
            return str(result[shortname]['id'])
        except:
            return str(result['id'])

    def list_dns(self, domain):
        """

        :param domain:
        :return:
        """
        return []
