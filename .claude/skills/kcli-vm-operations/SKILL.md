---
name: kcli-vm-operations
description: Guides VM lifecycle operations with kcli. Use when creating, managing, or troubleshooting virtual machines across providers.
---

# kcli VM Operations

## VM Lifecycle Commands

### Create VM
```bash
# From image
kcli create vm -i fedora40 myvm

# With parameters
kcli create vm -i centos9stream -P memory=4096 -P numcpus=4 -P disks=[20,50] myvm

# From profile
kcli create vm -p myprofile myvm
```

### List VMs
```bash
kcli list vm                    # All VMs
kcli list vm -o yaml            # YAML output
kcli list vm -o json            # JSON output
```

### VM Info
```bash
kcli info vm myvm               # Full info
kcli info vm myvm -f ip         # Specific field
kcli info vm myvm -o yaml       # YAML format
```

### Start/Stop/Restart
```bash
kcli start vm myvm
kcli stop vm myvm
kcli restart vm myvm
```

### Delete VM
```bash
kcli delete vm myvm             # With confirmation
kcli delete vm myvm --yes       # Skip confirmation
kcli delete vm myvm --snapshots # Delete snapshots too
```

## SSH Access

```bash
kcli ssh myvm                   # SSH as default user
kcli ssh -u root myvm           # SSH as specific user
kcli ssh -l myvm                # List SSH command only
```

## Console Access

```bash
kcli console myvm               # Graphical console (VNC/SPICE)
kcli console myvm --serial      # Serial console
```

## Disk Operations

```bash
# Add disk
kcli create disk -s 20 -p default myvm  # 20GB disk
kcli create disk -s 50 --thin myvm      # Thin provisioned

# Delete disk
kcli delete disk myvm-disk1 myvm

# List disks
kcli list disk
```

## NIC Operations

```bash
# Add NIC
kcli create nic -n mynetwork myvm

# Delete NIC
kcli delete nic eth1 myvm

# Update NIC
kcli update nic -n newnetwork myvm --index 0
```

## Snapshots

```bash
# Create snapshot
kcli create snapshot myvm mysnapshot

# List snapshots
kcli list snapshot myvm

# Revert to snapshot
kcli revert snapshot myvm mysnapshot

# Delete snapshot
kcli delete snapshot myvm mysnapshot
```

## VM Configuration

### Configuration Hierarchy
Parameters are resolved in order (later overrides earlier):
1. `kvirt/defaults.py` - Built-in defaults
2. `~/.kcli/config.yml` default section
3. Provider-specific section in config.yml
4. Profile definition (`~/.kcli/profiles.yml`)
5. Plan file parameters
6. Command-line `-P` overrides

### Common Parameters
```yaml
# Compute
numcpus: 2                      # CPU count
memory: 512                     # Memory in MB
cpumodel: host-model            # CPU model

# Storage
pool: default                   # Storage pool
disks:                          # Disk configuration
  - size: 20                    # Size in GB
  - size: 50
    pool: otherpool
    thin: true

# Network
nets:                           # Network configuration
  - default                     # Simple: network name only
  - name: mynet                 # Advanced: with options
    ip: 192.168.1.10
    netmask: 255.255.255.0
    gateway: 192.168.1.1
    mac: aa:bb:cc:dd:ee:ff

# OS Customization
image: fedora40                 # Base image
cloudinit: true                 # Enable cloud-init
keys:                           # SSH public keys
  - ssh-rsa AAAA... user@host
cmds:                           # Post-boot commands
  - dnf -y update
  - systemctl enable nginx
files:                          # Files to inject
  - path: /etc/myconfig
    content: |
      key=value
```

## Images

```bash
# List available images
kcli list image

# Download image
kcli download image fedora40
kcli download image centos9stream -p mypool

# Delete image
kcli delete image fedora40

# List all available images (from kcli catalog)
kcli list available-images
```

## Profiles

Profiles in `~/.kcli/profiles.yml`:
```yaml
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

webserver:
  image: centos9stream
  numcpus: 2
  memory: 4096
  nets:
    - default
  cmds:
    - dnf -y install nginx
    - systemctl enable --now nginx
```

Usage:
```bash
kcli create vm -p webserver myweb
```

## Update Operations

```bash
# Update memory
kcli update vm myvm -P memory=8192

# Update CPUs
kcli update vm myvm -P numcpus=4

# Update metadata
kcli update vm myvm -P information="Production server"
```

## Clone VM

```bash
kcli clone vm myvm myclone
kcli clone vm myvm myclone --full  # Full clone (not linked)
```

## Export VM

```bash
kcli export vm myvm                 # Export to image
kcli export vm myvm --image myimage # Custom image name
```

## Troubleshooting

### VM Won't Start
```bash
kcli -d start vm myvm              # Debug output
sudo virsh list --all               # Check libvirt state
sudo virsh start myvm               # Try direct start
```

### No IP Address
```bash
# Check DHCP is enabled on network
kcli info network default

# Check cloud-init completed
kcli ssh myvm
cat /var/log/cloud-init.log
```

### SSH Connection Issues
```bash
# Get SSH command details
kcli ssh -l myvm

# Check VM has IP
kcli info vm myvm -f ip

# Try direct SSH
ssh -i ~/.kcli/id_rsa user@<ip>
```
