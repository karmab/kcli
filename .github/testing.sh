#!/bin/bash

set -ex
shopt -s expand_aliases

alias kcli='docker run --net host --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir -v /var/tmp:/ignitiondir quay.io/karmab/kcli:latest'

sudo mkdir -p /var/lib/libvirt/images
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images
mkdir ~/.kcli
ssh-keygen -t rsa -N '' -f ~/.kcli/id_rsa
kcli create pool -p /var/lib/libvirt/images default
# kcli create plan -f .github/test_plan.yml test_plan > prout.txt 2>&1 || true
# kcli list plan | grep -q test_plan
# kcli delete plan --yes test_plan
kcli list vm
