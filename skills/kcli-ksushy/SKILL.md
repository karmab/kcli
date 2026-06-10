---
name: kcli-ksushy
description: Guides interaction with kcli VMs via ksushy (Redfish emulator). Use when booting, stopping, or managing baremetal-like VMs through the Redfish API, deploying the ksushy service, or working with sushy/redfish in general.
---

# kcli ksushy (Redfish Emulation)

ksushy provides a REST interface to interact with VMs using Redfish. It offers functionality similar to sushy-emulator but extends it to more providers (typically vSphere, KubeVirt, and oVirt) and through more friendly URLs.

## Requirements

ksushy is bundled within kcli. SSL support requires installing `cherrypy` and `pyopenssl` manually.

## Deploying the ksushy service

```bash
kcli create sushy-service
```

This creates a systemd unit listening on port 9000. The following environment variables are supported:

| Variable | Description |
|---|---|
| `KSUSHY_LISTEN_PORT` | Use a specific port |
| `KSUSHY_DEBUG` | Enable debug |
| `KSUSHY_USER` | Username for basic authentication |
| `KSUSHY_PASSWORD` | Password for basic authentication |
| `KSUSHY_BOOTONCE` | Enable bootonce |

## Determining the ksushy endpoint

The ksushy endpoint is derived from the hypervisor hosting the VMs, NOT from the VM itself or the local machine hostname:

1. Identify the current hypervisor with `kcli list hosts` (look for the `Current` column).
2. Get the hypervisor's FQDN or IP with `kcli info host <host_name>` (use the `host:` field), or look it up in `~/.kcli/config.yml`. If the host is a short name, check `~/.ssh/config` for the actual `Hostname` (IP or FQDN).
3. The ksushy base URL is `https://<host_ip>:9000/redfish/v1/Systems`.

## API Structure

Systems are organized by provider under `/redfish/v1/Systems/<provider>/<vm_name>`.

The `<provider>` matches the provider name as defined in `~/.kcli/config.yml`. For local libvirt VMs, the provider is `local`.

```bash
# List providers
curl -ks https://<host>:9000/redfish/v1/Systems

# List VMs under the local (libvirt) provider
curl -ks https://<host>:9000/redfish/v1/Systems/local

# Query a VM on a different provider
curl -ks https://<host>:9000/redfish/v1/Systems/myotherprovider/mynode

# Get info on a specific VM
curl -ks https://<host>:9000/redfish/v1/Systems/local/<vm_name>
```

## VM Power Operations

Typical redfish operations (start, stop, info, listing NICs) are supported for all providers.

```bash
# Power on a VM
curl -ks https://<host>:9000/redfish/v1/Systems/local/<vm_name>/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'

# Power off a VM
curl -ks https://<host>:9000/redfish/v1/Systems/local/<vm_name>/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "ForceOff"}'

# Restart a VM
curl -ks https://<host>:9000/redfish/v1/Systems/local/<vm_name>/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "ForceRestart"}'
```

## Virtual Media (ISO)

ISO plugging is only supported on virtualization providers.

```bash
# Insert ISO
curl -ks https://<host>:9000/redfish/v1/Systems/local/<vm_name>/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia \
  -H "Content-Type: application/json" \
  -d '{"Image": "http://<iso_server>/<image>.iso"}'

# Eject ISO
curl -ks https://<host>:9000/redfish/v1/Systems/local/<vm_name>/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia \
  -H "Content-Type: application/json" -d '{}'
```

## Authentication

When the service is deployed with `KSUSHY_USER` and `KSUSHY_PASSWORD`, access is secured through basic authentication:

```bash
curl -ks -u myuser:mypassword https://<host>:9000/redfish/v1/Systems/local/<vm_name>
```

## Typical Workflow

1. Create baremetal-like VMs with kcli:
   ```bash
   kcli create vm -P start=false -P memory=20480 -P numcpus=16 -P 'disks=[200]' -P uefi=true -P 'nets=[default]' -c 3 mycluster
   ```

2. Determine the ksushy endpoint (see above).

3. Boot VMs via redfish:
   ```bash
   for i in 0 1 2; do
     curl -ks https://<host>:9000/redfish/v1/Systems/local/mycluster-$i/Actions/ComputerSystem.Reset \
       -H "Content-Type: application/json" \
       -d '{"ResetType": "On"}'
   done
   ```
