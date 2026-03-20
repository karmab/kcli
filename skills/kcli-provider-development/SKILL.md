---
name: kcli-provider-development
description: Guides implementation of new virtualization providers for kcli. Use when adding support for a new cloud platform, hypervisor, or infrastructure provider.
---

# kcli Provider Development

## Provider Architecture

Providers are located in `kvirt/providers/` as subdirectories. Each provider implements the interface defined in `kvirt/providers/sampleprovider.py` (class `Kbase`).

## Required Implementation Steps

### 1. Create Provider Directory
```
kvirt/providers/yourprovider/
├── __init__.py      # Contains your Kyourprovider class
└── (optional helpers)
```

### 2. Implement the Provider Class

Your class must:
- Set `self.conn` attribute in `__init__` (set to `None` if backend unreachable)
- Set `self.debug` from the debug parameter
- Return standardized response dicts from methods

**Return Value Pattern:**
```python
# Success
return {'result': 'success'}

# Failure
return {'result': 'failure', 'reason': "VM %s not found" % name}
```

### 3. Core Methods to Implement

**VM Lifecycle (required):**
- `create()` - Create VM with all parameters (cpus, memory, disks, nets, etc.)
- `start(name)` - Start VM
- `stop(name, soft=False)` - Stop VM
- `restart(name)` - Restart VM (default calls start)
- `delete(name, snapshots=False, keep_disks=False)` - Delete VM
- `list()` - Return list of `[name, state, ip, source, plan, profile]`
- `info(name, output, fields, values, vm, debug)` - Return VM details dict
- `exists(name)` - Check if VM exists
- `status(name)` - Return VM status
- `ip(name)` - Return IP string
- `clone(old, new, full=False, start=False)` - Clone VM
- `export(name, image=None)` - Export VM as image
- `console(name, tunnel, tunnelhost, tunnelport, tunneluser, web)` - Graphical console
- `serialconsole(name, web)` - Serial console

**Storage:**
- `create_pool(name, poolpath, pooltype, user, thinpool)`
- `delete_pool(name, full)`
- `list_pools()` - Return list of pool names
- `get_pool_path(pool)` - Get pool path
- `add_disk(name, size, pool, thin, image, shareable, existing, interface, novm, overrides)`
- `delete_disk(name, diskname, pool, novm)`
- `create_disk(name, size, pool, thin, image)` - Create standalone disk
- `list_disks()` - Return dict `{'diskname': {'pool': poolname, 'path': name}}`
- `disk_exists(pool, name)` - Check if disk exists
- `detach_disks(name)` - Detach all disks from VM

**Networking:**
- `create_network(name, cidr, dhcp, nat, domain, plan, overrides)`
- `delete_network(name, cidr, force)`
- `update_network(name, dhcp, nat, domain, plan, overrides)`
- `list_networks()` - Return dict of networks
- `info_network(name)` - Get network info
- `net_exists(name)` - Check if network exists
- `network_ports(name)` - List ports on network
- `add_nic(name, network, model)`
- `delete_nic(name, interface)`
- `update_nic(name, index, network)` - Update NIC

**Subnets (cloud providers):**
- `create_subnet(name, cidr, dhcp, nat, domain, plan, overrides)`
- `delete_subnet(name, force)`
- `update_subnet(name, overrides)`
- `list_subnets()` - Return subnet dict
- `info_subnet(name)` - Get subnet info

**Images:**
- `volumes(iso=False, extended=False)` - List available images
- `add_image(url, pool, short, cmds, name, size, convert)`
- `delete_image(image, pool)`

**Snapshots:**
- `create_snapshot(name, base)` - Create snapshot
- `delete_snapshot(name, base)` - Delete snapshot
- `list_snapshots(base)` - List snapshots (returns list)
- `revert_snapshot(name, base)` - Revert to snapshot

**Update Operations:**
- `update_metadata(name, metatype, metavalue, append)`
- `update_memory(name, memory)`
- `update_cpus(name, numcpus)`
- `update_start(name, start)` - Set autostart
- `update_information(name, information)` - Update info metadata
- `update_iso(name, iso)` - Change attached ISO
- `update_flavor(name, flavor)` - Change VM flavor

