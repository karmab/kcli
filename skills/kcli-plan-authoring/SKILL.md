---
name: kcli-plan-authoring
description: Guides creation of kcli plan files for deploying VMs, networks, and infrastructure. Use when writing YAML plans with Jinja2 templating or debugging plan execution issues.
---

# kcli Plan Authoring

## Plan File Structure

Plans are YAML files with Jinja2 templating. Resources are defined as top-level keys with a `type` field.

```yaml
parameters:
  param1: value1
  param2: value2

resourcename:
  type: resourcetype
  key1: value1
  key2: {{ param1 }}
```

## Resource Types

### VM (default if no type specified)
```yaml
myvm:
  image: fedora40
  memory: 4096
  numcpus: 2
  disks:
    - size: 20
    - size: 10
      pool: otherpool
  nets:
    - name: default
    - name: mynet
      ip: 192.168.1.10
      netmask: 255.255.255.0
      gateway: 192.168.1.1
  cmds:
    - echo hello > /tmp/test
  files:
    - path: /etc/myconfig
      content: |
        key=value
```

### Profile
```yaml
myprofile:
  type: profile
  image: centos9stream
  memory: 2048
  numcpus: 2
  disks:
    - 10
  nets:
    - default
```

### Network
```yaml
mynetwork:
  type: network
  cidr: 192.168.100.0/24
  dhcp: true
  nat: true
  domain: mylab.local
```

### Image
```yaml
myimage:
  type: image
  url: https://example.com/image.qcow2
  pool: default
```

### Container
```yaml
mycontainer:
  type: container
  image: nginx:latest
  ports:
    - 8080:80
```

## Jinja2 Templating

### Parameter Substitution
```yaml
parameters:
  cluster_name: mycluster
  worker_count: 3

{{ cluster_name }}-master:
  image: rhcos
  
{% for i in range(worker_count) %}
{{ cluster_name }}-worker-{{ i }}:
  image: rhcos
{% endfor %}
```

### Conditionals
```yaml
parameters:
  enable_storage: true

myvm:
  image: fedora40
{% if enable_storage %}
  disks:
    - size: 100
{% endif %}
```

### Custom Filters
kcli provides custom Jinja2 filters in `kvirt/jinjafilters/jinjafilters.py`:

**Path/File Filters:**
- `basename` - Get filename from path
- `dirname` - Get directory from path
- `diskpath` - Convert to /dev/ path if needed
- `exists` - Check if file/path exists
- `pwd_path` - Handle workdir paths in containers
- `real_path` - Get real/absolute path
- `read_file` - Read file contents

**String/Data Filters:**
- `none` - Return empty string if None
- `type` - Return type name (string, int, dict, list)
- `base64` - Base64 encode value
- `certificate` - Wrap in BEGIN/END CERTIFICATE if needed
- `count` - Count occurrences of character

**Kubernetes/Cluster Filters:**
- `kubenodes` - Generate node names for cluster
- `defaultnodes` - Generate default node list
- `has_ctlplane` - Check if list has ctlplane/master entries

**Version/Release Filters:**
- `github_version` - Get latest version from GitHub releases
- `min_ocp_version` - Compare OpenShift versions (minimum)
- `max_ocp_version` - Compare OpenShift versions (maximum)

**Network Filters:**
- `local_ip` - Get local IP for network interface
- `network_ip` - Get IP from network CIDR
- `ipv6_wrap` - Wrap IPv6 addresses in brackets

**Utility Filters:**
- `kcli_info` - Get VM info via kcli command
- `find_manifests` - Find YAML manifests in directory
- `wait_crd` - Generate wait script for CRD creation
- `wait_csv` - Generate wait script for CSV readiness
- `filter_bgp_peers` - Filter BGP peer list

Standard Jinja2 filters (default, join, upper, lower, etc.) also work

## Parameter Files

Create `kcli_parameters.yml` alongside your plan:
```yaml
cluster_name: prod
worker_count: 5
memory: 8192
```

Override at runtime:
```bash
kcli create plan -f myplan.yml -P worker_count=10 myplan
```

## Common VM Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `numcpus` | 2 | Number of CPUs |
| `memory` | 512 | Memory in MB |
| `pool` | default | Storage pool |
| `image` | None | Base image name |
| `nets` | [default] | Network list |
| `disks` | [{size:10}] | Disk list |
| `cmds` | [] | Post-boot commands |
| `files` | [] | Files to inject |
| `keys` | [] | SSH public keys |
| `start` | true | Auto-start VM |
| `cloudinit` | true | Enable cloud-init |

## Plan Execution

```bash
# Create plan
kcli create plan -f myplan.yml myplanname

# Create with parameter overrides
kcli create plan -f myplan.yml -P memory=4096 -P image=fedora40 myplanname

# List plans
kcli list plan

# Get plan info
kcli info plan myplanname

# Delete plan (and all its resources)
kcli delete plan myplanname

# Update existing plan
kcli update plan -f myplan.yml myplanname
```

## Debugging Plans

1. **Validate YAML syntax** - Use `python -c "import yaml; yaml.safe_load(open('plan.yml'))"`
2. **Check Jinja2 rendering** - Look for unbalanced `{{` `}}` or `{% %}`
3. **Run with debug** - `kcli -d create plan -f plan.yml test`
4. **Check dependencies** - Ensure images/networks exist before VMs reference them

## Example: Multi-VM Plan

```yaml
parameters:
  domain: lab.local
  base_image: centos9stream

labnetwork:
  type: network
  cidr: 10.0.0.0/24
  dhcp: true
  domain: {{ domain }}

webserver:
  image: {{ base_image }}
  memory: 2048
  nets:
    - labnetwork
  cmds:
    - dnf -y install nginx
    - systemctl enable --now nginx

database:
  image: {{ base_image }}
  memory: 4096
  disks:
    - size: 20
    - size: 50
  nets:
    - labnetwork
  cmds:
    - dnf -y install postgresql-server
    - postgresql-setup --initdb
```
