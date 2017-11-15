export ORG="Karmalabs"
export LOCATION="Madrid"
export PASSWORD="unix1234"
rpm -ivh https://yum.puppetlabs.com/puppetlabs-release-pc1-el-7.noarch.rpm
yum -y install epel-release https://yum.theforeman.org/releases/1.15/el7/x86_64/foreman-release.rpm
yum -y install foreman-installer wget
echo `hostname -I` `hostname -s`.default `hostname -s` >> /etc/hosts
foreman-installer --foreman-admin-username admin  --foreman-admin-password $PASSWORD --foreman-initial-location $LOCATION --foreman-initial-organization $ORG
