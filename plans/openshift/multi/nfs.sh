# setsebool -P virt_use_nfs 1
for i in `seq -f "%03g" 1 20` ; do
mkdir /pv$i
echo "/pv$i *(rw)"  >>  /etc/exports
chcon -t svirt_sandbox_file_t /pv$i
done
exportfs -r
systemctl start nfs ; systemctl enable nfs-server
