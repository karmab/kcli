export ADMIN_PASSWORD="unix1234"
echo `hostname -I` `hostname -s` >> /etc/hosts
subscription-manager repos --enable=rhel-7-server-rh-common-rpms --enable=rhel-7-server-openstack-8-rpms --enable=rhel-ha-for-rhel-7-server-rpms --enable=rhel-7-server-extras-rpms
yum update -y
yum install -y openstack-packstack wget vim screen
HOME=/root packstack --gen-answer-file=/root/answers.txt
sed -i "s/CONFIG_SWIFT_INSTALL=y/CONFIG_SWIFT_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_HEAT_INSTALL=n/CONFIG_HEAT_INSTALL=y/" /root/answers.txt
sed -i "s/CONFIG_NAGIOS_INSTALL=y/CONFIG_NAGIOS_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_PROVISION_DEMO=y/CONFIG_PROVISION_DEMO=n/" /root/answers.txt
sed -i "s/CONFIG_SWIFT_INSTALL=y/CONFIG_SWIFT_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVS_BRIDGE_MAPPINGS=/CONFIG_NEUTRON_OVS_BRIDGE_MAPPINGS=external:br-ex/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVS_BRIDGE_IFACES=/CONFIG_NEUTRON_OVS_BRIDGE_IFACES=br-ex:eth0/" /root/answers.txt
HOME=/root packstack --answer-file=/root/answers.txt
