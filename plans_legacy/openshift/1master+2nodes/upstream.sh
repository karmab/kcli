#!/bin/bash
sleep 120
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
cd /root
git clone https://github.com/openshift/openshift-ansible
yum -y install ansible openshift-ansible-playbooks atomic
ssh-keyscan -H master.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node01.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node02.karmalabs.local >> ~/.ssh/known_hosts
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
sed -i "s/openshift_master_default_subdomain=.*/openshift_master_default_subdomain=$IP.xip.io/" /root/hosts
ansible-playbook -i /root/hosts /root/openshift-ansible/playbooks/byo/config.yml
