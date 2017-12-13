#!/bin/bash
yum -y install ansible openshift-ansible-playbooks
ssh-keyscan -H allinone.default >> ~/.ssh/known_hosts
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
sed -i "s/openshift_master_default_subdomain=.*/openshift_master_default_subdomain=$IP.xip.io/" /root/hosts
ansible-playbook -i /root/hosts /usr/share/ansible/openshift-ansible/playbooks/byo/config.yml
htpasswd -b /etc/origin/master/htpasswd developer developer
