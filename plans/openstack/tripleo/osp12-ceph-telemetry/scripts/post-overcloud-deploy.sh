#Install vars
POOL_START="10.147.15.120"
POOL_END="10.147.15.160"
GW="10.147.15.1"
SUB_RANGE='10.147.15.0/24'
FENCEVIRT=False
RALLY=False


# Populate /etc/hosts
source ~/stackrc
echo "#START_AUTO_HOSTS_HERE" > /tmp/servers.txt
openstack server list -f value -c Networks -c Name | sed 's/ctlplane=//g' | awk ' { print $2 " " $1 }' >> /tmp/servers.txt
echo "#END_AUTO_HOSTS_HERE" >> /tmp/servers.txt
sed -ibck '/#START_AUTO_HOSTS_HERE/,/#END_AUTO_HOSTS_HERE/d' /etc/hosts
sudo sh -c 'cat /tmp/servers.txt >> /etc/hosts'
if ! [ -d ~/ansible ] ; then mkdir ~/ansible ; fi
echo "[controller]" > ~/ansible/inventory
cat /tmp/servers.txt | awk '{print $2}' | grep -i ctrl >> ~/ansible/inventory
echo "[compute]" >> ~/ansible/inventory
cat /tmp/servers.txt | awk '{print $2}' | grep -E ^c.$ >> ~/ansible/inventory
echo "[ceph]" >> ~/ansible/inventory
cat /tmp/servers.txt | awk '{print $2}' | grep ceph >> ~/ansible/inventory
cat >> ~/ansible/inventory << __EOF__
[undercloud]
localhost ansible_connection=local
[overcloud:children]
controller
compute
ceph
__EOF__


#Create ansible.cfg file
cat > ~/ansible/ansible.cfg << __EOF__
[defaults]
inventory = ./inventory
remote_user = heat-admin
host_key_checking = False
ask_pass = false
library = /usr/share/openstack-tripleo-validations/validations/library

[privilege_escalation]
become = true
become_method = sudo
become_user = root
become_ask_pass = false
__EOF__

# Create dinamic inventory
cat << EOF > ~/ansible/dinventory
#!/bin/bash
# Unset some things in case someone has a V3 environment loaded
unset OS_IDENTITY_API_VERSION
unset OS_PROJECT_ID
unset OS_PROJECT_NAME
unset OS_USER_DOMAIN_NAME
unset OS_IDENTITY_API_VERSION
source ~/stackrc
DEFPLAN=overcloud
/usr/bin/tripleo-ansible-inventory \$*
EOF
chmod 755 ~/ansible/dinventory
cp -p ~/templates/scripts/overcloudrc* /home/stack

