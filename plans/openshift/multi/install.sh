#!/bin/bash
yum -y install openshift-ansible screen bind-utils
sed -i "s/#host_key_checking/host_key_checking = True/" /etc/ansible/ansible.cfg
sed -i "s/#log_path/log_path/" /etc/ansible/ansible.cfg
{% if deploy %}
sleep 360
{% endif %}
{% if type == 'kvm' %}
export MASTERIP=`dig +short m01.{{ domain }}`
{% if infras > 0 -%}
export ROUTERIP=`dig +short i01.{{ domain }}`
{% else %}
export ROUTERIP=$MASTERIP
{% endif %}
sed -i "s/#openshift_master_default_subdomain=.*/openshift_master_default_subdomain=app.$ROUTERIP.xip.io/" /root/inventory
sed -i "s/#openshift_master_cluster_hostname=.*/openshift_master_cluster_hostname=$MASTERIP.xip.io/" /root/inventory
sed -i "s/#openshift_master_cluster_public_hostname=.*/openshift_master_cluster_public_hostname=$MASTERIP.xip.io/" /root/inventory
{% elif type == 'ovirt' %}
sh /root/ovirt_fix_inventory.sh
rm -rf /root/ovirt_fix_inventory.sh
{% endif %}
ansible-playbook -i /root/inventory /usr/share/ansible/openshift-ansible/playbooks/prerequisites.yml && ansible-playbook -i /root/inventory /usr/share/ansible/openshift-ansible/playbooks/deploy_cluster.yml
