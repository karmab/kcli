mkdir /isos
mkdir /vms
echo '/vms *(rw)'  >>  /etc/exports
echo '/isos *(rw)'  >>  /etc/exports
exportfs -r
chown 36:36 /vms
chown 36:36 /isos
systemctl start nfs ; systemctl enable nfs
