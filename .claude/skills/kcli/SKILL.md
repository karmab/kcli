---
name: kcli
description: Comprehensive guide for kcli usage. Use when creating VMs, deploying plans, managing clusters, or performing any kcli operations. Covers all common user workflows.
---

# kcli User Guide

kcli is a unified CLI for managing virtual infrastructure across multiple providers (Libvirt/KVM, AWS, GCP, Azure, vSphere, KubeVirt, OpenStack, oVirt, Proxmox, Hetzner, IBM Cloud).

## Quick Reference

```bash
# VM Operations
kcli create vm -i <image> <name>      # Create VM
kcli list vm                          # List VMs
kcli ssh <name>                       # SSH into VM
kcli console <name>                   # Graphical console
kcli start/stop/restart vm <name>     # Control VM state
kcli delete vm <name>                 # Delete VM

# Plans (Infrastructure as Code)
kcli create plan -f plan.yml <name>   # Deploy plan
kcli list plan                        # List plans
kcli delete plan <name>               # Delete plan and resources

# Kubernetes Clusters
kcli create kube <type> <name>        # Deploy cluster
kcli list kube                        # List clusters
kcli delete kube <name>               # Delete cluster

# Images
kcli list available-images            # Show downloadable images
kcli download image <name>            # Download cloud image
kcli list image                       # List local images

# Infrastructure
kcli list network / pool / host       # List resources
kcli create network -c <cidr> <name>  # Create network
kcli create pool -p <path> <name>     # Create storage pool
```

## Creating VMs

### Basic VM Creation
```bash
# From cloud image (downloads if needed)
kcli create vm -i fedora40 myvm

# Shorthand (kcli remembers last VM)
kcli ssh                              # SSH to last created VM
```

### With Custom Resources
```bash
kcli create vm -i centos9stream \
  -P memory=4096 \
  -P numcpus=4 \
  -P disks=[20,50] \
  myvm
```

### Common VM Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `numcpus` | 2 | Number of CPUs |
| `memory` | 512 | Memory in MB |
| `disks` | [10] | Disk sizes in GB |
| `nets` | [default] | Networks to attach |
| `pool` | default | Storage pool |
| `cloudinit` | true | Enable cloud-init |
| `start` | true | Start VM after creation |
| `keys` | [] | SSH public keys to inject |
| `cmds` | [] | Commands to run at boot |
| `files` | [] | Files to inject |

### Advanced VM Examples
```bash
# With static IP
kcli create vm -i centos9stream \
  -P nets=['{"name":"default","ip":"192.168.122.100"}'] \
  myvm

# With post-boot commands
kcli create vm -i fedora40 \
  -P cmds=['dnf -y install nginx','systemctl enable --now nginx'] \
  webserver

# From profile
kcli create vm -p myprofile myvm

# Multiple disks with options
kcli create vm -i ubuntu2204 \
  -P disks=['{"size":20}','{"size":100,"pool":"data"}'] \
  myvm
```

## VM Management

```bash
# List VMs
kcli list vm                          # Table format
kcli list vm -o yaml                  # YAML output
kcli list vm -o json                  # JSON output

# VM Information
kcli info vm myvm                     # Full details
kcli info vm myvm -f ip               # Just IP address

# State Control
kcli start vm myvm
kcli stop vm myvm
kcli restart vm myvm

# Access
kcli ssh myvm                         # SSH as default user
kcli ssh -u root myvm                 # SSH as root
kcli console myvm                     # VNC/SPICE console
kcli console myvm --serial            # Serial console

# Modify
kcli update vm myvm -P memory=8192    # Change memory
kcli update vm myvm -P numcpus=8      # Change CPUs
kcli create disk -s 50 myvm           # Add 50GB disk

# Snapshots
kcli create snapshot myvm snap1
kcli list snapshot myvm
kcli revert snapshot myvm snap1
kcli delete snapshot myvm snap1

# Delete
kcli delete vm myvm                   # With confirmation
kcli delete vm myvm --yes             # Skip confirmation
```

## Plans (Infrastructure as Code)

Plans are YAML files with Jinja2 templating for deploying complete environments.

### Basic Plan Structure
```yaml
# myplan.yml
parameters:
  base_image: centos9stream
  domain: lab.local

# Network (created first)
labnet:
  type: network
  cidr: 192.168.100.0/24
  dhcp: true

# VM (uses the network)
webserver:
  image: {{ base_image }}
  memory: 2048
  numcpus: 2
  nets:
    - labnet
  cmds:
    - dnf -y install nginx
    - systemctl enable --now nginx
```

### Plan Commands
```bash
# Deploy
kcli create plan -f myplan.yml myplan

# Deploy with parameter overrides
kcli create plan -f myplan.yml -P base_image=fedora40 myplan

# List and manage
kcli list plan
kcli info plan myplan
kcli delete plan myplan               # Deletes all resources

# Update existing plan
kcli update plan -f myplan.yml myplan
```

### Multi-VM Plan with Loop
```yaml
parameters:
  cluster_name: web
  node_count: 3

{% for i in range(node_count) %}
{{ cluster_name }}-node-{{ i }}:
  image: centos9stream
  memory: 2048
  nets:
    - default
{% endfor %}
```

