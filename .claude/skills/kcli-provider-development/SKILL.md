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
- `delete(name, snapshots=False, keep_disks=False)` - Delete VM
- `list()` - Return list of `[name, state, ip, source, plan, profile]`
- `info(name, output, fields, values, vm, debug)` - Return VM details dict
- `exists(name)` - Check if VM exists
- `status(name)` - Return VM status
- `ip(name)` - Return IP string

**Storage:**
- `create_pool(name, poolpath, pooltype, user, thinpool)`
- `delete_pool(name, full)`
- `list_pools()` - Return list of pool names
- `add_disk(name, size, pool, thin, image, shareable, existing, interface, novm, overrides)`
- `delete_disk(name, diskname, pool, novm)`
- `list_disks()` - Return dict `{'diskname': {'pool': poolname, 'path': name}}`

**Networking:**
- `create_network(name, cidr, dhcp, nat, domain, plan, overrides)`
- `delete_network(name, cidr, force)`
- `list_networks()` - Return dict of networks
- `net_exists(name)`
- `add_nic(name, network, model)`
- `delete_nic(name, interface)`

**Images:**
- `volumes(iso=False, extended=False)` - List available images
- `add_image(url, pool, short, cmds, name, size, convert)`
- `delete_image(image, pool)`

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
- `kvirt/providers/kvm/` - Libvirt (most complete reference)
- `kvirt/providers/aws/` - AWS cloud
- `kvirt/providers/fake/` - Minimal stub for testing
