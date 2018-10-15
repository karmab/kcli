PASSWORD="[[ password ]]"
echo ${PASSWORD} | passwd --stdin root
sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config
systemctl restart sshd
yum -y install vdsm
