There is a controller leveraging kcli and using vm, plan and clusters crds to create vms the corresponding objects, regardless of the infrastructure.

## Requisites

- a running kubernetes/openshift cluster and KUBECONFIG env variable pointing to it (or simply .kube/config)
- some infrastructure supported by kcli running somewhere and the corresponding credentials.
- optionally storage to hold a pvc for cluster data and another one for plan files data.

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

Then deploy the controller (along with its CRDS):

```
kubectl create -f https://raw.githubusercontent.com/karmab/kcli/main/extras/controller/deploy.yml
```

If you want to use a pvc named `kcli-clusters` for storing cluster data, add it:

```
kubectl -n kcli-infra patch deploy kcli-controller --type json -p='[{"op": "add", "path": "/spec/template/spec/containers/0/volumeMounts/-", "value": {"mountPath": "/root/.kcli/clusters", "name": "kcli-clusters"}}, {"op": "add", "path": "/spec/template/spec/volumes/-", "value": {"persistentVolumeClaim": {"claimName" : "kcli-clusters"}, "name": "kcli-clusters"}}]'
```

## How to use

The directory [extras/controller/examples](https://github.com/karmab/kcli/tree/main/extras/controller/examples) contains different examples of vm, plan and cluster CRs.

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
  name: hendrix
spec:
  ctlplanes: 1
  api_ip: 192.168.122.252
```

Once a cluster is deployed successfully, you can retrieve its kubeconfig from it status

```
CLUSTER=hendrix
kubectl get cluster $CLUSTER -o jsonpath='{.status.create_cluster.kubeconfig}' | base64 -d > kubeconfig.$CLUSTER
```

#### autoscaling

You can enable autoscaling for a given cluster by setting `autoscale` to any value in its spec.

##### Scaling up

When more than a given threshold of pods can't be scheduled, one more worker will be added to the cluster and the autoscaling will pause until it appears as a new ready node.

This threshold is configured as an env variable AUTOSCALE_MAXIMUM provided during the deployment of the controller, which defaults to 20

Setting the threshold to any value higher than 9999 effectively disables the feature.

##### Scaling down

If the number of running pods for a given worker node goes below a minimum value, the cluster will be scaled down by one worker.

The minimum is configured as an env variable AUTOSCALE_MINIMUM provided during the deployment of the controller, which defaults to 2

Setting the minimum to any value below 1 effectively disables the feature.
