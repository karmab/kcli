subscription-manager repos --enable=rhel-7-server-supplementary-rpms --enable=rhel-7-server-rhv-4-mgmt-agent-rpms --enable=rhel-7-server-rhv-4.0-rpms
yum -y install ovirt-hosted-engine-setup ovirt-engine-cli
sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config
systemctl restart sshd
PASSWORD="unix1234"
echo $PASSWORD | passwd --stdin root
