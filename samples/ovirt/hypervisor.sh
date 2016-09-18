echo `hostname -I` `hostname -s` >> /etc/hosts
yum -y install http://plain.resources.ovirt.org/pub/yum-repo/ovirt-release40.rpm
yum -y install vdsm
sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config
systemctl restart 
echo unix1234 | passwd --stdin root
