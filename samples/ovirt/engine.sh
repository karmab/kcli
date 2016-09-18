echo `hostname -I` `hostname -s` >> /etc/hosts
yum -y install http://plain.resources.ovirt.org/pub/yum-repo/ovirt-release40.rpm
yum -y install ovirt-engine wget
wget -O /root/answers.txt https://raw.githubusercontent.com/karmab/kcli/master/samples/ovirt/answers.txt
sed -i "s/0000/`hostname -s`/" /root/answers.txt
mkdir /isos
mkdir /vms
echo '/vms *(rw)'  >>  /etc/exports
echo '/isos *(rw)'  >>  /etc/exports
chown vdsm.kvm /vms
chown vdsm.kvm /isos
systemctl start nfs ; systemctl enable nfs
engine-setup --config=/root/answers.txt
