useradd stack
echo stack | passwd --stdin stack
echo "stack ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/stack
chmod 0440 /etc/sudoers.d/stack
yum install -y python-rdomanager-oscplugin wget
su - stack -c "wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/undercloud.conf"
