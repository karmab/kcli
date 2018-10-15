#!/bin/bash
yum -y install openshift-ansible screen bind-utils
sed -i "s/#host_key_checking/host_key_checking = True/" /etc/ansible/ansible.cfg
sed -i "s/#log_path/log_path/" /etc/ansible/ansible.cfg
#export IP=`dig +short master01.[[ domain ]]`
#sed -i "s/openshift_master_default_subdomain=.*/openshift_master_default_subdomain=$IP.xip.io/" /root/hosts
#sed -i "s/openshift_master_cluster_hostname=.*/openshift_master_cluster_hostname=$IP.xip.io/" /root/hosts
#sed -i "s/openshift_master_cluster_public_hostname=.*/openshift_master_cluster_public_hostname=$IP.xip.io/" /root/hosts
[% if type == 'ovirt' %]
sh /root/fix_inventory.sh
[% endif %]
ansible-playbook -i /root/inventory /usr/share/ansible/openshift-ansible/playbooks/prerequisites.yml
ansible-playbook -i /root/inventory /usr/share/ansible/openshift-ansible/playbooks/deploy_cluster.yml
