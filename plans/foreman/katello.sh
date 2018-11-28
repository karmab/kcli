export ORG="{{ organization }}"
export LOCATION="{{ location }}"
export PASSWORD="{{ password }}"
rpm -ivh https://yum.puppetlabs.com/puppetlabs-release-pc1-el-7.noarch.rpm
yum -y install epel-release https://yum.theforeman.org/releases/{{ foreman_version }}/el7/x86_64/foreman-release.rpm
yum -y localinstall http://fedorapeople.org/groups/katello/releases/yum/{{ katello_version }}/katello/el7/x86_64/katello-repos-latest.rpm
yum -y install foreman-release-scl wget katello
#yum-y update
yum -y install katello
echo `hostname -I` `hostname -s`.default `hostname -s` >> /etc/hosts
foreman-installer --scenario katello --foreman-admin-username admin  --foreman-admin-password ${PASSWORD} --foreman-initial-location ${LOCATION} --foreman-initial-organization ${ORG}
