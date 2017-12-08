#!/bin/bash
sleep 360
yum -y install openshift-ansible-playbooks
ssh-keyscan -H lb.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master01.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master02.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H master03.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node01.karmalabs.local >> ~/.ssh/known_hosts
ssh-keyscan -H node02.karmalabs.local >> ~/.ssh/known_hosts
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
sed -i "s/#log_path/log_path/" /etc/ansible/ansible.cfg
sed -i "s/openshift_master_default_subdomain=.*/openshift_master_default_subdomain=$IP.xip.io/" /root/hosts
ansible-playbook -i /root/hosts /usr/share/ansible/openshift-ansible/playbooks/byo/config.yml
for i in 1 2 3 ; do 
  ssh master0${i}.karmalabs.local "htpasswd -b /etc/origin/master/htpasswd developer developer"
done
