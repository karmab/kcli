#!/bin/bash

set -ex

image_pool_dir="$HOME/pool/"
mkdir -p "${image_pool_dir}"
chmod a+rwx "${image_pool_dir}"

shopt -s expand_aliases
ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
cd travis
alias kcli='docker run --rm --privileged --net host -t -a stdout -a stderr -v ${HOME}/.kcli:/root/.kcli -v ${HOME}/.ssh:/root/.ssh -v /var/run/libvirt:/var/run/libvirt -v ${image_pool_dir}:${image_pool_dir} -v ${PWD}:/workdir karmab/kcli'
kcli create plan -f test_plan.yml -P image_pool_dir="${image_pool_dir}" test_plan --wait
kcli list vm
kcli list plan | grep -q test_plan
kcli ssh hostname | grep cruel
kcli ssh -u root cat /root/myfile.txt | grep name
kcli delete plan --yes test_plan
cd --
tree -f /srv
