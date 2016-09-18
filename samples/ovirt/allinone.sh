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
wget -O  /root/.ovirtshellrc https://raw.githubusercontent.com/karmab/kcli/master/samples/ovirt/ovirtshellrc
echo $PASSWORD | passwd --stdin root
sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config
systemctl restart sshd
yum -y install vdsm
ovirt-shell -E "add host --address `hostname -I` --cluster-name Default --name `hostname -s` --root_password $PASSWORD"
sleep 120
ovirt-shell -E "add storagedomain --name vms --host-name `hostname -s` --type data --storage-type nfs --storage-address `hostname -I` --storage-path /vms"
ovirt-shell -E "add storagedomain --name isos --host-name `hostname -s` --type iso --storage-type nfs --storage-address `hostname -I` --storage-path /isos"
sleep 20
ovirt-shell -E "add storagedomain --name vms --parent-datacenter-name Default"
ovirt-shell -E "add storagedomain --name isos --parent-datacenter-name Default"
