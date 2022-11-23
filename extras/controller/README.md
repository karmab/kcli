There is a controller leveraging kcli and using vm, plan and clusters crds to create vms the corresponding objects, regardless of the infrastructure.

## Requisites

- a running kubernetes/openshift cluster and KUBECONFIG env variable pointing to it (or simply .kube/config)
- some infrastructure supported by kcli running somewhere and the corresponding credentials.

## Deploying

If you're running kcli locally, use the following to create the proper configmaps to share your credentials and ssh keys:

```
kcli sync kube
```

To do the same manually, run instead:

```
kubectl create configmap kcli-config --from-file=$HOME/.kcli
kubectl create configmap ssh-config --from-file=$HOME/.ssh
```

Then deploy the crds and the controller:

```
kubectl create -f crd.yml
kubectl create -f deploy.yml
```

## How to use

The directory [extras/controller/examples](https://github.com/karmab/kcli/tree/master/extras/controller/examples) contains different examples of vm, plan an cluster crs.

Here are some sample ones for each type to get you started

### vms

```
apiVersion: kcli.karmalabs.local/v1
kind: Vm
metadata:
  name: cirros
spec:
  image: cirros
  memory: 512
  numcpus: 2
```

Note that when a vm is created, the controller waits before it gets an ip and populate it status with its complete information, which is then formatted when running `kubectl get vms`

### plans

```
apiVersion: kcli.karmalabs.local/v1
kind: Plan
metadata:
  name: simpleplan2
spec:
  plan: |
    vm11:
      memory: 512
      numcpus: 2
      nets:
       - default
      image: cirros
    vm22:
      memory: 1024
      numcpus: 4
      nets:
       - default
      disks:
       - 20
      pool: default
      image: cirros
      cmds:
       - echo this stuff works > /tmp/result.txt
```

To run plans which contain scripts or files, you ll need to copy those assets in the /workdir of the kcli pod

```
KCLIPOD=$(kubectl get pod -o name -n kcli | sed 's@pod/@@')
kubectl cp samplecrd/frout.txt $KCLIPOD:/workdir
```

### clusters

```
apiVersion: kcli.karmalabs.local/v1
kind: Cluster
metadata:
  name: fede
spec:
  masters: 3
  api_ip: 192.168.122.252
```
