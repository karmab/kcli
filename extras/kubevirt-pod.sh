#!/bin/bash

oc create secret generic pull-secret --from-file=pull-secret=openshift_pull.json
oc create -f https://raw.githubusercontent.com/karmab/kcli/refs/heads/main/extras/kubevirt-pod.yml
