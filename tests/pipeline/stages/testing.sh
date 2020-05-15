#!/bin/bash

set -ex

image_pool_dir="/srv/pool/"
sudo mkdir -p  "${image_pool_dir}"
sudo chmod a+rwx "${image_pool_dir}"

__libvirt_dir="/var/run/libvirt/"
__libvirt_sock="${__libvirt_dir}/libvirt-sock"
__libvirt_config="${PWD}/tests/pipeline/libvirtd.conf"
__kcli="docker run --rm \
               --privileged \
               --net host \
               -t -a stdout -a stderr \
               -v ${HOME}/.kcli:/root/.kcli \
               -v ${HOME}/.ssh:/root/.ssh \
               -v ${__libvirt_sock}:${__libvirt_sock} \
               -v ${__libvirt_dir}:${__libvirt_dir} \
               -v ${__libvirt_config}:/etc/libvirt/libvirtd.conf \
               -v ${image_pool_dir}:${image_pool_dir} \
               -v ${PWD}:/workdir \
               karmab/kcli"


sudo ${__kcli} create plan \
                      -P image_pool_dir="${image_pool_dir}" \
                      -f ./tests/pipeline/plans/base_kvm.yml base_plan_test
sudo ${__kcli} delete plan -y base_plan_test
