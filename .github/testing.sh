#!/bin/bash

set -euo pipefail
sudo mkdir -p /var/lib/libvirt/images
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images
mkdir ~/.kcli
ssh-keygen -t rsa -N '' -f ~/.kcli/id_rsa
pip3 install -e .
kcli create pool -p /var/lib/libvirt/images default
kcli create plan -f .github/test_plan.yml test_plan
kcli list plan | grep test_plan
kcli delete plan --yes test_plan
