export ORG="{{ organization }}"
export LOCATION="{{ location }}"
export PASSWORD="{{ password }}"
echo `hostname -I` `hostname -s`.default `hostname -s` >> /etc/hosts
echo `hostname -s`.default > /etc/hostname
# yum -y update
yum -y install satellite wget
#reboot
satellite-installer --scenario satellite --foreman-admin-username admin  --foreman-admin-password ${PASSWORD} --foreman-initial-location ${LOCATION} --foreman-initial-organization ${ORG} --capsule-puppet true --foreman-proxy-puppetca true --foreman-proxy-tftp true --enable-foreman-plugin-discovery
