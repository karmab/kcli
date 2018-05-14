#!/bin/bash
yum -y install openshift-ansible screen bind-utils
[% for master in range(0, masters) %]
ssh-keyscan -H master0[[ master + 1 ]].[[ domain ]] >> ~/.ssh/known_hosts
[% endfor %]
[% for node in range(0, nodes) %]
ssh-keyscan -H node0[[ node + 1 ]].[[ domain ]] >> ~/.ssh/known_hosts
[% endfor %]
export IP=`dig +short master01.[[ domain ]]`
sed -i "s/#log_path/log_path/" /etc/ansible/ansible.cfg
sed -i "s/openshift_master_default_subdomain=.*/openshift_master_default_subdomain=$IP.xip.io/" /root/hosts
#sed -i "s/openshift_master_cluster_hostname=.*/openshift_master_cluster_hostname=$IP.xip.io/" /root/hosts
#sed -i "s/openshift_master_cluster_public_hostname=.*/openshift_master_cluster_public_hostname=$IP.xip.io/" /root/hosts
ansible-playbook -i /root/hosts /usr/share/ansible/openshift-ansible/playbooks/prerequisites.yml
ansible-playbook -i /root/hosts /usr/share/ansible/openshift-ansible/playbooks/deploy_cluster.yml