#Run tripleo ansible validations
cd ~/ansible
ansible-playbook -i ~/ansible/dinventory $(grep post-deployment /usr/share/openstack-tripleo-validations/validations/*.yaml | awk -F ":" ' { print $1 }' | sort -u) > /tmp/ansible-validation.txt 2>&1

if grep -E '(ERROR|WARN)' /tmp/ansible-validation.txt ; then
echo "########################WARN OR ERRORS FOUND#################"
echo "########################IN VALIDATIONS#######################"
grep -E '(ERROR|WARN)' /tmp/ansible-validation.txt
echo "#############################################################"
fi


#Create public networks 
cd ~/templates/scripts/
source ~/templates/scripts/overcloudrc
openstack network create public --external --provider-network-type flat --provider-physical-network datacentre
#openstack network create public --external --provider-network-type vlan --provider-physical-network datacentre --provider-segment 515
openstack subnet create public --network public --no-dhcp --allocation-pool start=${POOL_START},end=${POOL_END} --gateway ${GW} --subnet-range ${SUB_RANGE}

#Flavors and projects
openstack flavor create --disk 10 --vcpus 1 --ram 1024 --public m1.cirros
openstack project create maqueta
openstack user create  --project maqueta --password maqueta1234 adminmaqueta
openstack role add --user=adminmaqueta --project=maqueta admin
cp overcloudrc ~/adminmaquetarc
sed -i -e 's/OS_USERNAME=admin/OS_USERNAME=adminmaqueta/g' -e 's/OS_PASSWORD=\(.*\)/OS_PASSWORD=maqueta1234/g' -e 's/OS_PROJECT_NAME=admin/OS_TENANT_NAME=maqueta/g' ~/adminmaquetarc
source ~/adminmaquetarc
#glance image-create --name "cirros" --disk-format qcow2 --container-format bare --file cirros-0.3.5-x86_64-disk.img
wget http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img
#glance image-create --name "rhel73" --disk-format qcow2 --container-format bare --file rhel-guest-image-7.3-35.x86_64.qcow2 --is-public True
glance image-create --name "cirros" --disk-format qcow2 --container-format bare --file cirros-0.3.4-x86_64-disk.img  --visibility public
sudo tail -1 /home/stack/.ssh/id_rsa.pub > ~/adminmaqueta.pub
nova keypair-add --pub-key ~/adminmaqueta.pub adminmaqueta
neutron net-create private
neutron subnet-create --name 10.0.0.0/24 --allocation-pool start=10.0.0.2,end=10.0.0.254 --gateway 10.0.0.1 private 10.0.0.0/24
neutron router-create router
neutron router-gateway-set router public
neutron router-interface-add router 10.0.0.0/24
openstack security group create adminmaqueta
openstack security group rule create --dst-port 22 adminmaqueta
openstack security group rule create --protocol ICMP adminmaqueta

cat > ~/user-data.yaml << __EOF__
debug: True
ssh_pwauth: True
disable_root: false
chpasswd:
  list: |
    root:unix1234
    cirros:unix1234
  expire: false
runcmd:
- sed -i'.orig' -e's/without-password/yes/' /etc/ssh/sshd_config
- service sshd restart
__EOF__
nova boot --flavor m1.cirros --security-groups adminmaqueta --key-name adminmaqueta --user-data ~/user-data.yaml --image cirros --nic net-id=`neutron net-show private -c id -f value` maqueta1
openstack floating ip create public
sleep 15
openstack server add floating ip maqueta1 $(openstack floating ip list -c "Floating IP Address" -f value)
sleep 15
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null cirros@$(openstack floating ip list -c "Floating IP Address" -f value) "cat /etc/fstab && echo "working ok""

####
#Configure fence-virt on the host
###
if [ ${FENCEVIRT} = True ] ; then
HOSTIP=$(cat instackenv.json | grep pm_addr | uniq | awk -F "\"" '{ print $4}')
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${HOSTIP}  yum install fence-virt fence-virtd fence-virtd-multicast fence-virtd-libvirt
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${HOSTIP} mkdir -p /etc/cluster
cat > ~/fence_virt.conf << __EOF__
fence_virtd {
	listener = "multicast";
	backend = "libvirt";
}

listeners {
	multicast {
		key_file = "/etc/cluster/fence_xvm.key";
		address = "225.0.0.12";
		# Needed on Fedora systems
		interface = "virbr4";
                family = "ipv4";
                port = "1229";
	}
}

backends {
	libvirt { 
		uri = "qemu:///system";
	}
}
__EOF__
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ~/fence_virt.conf root@${HOSTIP}:/etc/fence_virt.conf
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${HOSTIP}  systemctl enable fence_virtd
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${HOSTIP}  systemctl start fence_virtd
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${HOSTIP} iptables -I INPUT -p udp -m udp --dport 1229 -j ACCEPT
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@${HOSTIP} iptables -I INPUT -p tcp -m tcp --dport 1229 -j ACCEPT
fi



# (the following iscsi_use_multipath options is valid for both iscsi+FC as protocol)
# (reference https://docs.openstack.org/newton/config-reference/block-storage/drivers/emc-vnx-driver.html#multipath-setup)
#for i in ` nova list  | grep -i comp | awk '{print $12}' |  cut -f2 -d "="`; do ssh heat-admin@$i 'sudo openstack-config --set /etc/nova/nova.conf libvirt iscsi_use_multipath True';done
#for i in ` nova list  | grep -i comp | awk '{print $12}' |  cut -f2 -d "="`; do ssh heat-admin@$i 'sudo openstack-config --set /etc/nova/nova.conf DEFAULT block_device_allocate_retries 120';done
#for i in ` nova list  | grep -i comp | awk '{print $12}' |  cut -f2 -d "="`; do ssh heat-admin@$i 'sudo openstack-config --set /etc/nova/nova.conf DEFAULT block_device_creation_timeout 300';done
#for i in ` nova list  | grep -i comp | awk '{print $12}' |  cut -f2 -d "="`; do ssh heat-admin@$i 'sudo openstack-config --set /etc/nova/nova.conf DEFAULT block_device_allocate_retries_interval 10';done
#yum install sysfsutils sg3_utils device-mapper-multipath



###
#Install rally and run tests
###
if [ ${RALLY} = True ] ; then
mkdir ~/rally_home
sudo chown 65500 ~/rally_home
cd ~/rally_home && git clone ssh://git@gitlab.consulting.redhat.com:2222/dparkes/Rally-tasks.git
sudo docker pull rallyforge/rally
sudo docker run --privileged -n rally_dock -t -v ~/rally_home:/home/rally rallyforge/rally
rally-manage db recreate
cat > ~/rally_home/deployment.json << __EOF__
{
    "type": "ExistingCloud",
    "auth_url": "http://10.147.15.42:5000/v3",
   "region_name": "regionOne",
    "endpoint_type": "public",
    "admin": {
        "username": "adminmaqueta",
        "password": "maqueta1234",
        "user_domain_name": "default",
        "project_domain_name": "default",
        "project_name": "maqueta"
    }
}
__EOF__
sudo docker exec -t rally_dock rally deployment create --name acc --filename deployment.json
sudo docker exec -t rally_dock rally deployment check
sudo docker exec -t rally_dock rally task start ~/Rally-tasks/test_plan_total.yaml
fi

###
#Configure Fencing Manually
###
#pcs stonith create ilo_fence_emhrh015 fence_ipmilan pcmk_host_list=emhrh015 ipaddr=10.67.37.146 login=Administrator passwd=maqueta1234 lanplus=1 cipher=1 op monitor interval=60s
#pcs stonith create ilo_fence_emhrh016 fence_ipmilan pcmk_host_list=emhrh016 ipaddr=10.67.37.147 login=Administrator passwd=maqueta1234 lanplus=1 cipher=1 op monitor interval=60s
#pcs stonith create ilo_fence_emhrh017 fence_ipmilan pcmk_host_list=emhrh017 ipaddr=10.67.37.154 login=Administrator passwd=maqueta1234 lanplus=1 cipher=1 op monitor interval=60s
#pcs constraint location ilo_fence_emhrh015 avoids emhrh015
#pcs constraint location ilo_fence_emhrh016 avoids emhrh016
#pcs constraint location ilo_fence_emhrh017 avoids emhrh017
#pcs property set stonith-enabled=true




### cleanup a node
# Restore from clean failed
#openstack baremetal node manage node1
# running a provide run also the clean
#openstack baremetal node provide node1
# or force the clean
#openstack baremetal node clean --clean-steps '[{"step": "erase_devices_metadata", "interface": "deploy"}]' node1

