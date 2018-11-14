oc apply -f /root/multus.yml
oc apply -f /root/cni-plugins.yml
oc apply -f /root/ovs-cni.yml
yum -y install openvswitch
systemctl start openvswitch
systemctl enable openvswitch
ovs-vsctl add-br br1
ovs-vsctl add-port br1 eth1
oc apply -f /root/nad_br1.yml
