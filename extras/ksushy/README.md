This directory contains the scripts and Dockerfile used to create the ksushy container, based on [fakefish](https://github.com/openshift-metal3/fakefish).

This allows to interact with vms using redfish protocol and through bash scripts that leverage kcli commands under the hood.

## How to use

To run the container, use the following invocation to control a vm named VM_NAME on port 9000

```
podman run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir quay.io/karmab/ksushy --remote-bmc $VM_NAME
```
