sysctl -w net.ipv4.ip_forward=1
sysctl -p /etc/sysctl.conf
useradd stack
echo stack | passwd --stdin stack
echo "stack ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/stack
chmod 0440 /etc/sudoers.d/stack
yum install -y python-rdomanager-oscplugin wget vim screen libguestfs-tools
yum -y install rhosp-director-images rhosp-director-images-ipa
su - stack -c "wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/undercloud.conf"
su - stack -c "wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/undercloud.sh"
su - stack -c "wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/clean.sh"
su - stack -c "wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/instackenv.sh"
su - stack -c "wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/assignprofiles.sh"
su - stack -c "wget https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/deploy.sh"
su - stack -c "mkdir advanced"
su - stack -c "wget -P advanced https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/advanced/instackenv.sh"
su - stack -c "wget -P advanced https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/advanced/assignprofiles.sh"
su - stack -c "wget -P advanced https://raw.githubusercontent.com/karmab/kcli/master/plans/openstack/tripleo/advanced/deploy.sh"
systemctl stop NetworkManager
systemctl disable NetworkManager
yum -y update
#reboot
