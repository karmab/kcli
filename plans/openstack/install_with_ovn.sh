export ADMIN_PASSWORD="{{ password }}"
echo `hostname -I` `hostname -s` >> /etc/hosts
yum update -y
yum install -y openstack-packstack wget vim screen
HOME=/root packstack --gen-answer-file=/root/answers.txt
sed -i "s/CONFIG_SWIFT_INSTALL=y/CONFIG_SWIFT_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_HEAT_INSTALL=n/CONFIG_HEAT_INSTALL=y/" /root/answers.txt
sed -i "s/CONFIG_NAGIOS_INSTALL=y/CONFIG_NAGIOS_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_PROVISION_DEMO=y/CONFIG_PROVISION_DEMO=n/" /root/answers.txt
sed -i "s/CONFIG_SWIFT_INSTALL=y/CONFIG_SWIFT_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_LBAAS_INSTALL=n/CONFIG_LBAAS_INSTALL=y/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVN_BRIDGE_MAPPINGS=.*/CONFIG_NEUTRON_OVN_BRIDGE_MAPPINGS=external:br-ex/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVN_BRIDGE_IFACES=/CONFIG_NEUTRON_OVN_BRIDGE_IFACES=br-ex:eth0/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVN_EXTERNAL_PHYSNET=.*/CONFIG_NEUTRON_OVN_EXTERNAL_PHYSNET=external/" /root/answers.txt
sed -i "s/CONFIG_DEBUG_MODE=n/CONFIG_DEBUG_MODE=y/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_L3_EXT_BRIDGE=.*/CONFIG_NEUTRON_L3_EXT_BRIDGE=provider/" /root/answers.txt
HOME=/root packstack --answer-file=/root/answers.txt
