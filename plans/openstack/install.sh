export ADMIN_PASSWORD="[[ password ]]"
echo `hostname -I` `hostname -s` >> /etc/hosts
yum update -y
yum install -y openstack-packstack wget vim screen
HOME=/root packstack --gen-answer-file=/root/answers.txt
[% if swift %]
sed -i "s/CONFIG_SWIFT_INSTALL=y/CONFIG_SWIFT_INSTALL=n/" /root/answers.txt
[% endif %]
sed -i "s/CONFIG_HEAT_INSTALL=n/CONFIG_HEAT_INSTALL=y/" /root/answers.txt
sed -i "s/CONFIG_NAGIOS_INSTALL=y/CONFIG_NAGIOS_INSTALL=n/" /root/answers.txt
sed -i "s/CONFIG_PROVISION_DEMO=y/CONFIG_PROVISION_DEMO=n/" /root/answers.txt
[% if not ceilometer %]
sed -i "s/CONFIG_CEILOMETER_INSTALL=y/CONFIG_CEILOMETER_INSTALL=n/" /root/answers.txt
[% endif %]
[% if not aodh %]
sed -i "s/CONFIG_AODH_INSTALL=y/CONFIG_AODH_INSTALL=n/" /root/answers.txt
[% endif %]
[% if lbaas %]
sed -i "s/CONFIG_LBAAS_INSTALL=n/CONFIG_LBAAS_INSTALL=y/" /root/answers.txt
[% endif %]
[% if ovn %]
sed -i "s/CONFIG_NEUTRON_OVN_BRIDGE_MAPPINGS=.*/CONFIG_NEUTRON_OVN_BRIDGE_MAPPINGS=extnet:br-ex/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVN_BRIDGE_IFACES=/CONFIG_NEUTRON_OVN_BRIDGE_IFACES=br-ex:eth0/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVN_EXTERNAL_PHYSNET=.*/CONFIG_NEUTRON_OVN_EXTERNAL_PHYSNET=extnet/" /root/answers.txt
[% else %]
sed -i "s/CONFIG_NEUTRON_OVS_BRIDGE_MAPPINGS=.*/CONFIG_NEUTRON_OVS_BRIDGE_MAPPINGS=extnet:br-ex/" /root/answers.txt
sed -i "s/CONFIG_NEUTRON_OVS_BRIDGE_IFACES=/CONFIG_NEUTRON_OVS_BRIDGE_IFACES=br-ex:eth0/" /root/answers.txt
[% endif %]
sed -i "s/CONFIG_DEBUG_MODE=n/CONFIG_DEBUG_MODE=y/" /root/answers.txt
#sed -i "s/CONFIG_NEUTRON_L3_EXT_BRIDGE=.*/CONFIG_NEUTRON_L3_EXT_BRIDGE=provider/" /root/answers.txt
[% if panko %]
sed -i "s/CONFIG_PANKO_INSTALL=n/CONFIG_PANKO_INSTALL=y/" /root/answers.txt
[% endif %]
[% if sahara %]
sed -i "s/CONFIG_SAHARA_INSTALL=n/CONFIG_SAHARA_INSTALL=y/" /root/answers.txt
[% endif %]
[% if trove %]
sed -i "s/CONFIG_TROVE_INSTALL=n/CONFIG_TROVE_INSTALL=y/" /root/answers.txt
[% endif %]
[% if magnum %]
sed -i "s/CONFIG_MAGNUM_INSTALL=n/CONFIG_MAGNUM_INSTALL=y/" /root/answers.txt
[% endif %]
HOME=/root packstack --answer-file=/root/answers.txt
