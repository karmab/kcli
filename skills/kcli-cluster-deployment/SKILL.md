---
name: kcli-cluster-deployment
description: Guides deployment and management of Kubernetes clusters with kcli. Use when deploying OpenShift, k3s, kubeadm, or other Kubernetes distributions.
---

# kcli Cluster Deployment

## Supported Cluster Types

| Type | Description | Module |
|------|-------------|--------|
| `openshift` | Red Hat OpenShift (IPI/UPI) | `kvirt/cluster/openshift/` |
| `okd` | Community OpenShift | Same as openshift |
| `hypershift` | OpenShift Hosted Control Planes | `kvirt/cluster/hypershift/` |
| `microshift` | Lightweight edge OpenShift | `kvirt/cluster/microshift/` |
| `generic` | Generic Kubernetes (alias: `kubernetes`) | `kvirt/cluster/kubernetes/` |
| `kubeadm` | Standard Kubernetes via kubeadm | `kvirt/cluster/kubeadm/` |
| `k3s` | Lightweight Kubernetes | `kvirt/cluster/k3s/` |
| `rke2` | Rancher Kubernetes Engine 2 | `kvirt/cluster/rke2/` |
| `aks` | Azure Kubernetes Service | `kvirt/cluster/aks/` |
| `eks` | Amazon Elastic Kubernetes | `kvirt/cluster/eks/` |
| `gke` | Google Kubernetes Engine | `kvirt/cluster/gke/` |

## Basic Cluster Commands

```bash
# Create cluster
kcli create kube <type> <clustername>

# Create with parameters
kcli create kube openshift -P ctlplanes=3 -P workers=2 mycluster

# List clusters
kcli list kube

# Get cluster info
kcli info kube mycluster

# Delete cluster
kcli delete kube mycluster

# Scale cluster
kcli scale kube <type> -P workers=5 mycluster

# Get kubeconfig
kcli get kubeconfig mycluster
```

## OpenShift Deployment

### Minimal Example
```bash
kcli create kube openshift -P pull_secret=~/pull-secret.json mycluster
```

### Key Parameters
```yaml
# Required
pull_secret: ~/pull-secret.json    # Red Hat pull secret
domain: example.com                 # Base domain

# Topology
ctlplanes: 3                        # Control plane nodes
workers: 2                          # Worker nodes
version: stable                     # OpenShift version (stable, 4.14, etc.)

# Resources
ctlplane_memory: 16384              # Control plane memory (MB)
ctlplane_numcpus: 8                 # Control plane CPUs
worker_memory: 8192                 # Worker memory
worker_numcpus: 4                   # Worker CPUs

# Networking
network: default                    # Libvirt network
api_ip: 192.168.122.253            # API VIP (auto-detected if omitted)
ingress_ip: 192.168.122.252        # Ingress VIP
```

### Disconnected/Air-gapped
```yaml
disconnected_url: registry.local:5000
disconnected_user: admin
disconnected_password: password
ca: |
  -----BEGIN CERTIFICATE-----
  ...
  -----END CERTIFICATE-----
```

## kubeadm Deployment

```bash
kcli create kube kubeadm -P domain=k8s.local -P ctlplanes=1 -P workers=2 myk8s
```

### Key Parameters
```yaml
domain: k8s.local                   # Required domain
version: 1.29                       # Kubernetes version
ctlplanes: 1                        # Control planes (odd number for HA)
workers: 2                          # Worker count
network: default                    # Network name
api_ip: 192.168.122.250            # API endpoint (for multi-ctlplane)
image: centos9stream                # Base OS image
```

## k3s Deployment

```bash
kcli create kube k3s -P ctlplanes=1 -P workers=2 myk3s
```

### Key Parameters
```yaml
ctlplanes: 1
workers: 2
version: latest                     # k3s version
domain: k3s.local
image: ubuntu2204
```

## RKE2 Deployment

```bash
kcli create kube rke2 -P ctlplanes=1 -P workers=2 myrke2
```

### Key Parameters
```yaml
ctlplanes: 1
workers: 2
version: latest                     # RKE2 version
domain: rke2.local
image: ubuntu2204
```

## HyperShift (Hosted Control Planes)

```bash
kcli create kube hypershift \
  -P pull_secret=~/pull-secret.json \
  -P nodepool_replicas=2 \
  myhypershift
```

### Key Parameters
```yaml
pull_secret: ~/pull-secret.json
management_cluster: mgmt            # Existing cluster name
nodepool_replicas: 2                # Worker node count
release_image: ...                  # Specific OCP release
```

## MicroShift Deployment

```bash
kcli create kube microshift -P pull_secret=~/pull-secret.json mymicroshift
```

### Key Parameters
```yaml
pull_secret: ~/pull-secret.json
version: latest                     # MicroShift version
image: rhel9                        # RHEL-based image required
```

## Cluster Directory Structure

Clusters store state in `~/.kcli/clusters/<clustername>/`:
```
~/.kcli/clusters/mycluster/
├── kcli_parameters.yml    # Stored parameters
├── kubeconfig             # Cluster kubeconfig
├── auth/                  # Auth credentials (OpenShift)
│   ├── kubeadmin-password
│   └── kubeconfig
└── (other cluster-specific files)
```

## Scaling Operations

```bash
# Scale workers
kcli scale kube openshift -P workers=5 mycluster

# Scale control planes (careful!)
kcli scale kube kubeadm -P ctlplanes=3 mycluster

# Add nodes with specific parameters
kcli scale kube openshift -P workers=3 -P worker_memory=16384 mycluster
```

## Troubleshooting

### Check Deployment Progress
```bash
# OpenShift: watch bootstrap
kcli ssh mycluster-bootstrap
journalctl -f -u bootkube

# kubeadm: check cluster status
export KUBECONFIG=~/.kcli/clusters/mycluster/kubeconfig
kubectl get nodes
kubectl get pods -A
```

### Common Issues

1. **API IP not reachable**: Ensure `api_ip` is in the correct subnet
2. **Pull secret invalid**: Verify JSON format and Red Hat subscription
3. **Insufficient resources**: Check VM memory/CPU against requirements
4. **DNS resolution**: Ensure domain resolves or use `sslip: true`

### Debug Mode
```bash
kcli -d create kube openshift mycluster  # Verbose output
```

## Cloud Provider Notes

For cloud providers (AWS, GCP, Azure), kcli can:
- Auto-create load balancers (`cloud_lb: true`)
- Configure cloud DNS (`cloud_dns: true`)
- Set up cloud storage (`cloud_storage: true`)

```yaml
cloud_lb: true
cloud_dns: true
cloud_storage: true
```
