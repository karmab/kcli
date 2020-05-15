#!/bin/bash

# ready hypervizor for usage in travis runner

set -ex

__libvirtd_pid_file="/srv/virt_pid"
__libvirtd_config_file="${PWD}/tests/pipeline/libvirtd.conf"
__libvirt_dir="/var/run/libvirt/"

sudo touch "${__libvirtd_pid_file}"

sudo libvirtd --pid-file "${__libvirtd_pid_file}"  \
              --config "${__libvirtd_config_file}" \
              --daemon \
              --verbose

sudo chmod -R a+rwx "${__libvirt_dir}"
