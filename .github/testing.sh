#!/bin/bash

set -ex

kcli="docker run --rm --privileged --net host -t -a stdout -a stderr -v ${HOME}/.kcli:/root/.kcli -v ${HOME}/.ssh:/root/.ssh -v /var/run/libvirt:/var/run/libvirt -v ${image_pool_dir}:${image_pool_dir} -v ${PWD}:/workdir quay.io/karmab/kcli"

sudo kcli create pool -p /var/lib/libvirt/images default
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images
ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
sudo ${kcli} create plan -f .github/test_plan.yml test_plan
sudo ${kcli} list vm
sudo ${kcli} list plan | grep -q test_plan
sudo ${kcli} delete plan --yes test_plan