**Buckets (object storage):**
- `create_bucket(bucket, public)` - Create storage bucket
- `delete_bucket(bucket)` - Delete bucket
- `list_buckets()` - List all buckets
- `list_bucketfiles(bucket)` - List files in bucket
- `upload_to_bucket(bucket, path, overrides, temp_url, public)`
- `download_from_bucket(bucket, path)`
- `delete_from_bucket(bucket, path)`

**Security Groups (cloud providers):**
- `create_security_group(name, overrides)`
- `delete_security_group(name)`
- `update_security_group(name, overrides)`
- `list_security_groups(network)` - List security groups

**DNS:**
- `reserve_dns(name, nets, domain, ip, alias, force, primary, instanceid)`
- `list_dns_zones()` - List DNS zones
- `dnsinfo(name)` - Return (dnsclient, domain) for VM

**Other:**
- `close()` - Clean up connection
- `info_host()` - Return host info dict
- `vm_ports(name)` - List ports on VM
- `list_flavors()` - Return `[[name, numcpus, memory], ...]` if platform supports flavors

### 4. Register Provider in config.py

Add import and instantiation in `kvirt/config.py` (around lines 102-220):

```python
elif self.type == 'yourprovider':
    # Get provider-specific options
    option1 = options.get('option1')
    if option1 is None:
        error("Missing option1 in configuration. Leaving")
        sys.exit(1)
    try:
        from kvirt.providers.yourprovider import Kyourprovider
    except Exception as e:
        exception = e if debug else None
        dependency_error('yourprovider', exception)
    k = Kyourprovider(option1=option1, debug=debug)
```

### 5. Add Dependencies to setup.py

```python
YOURPROVIDER = ['required-package1', 'required-package2']

# Add to extras_require dict:
extras_require={
    'yourprovider': YOURPROVIDER,
    # ...
}

# Add to ALL list if needed:
ALL = EXTRAS + AWS + ... + YOURPROVIDER
```

## Info Method Structure

The `info()` method should build a dict with these keys:
- `name`, `autostart`, `plan`, `profile`, `image`, `ip`, `memory`, `numcpus`, `creationdate`
- `nets`: list of `{'device': device, 'mac': mac, 'net': network, 'type': network_type}`
- `disks`: list of `{'device': device, 'size': disksize, 'format': diskformat, 'type': drivertype, 'path': path}`
- `snapshots`: list of `{'snapshot': snapshot, 'current': current}`

Then call: `common.print_info(yamlinfo, output=output, fields=fields, values=values)`

## Reference Implementations

Study these existing providers:
- `kvirt/providers/kvm/` - Libvirt (most complete reference, ~4300 lines)
- `kvirt/providers/aws/` - AWS cloud (~2200 lines)
- `kvirt/providers/gcp/` - Google Cloud Platform (~2100 lines)
- `kvirt/providers/kubevirt/` - KubeVirt on Kubernetes (~1900 lines)
- `kvirt/providers/vsphere/` - VMware vSphere (~1900 lines)
- `kvirt/providers/azure/` - Microsoft Azure (~1500 lines)
- `kvirt/providers/ibm/` - IBM Cloud (~1500 lines)
- `kvirt/providers/ovirt/` - oVirt/RHV (~1400 lines)
- `kvirt/providers/openstack/` - OpenStack (~1350 lines)
- `kvirt/providers/proxmox/` - Proxmox VE (~1200 lines)
- `kvirt/providers/hcloud/` - Hetzner Cloud (~550 lines)
- `kvirt/providers/web/` - Web-based provider (~530 lines)
- `kvirt/providers/fake/` - Minimal stub for testing (~20 lines)

## Provider Complexity Guide

Not all providers need to implement every method. Focus on:

1. **Minimum viable**: `create`, `delete`, `list`, `info`, `start`, `stop`, `exists`, `status`, `ip`
2. **Storage**: `add_disk`, `delete_disk`, `list_disks`, `create_pool`, `delete_pool`, `list_pools`
3. **Networking**: `create_network`, `delete_network`, `list_networks`, `net_exists`
4. **Images**: `volumes`, `add_image`, `delete_image`
5. **Advanced**: Snapshots, cloning, export, buckets, security groups (as needed)

Methods can return `{'result': 'success'}` with a `print("not implemented")` for optional features.
