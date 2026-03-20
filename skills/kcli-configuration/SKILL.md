---
name: kcli-configuration
description: Guides kcli configuration and provider setup. Use when setting up ~/.kcli/config.yml, configuring providers (KVM, AWS, GCP, Azure, etc.), or managing profiles.
---

# kcli Configuration

## Configuration Files Location

```
~/.kcli/
├── config.yml           # Main configuration (clients/providers)
├── profiles.yml         # VM profiles (optional, can be in config.yml)
├── id_rsa / id_rsa.pub  # SSH keys for VM access
├── id_ed25519           # Alternative SSH key
└── clusters/            # Cluster state (created by kcli)
```

## Basic config.yml Structure

```yaml
default:
  client: localhost       # Default provider to use
  numcpus: 2
  memory: 512
  pool: default
  nets:
    - default
  disks:
    - size: 10

# Provider definitions
localhost:
  type: kvm
  host: 127.0.0.1
```

## Provider Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `kvm` | Local/remote libvirt | host |
| `aws` | Amazon Web Services | access_key_id, access_key_secret, region |
| `gcp` | Google Cloud Platform | credentials, project, zone |
| `azure` | Microsoft Azure | subscription_id, credentials (file) |
| `kubevirt` | VMs on Kubernetes | context, host |
| `openstack` | OpenStack cloud | auth_url, user, password, project |
| `ovirt` | oVirt/RHV | host, user, password, datacenter |
| `vsphere` | VMware vSphere | host, user, password, datacenter |
| `proxmox` | Proxmox VE | host, user, password |
| `hcloud` | Hetzner Cloud | token |
| `ibm` | IBM Cloud | iam_api_key, region, vpc |

## KVM/Libvirt Configuration

```yaml
# Local libvirt
localhost:
  type: kvm
  host: 127.0.0.1
  pool: default

# Remote libvirt via SSH
remote-kvm:
  type: kvm
  host: 192.168.1.100
  protocol: ssh           # ssh (default), tcp, or tls
  user: root              # SSH user
  pool: default
  # url: qemu+ssh://root@host/system  # Or custom URI
```

## AWS Configuration

```yaml
myaws:
  type: aws
  access_key_id: AKIAIOSFODNN7EXAMPLE
  access_key_secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  region: us-east-1
  keypair: mykey          # EC2 key pair name
```

## GCP Configuration

```yaml
mygcp:
  type: gcp
  credentials: ~/service-account.json   # Service account JSON
  project: my-project-id
  zone: us-central1-a
  region: us-central1     # Optional, derived from zone
```

## Azure Configuration

```yaml
myazure:
  type: azure
  subscription_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  credentials: ~/.azure/credentials.json
  # Or use environment: AZURE_AUTH_LOCATION
  location: eastus
  resource_group: my-rg   # Optional, created if needed
```

## KubeVirt Configuration

```yaml
mykubevirt:
  type: kubevirt
  context: my-k8s-context   # kubectl context
  host: api.cluster.local   # API server for SSH tunneling
  pool: my-storageclass     # StorageClass name
  multus: true              # Use Multus CNI
  cdi: true                 # Use CDI for images
```

## OpenStack Configuration

```yaml
myopenstack:
  type: openstack
  auth_url: https://openstack:5000/v3
  user: admin
  password: secret
  project: myproject
  domain: Default
```

## oVirt/RHV Configuration

```yaml
myovirt:
  type: ovirt
  host: ovirt-engine.local
  user: admin@internal
  password: secret
  datacenter: Default
  cluster: Default
  pool: DataDomain
  ca_file: ~/ovirt.pem      # Engine CA certificate
```

## Default Section Options

```yaml
default:
  # Client selection
  client: localhost

  # Compute
  numcpus: 2
  memory: 512               # MB
  cpumodel: host-model
  nested: true              # Nested virtualization

  # Storage
  pool: default
  disks:
    - size: 10
  diskinterface: virtio
  diskthin: true

  # Network
  nets:
    - default
  reservedns: false
  reservehost: false
  reserveip: false

  # OS/Cloud-init
  cloudinit: true
  keys: []                  # SSH public keys
  cmds: []                  # Post-boot commands
  files: []                 # Files to inject

  # Access
  tunnel: false             # SSH tunneling for console
  insecure: false           # Ignore SSH host keys
  enableroot: true          # Allow root SSH

  # Metadata
  storemetadata: false
  planview: false
```

## Profiles (profiles.yml or in config.yml)

```yaml
# In ~/.kcli/profiles.yml or config.yml profiles section
small:
  numcpus: 1
  memory: 1024
  disks:
    - size: 10

medium:
  numcpus: 2
  memory: 2048
  disks:
    - size: 20

large:
  numcpus: 4
  memory: 4096
  disks:
    - size: 40
    - size: 100

webserver:
  image: centos9stream
  numcpus: 2
  memory: 4096
  nets:
    - default
  cmds:
    - dnf -y install nginx
    - systemctl enable --now nginx
  base: medium              # Inherit from another profile
```

## Multiple Clients

```yaml
default:
  client: local-kvm         # Default client

local-kvm:
  type: kvm
  host: 127.0.0.1

remote-kvm:
  type: kvm
  host: 192.168.1.100

myaws:
  type: aws
  access_key_id: ...
  access_key_secret: ...
  region: us-east-1
```

Switch clients:
```bash
kcli switch local-kvm       # Change default
kcli -C myaws list vm       # Use specific client
```

## Validation Commands

```bash
# List configured clients
kcli list client

# Check client connectivity
kcli list host

# Info about current client
kcli info host

# Switch default client
kcli switch <client>

# Test with specific client
kcli -C <client> list vm
```

## Environment Variables

Some values can come from environment:
- `GOOGLE_APPLICATION_CREDENTIALS` - GCP credentials path
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `AZURE_AUTH_LOCATION` - Azure credentials path
- `OS_*` - OpenStack credentials (standard OS_ vars)

## Troubleshooting

**Connection refused (KVM):**
```bash
# Check libvirt is running
sudo systemctl status libvirtd

# Test virsh connection
virsh -c qemu:///system list
```

**SSH key issues:**
```bash
# Generate kcli SSH key
ssh-keygen -t rsa -N '' -f ~/.kcli/id_rsa

# Or use ed25519
ssh-keygen -t ed25519 -N '' -f ~/.kcli/id_ed25519
```

**Debug mode:**
```bash
kcli -d list vm             # Shows provider connection details
```
