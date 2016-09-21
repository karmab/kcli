mkdir /isos
mkdir /vms
echo '/vms *(rw)'  >>  /etc/exports
echo '/isos *(rw)'  >>  /etc/exports
exportfs -r
chown vdsm.kvm /vms
chown vdsm.kvm /isos
systemctl start nfs ; systemctl enable nfs
