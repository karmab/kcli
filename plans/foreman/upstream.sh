rpm -ivh https://yum.puppetlabs.com/puppetlabs-release-pc1-el-7.noarch.rpm
yum -y install epel-release https://yum.theforeman.org/releases/[[ version ]]/el7/x86_64/foreman-release.rpm
yum -y install foreman-installer wget
echo `hostname -I` `hostname -s`.default `hostname -s` >> /etc/hosts
foreman-installer --foreman-admin-username [[ user ]] --foreman-admin-password [[ password ]] --foreman-initial-location [[ location ]] --foreman-initial-organization [[ organization ]]
