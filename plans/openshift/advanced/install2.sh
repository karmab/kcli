#!/bin/bash
ansible-playbook -i /root/hosts /usr/share/ansible/openshift-ansible/playbooks/byo/config.yml
for i in 1 2 3 ; do 
  ssh master${i}.karmalabs.com "htpasswd -b /etc/origin/master/htpasswd karim karim"
done
