export ADMIN_PASSWORD="unix1234"
echo `hostname -I` `hostname -s` >> /etc/hosts
yum update -y
yum install -y openstack-packstack wget vim screen
ssh-keyscan -H `hostname -I` >> ~/.ssh/known_hosts
ssh-keyscan -H ospcontroller >> ~/.ssh/known_hosts
ssh-keyscan -H ospcompute01 >> ~/.ssh/known_hosts
ssh-keyscan -H ospcompute02 >> ~/.ssh/known_hosts
ssh-keyscan -H ospcompute03 >> ~/.ssh/known_hosts
HOME=/root packstack --gen-answer-file=/root/answers.txt --ssh-public-key=/root/.ssh/id_rsa.pub
sed -i "s/CONFIG_SWIFT_INSTALL=y/CONFIG_SWIFT_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_HEAT_INSTALL=n/CONFIG_HEAT_INSTALL=y/" /root/answers.txt
sed -i "s/CONFIG_NAGIOS_INSTALL=y/CONFIG_NAGIOS_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_PROVISION_DEMO=y/CONFIG_PROVISION_DEMO=n/" /root/answers.txt
sed -i "s/CONFIG_SWIFT_INSTALL=y/CONFIG_SWIFT_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_LBAAS_INSTALL=n/CONFIG_LBAAS_INSTALL=y/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVS_BRIDGE_MAPPINGS=.*/CONFIG_NEUTRON_OVS_BRIDGE_MAPPINGS=external:br-ex/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVS_BRIDGE_IFACES=/CONFIG_NEUTRON_OVS_BRIDGE_IFACES=br-ex:eth0/" /root/answers.txt
sed -i "s/CONFIG_DEBUG_MODE=n/CONFIG_DEBUG_MODE=y/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_L3_EXT_BRIDGE=.*/CONFIG_NEUTRON_L3_EXT_BRIDGE=provider/" /root/answers.txt
sed -i "s/CONFIG_COMPUTE_HOSTS=.*/CONFIG_COMPUTE_HOSTS=ospcompute01,ospcompute02,ospcompute03/" /root/answers.txt

HOME=/root packstack --answer-file=/root/answers.txt
