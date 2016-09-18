export HYPERVISOR_IP="192.168.0.101"
export PASSWORD="unix1234"
echo `hostname -I` `hostname -s` >> /etc/hosts
yum -y install http://plain.resources.ovirt.org/pub/yum-repo/ovirt-release40.rpm
yum -y install ovirt-engine wget
wget -O /root/answers.txt https://raw.githubusercontent.com/karmab/kcli/master/samples/ovirt/answers.txt
sed -i "s/0000/`hostname -s`/" /root/answers.txt
mkdir /isos
mkdir /vms
echo '/vms *(rw)'  >>  /etc/exports
echo '/isos *(rw)'  >>  /etc/exports
exportfs -r
chown vdsm.kvm /vms
chown vdsm.kvm /isos
systemctl start nfs ; systemctl enable nfs
engine-setup --config=/root/answers.txt
sed -i "s@url = @url = https://127.0.0.1:443/ovirt-engine/api@" /root/.ovirtshellrc
sed -i "s/username =/username = admin@internal/" /root/.ovirtshellrc
sed -i "s/password =/password = $PASSWORD/" /root/.ovirtshellrc
sed -i "s/insecure = False/insecure = True/" /root/.ovirtshellrc
ovirt-shell -E "add host --address $HYPERVISOR_IP --cluster-name Default --name hypervisor --root_password $PASSWORD"
ovirt-shell -E "add storagedomain --name vms --host-name hypervisor --type data --storage-type nfs --storage-address $HYPERVISOR_IP --storage-path /vms"
ovirt-shell -E "add storagedomain --name vms --parent-datacenter-name Default"
