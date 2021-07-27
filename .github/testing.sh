#!/bin/bash

set -ex

kcli='docker run --net host -it --rm --security-opt label=disable -v $HOME/.ssh:/root/.ssh -v $HOME/.kcli:/root/.kcli -v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli'

sudo $kcli create pool -p /var/lib/libvirt/images default
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images
ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
sudo $kcli create plan -f .github/test_plan.yml test_plan
sudo $kcli list vm
sudo $kcli list plan | grep -q test_plan
sudo $kcli delete plan --yes test_plan