### Resource Types in Plans

| Type | Description |
|------|-------------|
| (none) | VM (default if no type specified) |
| `network` | Virtual network |
| `pool` | Storage pool |
| `image` | Download image from URL |
| `profile` | Reusable VM template |
| `container` | Container workload |
| `kube` | Kubernetes cluster |

## Kubernetes Clusters

### Supported Types
- `generic` / `kubeadm` - Standard Kubernetes
- `openshift` / `okd` - OpenShift
- `k3s` - Lightweight K3s
- `rke2` - Rancher RKE2
- `microshift` - Edge MicroShift
- `hypershift` - Hosted control planes
- `aks` / `eks` / `gke` - Cloud managed

### Deploy Clusters
```bash
# Generic Kubernetes
kcli create kube generic -P ctlplanes=1 -P workers=2 myk8s

# K3s (lightweight)
kcli create kube k3s -P ctlplanes=1 -P workers=2 myk3s

# OpenShift (requires pull secret)
kcli create kube openshift \
  -P pull_secret=~/pull-secret.json \
  -P ctlplanes=3 \
  -P workers=2 \
  myocp
```

### Cluster Management
```bash
# List clusters
kcli list kube

# Get kubeconfig
kcli get kubeconfig mycluster
export KUBECONFIG=~/.kcli/clusters/mycluster/kubeconfig

# Scale workers
kcli scale kube generic -P workers=5 mycluster

# Delete
kcli delete kube mycluster
```

## Images

```bash
# List available cloud images
kcli list available-images

# Download image
kcli download image fedora40
kcli download image centos9stream
kcli download image ubuntu2204

# List downloaded images
kcli list image

# Delete image
kcli delete image fedora40
```

Common images: `fedora40`, `centos9stream`, `ubuntu2204`, `rhel9`, `debian12`, `rocky9`, `almalinux9`

## Networks and Storage

### Networks
```bash
# Create network
kcli create network -c 192.168.100.0/24 mynet
kcli create network -c 10.0.0.0/24 --dhcp --nat privatenet

# List and delete
kcli list network
kcli info network mynet
kcli delete network mynet
```

### Storage Pools
```bash
# Create pool
kcli create pool -p /var/lib/libvirt/images default
kcli create pool -p /home/vms myvms

# List and delete
kcli list pool
kcli delete pool myvms
```

## Provider/Client Management

```bash
# List configured clients
kcli list client

# Switch default client
kcli switch mykvm

# Use specific client for command
kcli -C aws list vm
kcli -C gcp create vm -i ubuntu2204 myvm

# List VMs from all clients
kcli -C all list vm

# Host information
kcli info host
kcli list host
```

## Profiles

Profiles are reusable VM templates defined in `~/.kcli/profiles.yml`:

```yaml
# ~/.kcli/profiles.yml
small:
  numcpus: 1
  memory: 1024
  disks:
    - 10

webserver:
  image: centos9stream
  numcpus: 2
  memory: 4096
  cmds:
    - dnf -y install nginx
    - systemctl enable --now nginx
```

Usage:
```bash
kcli create vm -p webserver myweb
```

## Debug and Troubleshooting

```bash
# Debug mode (verbose output)
kcli -d create vm -i fedora40 myvm
kcli -d list vm

# Check VM details
kcli info vm myvm

# Check cloud-init logs (after SSH)
kcli ssh myvm
cat /var/log/cloud-init.log

# Verify provider connectivity
kcli list host
kcli info host
```

### Common Issues

**No IP address**: Check DHCP on network, wait for cloud-init
```bash
kcli info network default
```

**SSH fails**: Verify key injection worked
```bash
kcli ssh -l myvm                      # Show SSH command
```

**Permission denied (libvirt)**: Add user to groups
```bash
sudo usermod -aG qemu,libvirt $(id -un)
newgrp libvirt
```

## Configuration Files

```
~/.kcli/
├── config.yml      # Client/provider configuration
├── profiles.yml    # VM profiles
├── id_rsa          # SSH private key (auto-used)
└── clusters/       # Cluster state files
```

### Minimal config.yml
```yaml
default:
  client: local

local:
  type: kvm
  host: 127.0.0.1
  pool: default
```

## Container Mode

Run kcli without installation:
```bash
# With libvirt socket
alias kcli='podman run --rm -it \
  -v ~/.kcli:/root/.kcli:z \
  -v /var/run/libvirt:/var/run/libvirt:z \
  quay.io/karmab/kcli'

# Then use normally
kcli list vm
```

## Useful Tips

1. **Last VM shortcut**: Many commands work without VM name (uses last created)
   ```bash
   kcli ssh                            # SSH to last VM
   kcli console                        # Console of last VM
   ```

2. **Output formats**: Most list commands support `-o yaml` or `-o json`

3. **Parameter files**: Use `kcli_parameters.yml` alongside plans for defaults

4. **Render plans**: Preview templated plans before deploying
   ```bash
   kcli render -f myplan.yml
   ```

5. **Export VMs**: Create images from running VMs
   ```bash
   kcli export vm myvm
   ```
