sysctl -w net.ipv4.ip_forward=1
sysctl -p /etc/sysctl.conf
useradd stack
echo stack | passwd --stdin stack
echo "stack ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/stack
chmod 0440 /etc/sudoers.d/stack
yum install -y python-rdomanager-oscplugin vim screen tmux libguestfs-tools
yum -y install rhosp-director-images rhosp-director-images-ipa
systemctl stop NetworkManager
systemctl disable NetworkManager
systemctl restart network
yum -y -q update
sed -i /requiretty/d /etc/sudoers
su - stack -c "ls"
cp -R /root/stack/* /home/stack/
chown -R stack:stack /home/stack/*
su - stack -c "openstack undercloud install"
