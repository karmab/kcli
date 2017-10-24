#!/bin/bash
sleep 120
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
cd /root
git clone https://github.com/openshift/openshift-ansible
yum -y install ansible openshift-ansible-playbooks atomic
ssh-keyscan -H master.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node01.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node02.karmalabs.local >> ~/.ssh/known_hosts
ansible-playbook -i /root/hosts /root/openshift-ansible/playbooks/byo/config.yml
