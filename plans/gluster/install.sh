yum -y install glusterfs-server glusterfs-ganesha glusterfs glusterfs-geo-replication glusterfs-cli samba ctdb #firewalld -y
systemctl start glusterd
systemctl enable glusterd
systemctl start smb
systemctl enable smb
systemctl start nmb
systemctl enable nmb
#tuned-adm profile rhgs-random-io
tuned-adm profile throughput-performance
#sleep 30
#firewall-offline-cmd --add-service=glusterfs
#firewall-offline-cmd --add-service=nfs
#firewall-offline-cmd --add-service=rpc-bind
#firewall-offline-cmd --add-service=samba
#firewall-offline-cmd --runtime-to-permanent
#systemctl start firewalld 
#systemctl enable firewalld 
pvcreate /dev/vdb
pvcreate /dev/vdc
vgcreate /dev/vg_bricks /dev/vdb /dev/vdc
lvcreate -L 50G -T vg_bricks/glusterpool
lvcreate -V 10G -T vg_bricks/glusterpool -n brick-$(hostname -s)-1
lvcreate -V 10G -T vg_bricks/glusterpool -n brick-$(hostname -s)-2
mkfs -t xfs -i size=512 /dev/vg_bricks/brick-$(hostname -s)-1
mkfs -t xfs -i size=512 /dev/vg_bricks/brick-$(hostname -s)-2
mkdir -p /bricks/brick-$(hostname -s)-1
mkdir -p /bricks/brick-$(hostname -s)-2
echo "/dev/vg_bricks/brick-$(hostname -s)-1 /bricks/brick-$(hostname -s)-1 xfs defaults 1 2" >> /etc/fstab
echo "/dev/vg_bricks/brick-$(hostname -s)-2 /bricks/brick-$(hostname -s)-2 xfs defaults 1 2" >> /etc/fstab
mount -a
mkdir -p /bricks/brick-$(hostname -s)-1/brick
mkdir -p /bricks/brick-$(hostname -s)-2/brick
semanage fcontext -a -t glusterd_brick_t /bricks/brick-$(hostname -s)-1/brick
semanage fcontext -a -t glusterd_brick_t /bricks/brick-$(hostname -s)-2/brick
restorecon -Rv /bricks/brick-$(hostname -s)-1/brick
restorecon -Rv /bricks/brick-$(hostname -s)-2/brick
useradd -s /sbin/nologin {{ user }}
(echo {{ user }}; echo {{ password }}) | smbpasswd -a -s {{ user }}
sed -i '/type mgmt/a option rpc-auth-allow-insecure on'  /etc/glusterfs/glusterd.vol
systemctl restart glusterd.service
sleep 5
