# -*- coding: utf-8 -*-

from inspect import signature
from kvirt import common
from kvirt.common import pprint, error, success
import os
import json
import ssl
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import webbrowser


class Kwebclient(object):
    def __init__(self, host='127.0.0.1', port=8000, debug=False, localkube=True):
        self.debug = debug
        self.conn = 'web'
        self.base = f'http://{host}:{port}'
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        self.context = ssl.create_default_context()
        self.context.check_hostname = False
        self.context.verify_mode = ssl.CERT_NONE
        self.localkube = localkube

    def close(self):
        return

    def exists(self, name):
        url = f"{self.base}/vms/{name}"
        request = Request(url, headers=self.headers)
        result = json.loads(urlopen(request, context=self.context).read())
        return bool(result)

    def net_exists(self, name):
        return name in self.list_networks()

    def disk_exists(self, pool, name):
        print("not implemented")

    def create(self, name, virttype=None, profile='', flavor=None, plan='kvirt', cpumodel='host-model',
               cpuflags=[], cpupinning=[], numcpus=2, memory=512, guestid='guestrhel764', pool='default', image=None,
               disks=[{'size': 10}], disksize=10, diskthin=True, diskinterface='virtio', nets=['default'], iso=None,
               vnc=True, cloudinit=True, reserveip=False, reservedns=False, reservehost=False, start=True, keys=[],
               cmds=[], ips=None, netmasks=None, gateway=None, nested=True, dns=None, domain=None, tunnel=False,
               files=[], enableroot=True, overrides={}, tags=[], storemetadata=False, sharedfolders=[], kernel=None,
               initrd=None, cmdline=None, placement=[], autostart=False, cpuhotplug=False, memoryhotplug=False,
               numamode=None, numa=[], pcidevices=[], tpm=False, rng=False, metadata={}, securitygroups=[],
               vmuser=None):
        vms_url = f"{self.base}/vms"
        sig = signature(Kwebclient.create)
        data = dict(sig.bind(self, name, virttype, profile, flavor, plan, cpumodel, cpuflags, cpupinning, numcpus,
                             memory, guestid, pool, image, disks, disksize, diskthin, diskinterface, nets, iso,
                             vnc, cloudinit, reserveip, reservedns, reservehost, start, keys,
                             cmds, ips, netmasks, gateway, nested, dns, domain, tunnel,
                             files, enableroot, overrides, tags, storemetadata, sharedfolders, kernel,
                             initrd, cmdline, placement, autostart, cpuhotplug, memoryhotplug,
                             numamode, numa, pcidevices, tpm, rng, metadata, securitygroups, vmuser).arguments)
        del data['self']
        data = json.dumps(data).encode('utf-8')
        request = Request(vms_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def start(self, name):
        start_url = f"{self.base}/vms/{name}/start"
        data = json.dumps({}).encode('utf-8')
        request = Request(start_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def stop(self, name, soft=False):
        stop_url = f"{self.base}/vms/{name}/stop"
        data = json.dumps({}).encode('utf-8')
        request = Request(stop_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def create_snapshot(self, name, base):
        snapshot_url = f"{self.base}/snapshots/{base}"
        data = {'snapshot': name}
        data = json.dumps(data).encode('utf-8')
        request = Request(snapshot_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def delete_snapshot(self, name, base):
        snapshot_url = f"{self.base}/snapshots/{base}"
        data = {'snapshot': name}
        data = json.dumps(data).encode('utf-8')
        request = Request(snapshot_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def list_snapshots(self, base):
        if not self.exists(base):
            return {'result': 'failure', 'reason': f"VM {base} not found"}
        url = f"{self.base}/snapshots/{base}"
        request = Request(url, headers=self.headers)
        return json.loads(urlopen(request, context=self.context).read())['snapshots']

    def revert_snapshot(self, name, base):
        revert_url = f"{self.base}/snapshots/{base}/revert"
        data = {'snapshot': name}
        data = json.dumps(data).encode('utf-8')
        request = Request(revert_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def restart(self, name):
        return self.start(name)

    def info_host(self):
        info_url = f"{self.base}/host"
        request = Request(info_url, headers=self.headers)
        result = json.loads(urlopen(request, context=self.context).read())
        return result

    def status(self, name):
        url = f"{self.base}/vms/{name}"
        request = Request(url, headers=self.headers)
        result = json.loads(urlopen(request, context=self.context).read())
        return result.get('status')

    def list(self):
        url = f"{self.base}/vms"
        request = Request(url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        vms = response['vms']
        return vms

    def console(self, name, tunnel=False, tunnelhost=None, tunnelport=22, tunneluser='root', web=False):
        url = f'{self.base}/vmconsole/{name}'
        pprint(f"Opening web console {url}")
        webbrowser.open(url, new=2, autoraise=True)

    def serialconsole(self, name, web=False):
        print("not implemented")

    def info(self, name, output='plain', fields=[], values=False, vm=None, debug=False):
        url = f"{self.base}/vms/{name}"
        request = Request(url, headers=self.headers)
        result = json.loads(urlopen(request, context=self.context).read())
        if not result:
            error(f"VM {name} not found")
        return result

    def ip(self, name):
        url = f"{self.base}/vms/{name}"
        request = Request(url, headers=self.headers)
        result = json.loads(urlopen(request, context=self.context).read())
        return result.get('ip')

    def volumes(self, iso=False):
        _type = 'isos' if iso else 'images'
        url = f"{self.base}/{_type}"
        request = Request(url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response[_type]

    def delete(self, name, snapshots=False):
        vm_url = f"{self.base}/vms/{name}"
        data = json.dumps({'snapshots': snapshots}).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def dnsinfo(self, name):
        url = f"{self.base}/vms/{name}"
        request = Request(url, headers=self.headers)
        result = json.loads(urlopen(request, context=self.context).read())
        return result.get('dnsclient'), result.get('domain')

    def clone(self, old, new, full=False, start=False):
        print("not implemented")

    def update_metadata(self, name, metatype, metavalue, append=False):
        vm_url = f"{self.base}/vms/{name}"
        data = {metatype: metavalue}
        data = json.dumps(data).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def update_memory(self, name, memory):
        vm_url = f"{self.base}/vms/{name}"
        data = {'memory': memory}
        data = json.dumps(data).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def update_cpus(self, name, numcpus):
        vm_url = f"{self.base}/vms/{name}"
        data = {'numcpus': numcpus}
        data = json.dumps(data).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def update_start(self, name, start=True):
        vm_url = f"{self.base}/vms/{name}"
        data = {'start': start}
        data = json.dumps(data).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def update_information(self, name, information):
        self.update_metadata(name, 'information', information)

    def update_iso(self, name, iso):
        vm_url = f"{self.base}/vms/{name}"
        data = {'iso': iso}
        data = json.dumps(data).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def update_flavor(self, name, flavor):
        vm_url = f"{self.base}/vms/{name}"
        data = {'flavor': flavor}
        data = json.dumps(data).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def create_disk(self, name, size, pool=None, thin=True, image=None):
        print("not implemented")

    def add_disk(self, name, size=1, pool=None, thin=True, image=None, shareable=False, existing=None,
                 interface='virtio', novm=False, overrides={}, diskname=None):
        if not self.exists(name):
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        if size < 1:
            error("Incorrect size.Leaving...")
            return {'result': 'failure', 'reason': "Incorrect size"}
        disk_url = f"{self.base}/disks/{name}"
        data = {'size': size, 'pool': pool}
        data = json.dumps(data).encode('utf-8')
        request = Request(disk_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def delete_disk(self, name, diskname, pool=None, novm=False):
        disk_url = f"{self.base}/disks/{name}"
        data = {'disk': diskname}
        data = json.dumps(data).encode('utf-8')
        request = Request(disk_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def list_disks(self):
        print("not implemented")
        return []

    def add_nic(self, name, network, model='virtio'):
        if not self.exists(name):
            error(f"VM {name} not found")
            return {'result': 'failure', 'reason': f"VM {name} not found"}
        nic_url = f"{self.base}/nics/{name}"
        data = {'network': network, 'name': name, 'model': model}
        data = json.dumps(data).encode('utf-8')
        request = Request(nic_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def delete_nic(self, name, interface):
        nic_url = f"{self.base}/nics/{name}"
        data = {'nic': interface}
        data = json.dumps(data).encode('utf-8')
        request = Request(nic_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def create_pool(self, name, poolpath, pooltype='dir', user='qemu', thinpool=None):
        pool_url = f"{self.base}/pools"
        data = {'pool': name, 'path': poolpath, 'type': pooltype}
        data = json.dumps(data).encode('utf-8')
        request = Request(pool_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def delete_image(self, image, pool=None):
        image_url = f"{self.base}/images/{os.path.basename(image)}"
        data = {'pool': pool} if pool is not None else {}
        data = json.dumps(data).encode('utf-8')
        request = Request(image_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def add_image(self, url, pool, short=None, cmd=None, name=None, size=None, convert=False):
        image_url = f"{self.base}/images"
        data = {'url': url, 'pool': pool, 'convert': convert}
        if name is not None:
            data['image'] = name
        if cmd is not None:
            data['cmd'] = cmd
        if size is not None:
            data['size'] = size
        data = json.dumps(data).encode('utf-8')
        request = Request(image_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def create_network(self, name, cidr=None, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        networks = self.list_networks()
        if name in networks:
            msg = f"Network {name} already exists"
            return {'result': 'failure', 'reason': msg}
        networks_url = f"{self.base}/networks"
        data = {'network': name, 'cidr': cidr, 'dhcp': dhcp, 'isolated': not nat}
        data = json.dumps(data).encode('utf-8')
        request = Request(networks_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def delete_network(self, name=None, cidr=None, force=False):
        if name not in self.list_networks():
            return {'result': 'failure', 'reason': f"Network {name} not found"}
        machines = self.network_ports(name)
        if machines:
            machines = ','.join(machines)
            return {'result': 'failure', 'reason': f"Network {name} is being used by {machines}"}
        network_url = f"{self.base}/networks/{name}"
        data = json.dumps({}).encode('utf-8')
        request = Request(network_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def list_pools(self):
        url = f"{self.base}/pools"
        request = Request(url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return [pool[0] for pool in response['pools']]

    def list_networks(self):
        url = f"{self.base}/networks"
        request = Request(url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        networks = response['networks']
        return networks

    def info_network(self, name):
        networkinfo = common.info_network(self, name)
        if self.debug and networkinfo:
            print(networkinfo)
        return networkinfo

    def list_subnets(self):
        print("not implemented")
        return {}

    def delete_pool(self, name, full=False):
        pool_url = f"{self.base}/pools/{name}"
        data = json.dumps({}).encode('utf-8')
        request = Request(pool_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def network_ports(self, name):
        machines = []
        url = f"{self.base}/vms"
        request = Request(url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        for vm in response['vms']:
            vm_name = vm['name']
            nets = vm.get('nets', [])
            for net in nets:
                if net['net'] == name:
                    machines.append(vm_name)
        return machines

    def vm_ports(self, name):
        networks = []
        url = f"{self.base}/vms/{name}"
        request = Request(url, headers=self.headers)
        vm = json.loads(urlopen(request, context=self.context).read())
        for net in vm.get('nets', []):
            networks.append(net['net'])
        return networks

    def get_pool_path(self, pool):
        url = f"{self.base}/pools"
        request = Request(url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        for p in response['pools']:
            if p[0] == pool:
                return p[1]

    def list_flavors(self):
        return []

    def export(self, name, image=None):
        print("not implemented")

    def create_bucket(self, bucket, public=False):
        print("not implemented")

    def delete_bucket(self, bucket):
        print("not implemented")

    def delete_from_bucket(self, bucket, path):
        print("not implemented")

    def download_from_bucket(self, bucket, path):
        print("not implemented")

    def upload_to_bucket(self, bucket, path, overrides={}, temp_url=False, public=False):
        print("not implemented")

    def list_buckets(self):
        print("not implemented")
        return []

    def list_bucketfiles(self, bucket):
        print("not implemented")
        return []

    def reserve_dns(self, name, nets=[], domain=None, ip=None, alias=[], force=False, primary=False):
        print("not implemented")

    def update_nic(self, name, index, network):
        vm_url = f"{self.base}/vms/{name}"
        data = {'index': index, 'network': network}
        data = json.dumps(data).encode('utf-8')
        request = Request(vm_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def update_network(self, name, dhcp=None, nat=None, domain=None, plan=None, overrides={}):
        network_url = f"{self.base}/networks/{name}"
        data = {}
        if dhcp is not None:
            data['dhcp'] = dhcp
        if nat is not None:
            data['nat'] = nat
        if domain is not None:
            data['domain'] = domain
        if plan is not None:
            data['plan'] = plan
        if overrides:
            data['overrides'] = overrides
        data = json.dumps(data).encode('utf-8')
        request = Request(network_url, data=data, headers=self.headers, method='UPDATE')
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def list_security_groups(self, network=None):
        print("not implemented")
        return []

    def create_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_security_group(self, name):
        print("not implemented")
        return {'result': 'success'}

    def update_security_group(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def create_kube(self, cluster, kubetype, overrides={}):
        kubes_url = f"{self.base}/kubes"
        overrides['cluster'] = cluster
        overrides['kubetype'] = kubetype
        data = json.dumps(overrides).encode('utf-8')
        request = Request(kubes_url, data=data, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        if response['result'] != 'success':
            error("Hit {response['reason']}")
        return response

    def delete_kube(self, cluster, kubetype, overrides={}):
        pprint(f"Deleting cluster {cluster}")
        kubes_url = f"{self.base}/kubes/{cluster}"
        overrides['kubetype'] = kubetype
        data = json.dumps(overrides).encode('utf-8')
        request = Request(kubes_url, data=data, headers=self.headers, method='DELETE')
        response = json.loads(urlopen(request, context=self.context).read())
        if response['result'] == 'success':
            success(f"Cluster {cluster} deleted")
        else:
            error("Hit {response['reason']}")
        return response

    def list_kubes(self):
        kubes_url = f"{self.base}/kubes"
        request = Request(kubes_url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response['kubes']

    def download_kubeconfig(self, kube):
        kubeconfig_url = f"{self.base}/kubes/{kube}/kubeconfig"
        request = Request(kubeconfig_url, headers=self.headers)
        try:
            return urlopen(request, context=self.context).read()
        except HTTPError:
            return None

    def info_specific_kube(self, kube):
        kube_url = f"{self.base}/kubes/{kube}"
        request = Request(kube_url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def info_subnet(self, name):
        print("not implemented")
        return {}

    def create_subnet(self, name, cidr, dhcp=True, nat=True, domain=None, plan='kvirt', overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def delete_subnet(self, name, force=False):
        print("not implemented")
        return {'result': 'success'}

    def update_subnet(self, name, overrides={}):
        print("not implemented")
        return {'result': 'success'}

    def list_dns_zones(self):
        print("not implemented")
        return []
