export ADMIN_PASSWORD="[[ admin_password ]]"
export EXTERNAL_SUBNET="192.168.122.0/24"
export EXTERNAL_START="192.168.122.200"
export EXTERNAL_END="192.168.122.254"
export EXTERNAL_GATEWAY="192.168.122.1"
export EXTERNAL_FLOATING="192.168.122.202"
cp ~/keystonerc_admin ~/keystonerc_[[ user ]]
sed -i "s/OS_USERNAME=admin/OS_USERNAME=[[ user ]]/" ~/keystonerc_[[ user ]]
sed -i "s/OS_PASSWORD=.*/OS_PASSWORD=[[ password ]]/" ~/keystonerc_[[ user ]]
sed -i "s/OS_TENANT_NAME=admin/OS_TENANT_NAME=[[ project ]]/" ~/keystonerc_[[ user ]]
sed -i "s/OS_PROJECT_NAME=admin/OS_PROJECT_NAME=[[ project ]]/" ~/keystonerc_[[ user ]]
sed -i "s/keystone_admin/keystone_[[ user ]]/" ~/keystonerc_[[ user ]]
source ~/keystonerc_admin
nova flavor-list | grep -q m1.tiny || nova flavor-create --is-public true m1.tiny auto 256 0 1 || openstack flavor create --public m1.tiny --id auto --ram 256 --disk 0 --vcpus 1 --rxtx-factor 1
openstack project create [[ project ]]
openstack user create  --project [[ project ]] --password [[ password ]] [[ user ]]
openstack role add --user=[[ user ]] --project=[[ project ]] admin
grep -q 'type_drivers = vxlan' /etc/neutron/plugin.ini && sed -i 's/type_drivers =.*/type_drivers = vxlan,flat/' /etc/neutron/plugin.ini && systemctl restart neutron-server
neutron net-create extnet --provider:network_type flat --provider:physical_network extnet --router:external || neutron net-create extnet --router:external
neutron subnet-create --name ${EXTERNAL_SUBNET} --allocation-pool start=${EXTERNAL_START},end=${EXTERNAL_END} --disable-dhcp --gateway ${EXTERNAL_GATEWAY} extnet ${EXTERNAL_SUBNET}
OLD_PASSWORD=`grep PASSWORD /root/keystonerc_admin | cut -f2 -d'='`
openstack user password set  --original-password ${OLD_PASSWORD} --password ${ADMIN_PASSWORD} || openstack user set --password ${ADMIN_PASSWORD} admin || keystone password-update --new-password ${ADMIN_PASSWORD}
sed -i "s/OS_PASSWORD=.*/OS_PASSWORD=$ADMIN_PASSWORD/" ~/keystonerc_admin
source ~/keystonerc_[[ user ]]
curl [[ cirros_image ]] > /tmp/c.img
glance image-create --name "cirros" --disk-format qcow2 --container-format bare --file /tmp/c.img
tail -1 /root/.ssh/authorized_keys > ~/[[ user ]].pub
nova keypair-add --pub-key ~/[[ user ]].pub [[ user ]]
neutron net-create private
neutron subnet-create --name 10.0.0.0/24 --allocation-pool start=10.0.0.2,end=10.0.0.254 --gateway 10.0.0.1 private 10.0.0.0/24
neutron router-create router
neutron router-gateway-set router extnet
neutron router-interface-add router 10.0.0.0/24
seq 5 | xargs -I -- neutron floatingip-create extnet
neutron security-group-create [[ user ]]
neutron security-group-rule-create --direction ingress --protocol tcp --port_range_min 22 --port_range_max 22 --remote-ip-prefix 0.0.0.0/0 [[ user ]]
neutron security-group-rule-create --protocol icmp --direction ingress  --remote-ip-prefix 0.0.0.0/0 [[ user ]]
nova boot --flavor m1.tiny --security-groups testk --key-name testk --image cirros --nic net-id=`neutron net-show private -c id -f value` [[ user ]]
sleep 8
ip=$(neutron  floatingip-list -f value -c floating_ip_address  | head -1) ; nova floating-ip-associate [[ user ]] ${ip} || openstack server add floating ip [[ user ]] ${ip}
