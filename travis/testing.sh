#!/bin/bash

set -ex

image_pool_dir="/srv/pool/"
sudo mkdir -p  "${image_pool_dir}"
sudo chmod a+rwx "${image_pool_dir}"

kcli="docker run --rm --privileged --net host -t -a stdout -a stderr -v ${HOME}/.kcli:/root/.kcli -v ${HOME}/.ssh:/root/.ssh -v /var/run/libvirt:/var/run/libvirt -v ${image_pool_dir}:${image_pool_dir} -v ${PWD}:/workdir karmab/kcli"

ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
sudo ${kcli} create plan -f travis/test_plan.yml -P image_pool_dir="${image_pool_dir}" test_plan
sudo ${kcli} list vm
sudo ${kcli} list plan | grep -q test_plan
sudo ${kcli} delete plan --yes test_plan
tree -f /srv
