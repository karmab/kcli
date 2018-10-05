#!/usr/bin/env bash
[% if driver == 'generic' %]
ssh-keyscan -H 127.0.0.1 >> ~/.ssh/known_hosts
minishift start --vm-driver=generic --iso-url centos --remote-ipaddress 127.0.0.1 --remote-ssh-user root --remote-ssh-key ~/.ssh/id_rsa --memory [[ minishift_memory ]]
[% else %]
minishift start --vm-driver=kvm --iso-url centos --memory [[ minishift_memory ]]
[% endif %]
eval $(minishift oc-env)
minishift oc-env >>/root/.bashrc
oc login -u system:admin
oc adm policy add-cluster-role-to-user cluster-admin admin
oc adm policy add-cluster-role-to-user cluster-admin developer
