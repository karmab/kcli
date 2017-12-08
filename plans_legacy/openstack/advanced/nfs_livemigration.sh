##Server
echo "/var/lib/nova/instances *(rw,no_root_squash)" >> /etc/exports
yum install nfs-utils -y
systemctl enable nfs-server.service
systemctl start nfs-server.service
chown -R nova:nova /var/lib/nova/instances
iptables -A INPUT -s 192.168.1.0/24 -d 192.168.1.0/24 -p tcp -m multiport --dports 2049 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables-save > /etc/sysconfig/iptables
exportfs -a
HOSTIP=$(hostname -I | tr -d " \t\n\r")
#Client
for COMP in 1 2 3
do
 ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@ospcompute0${COMP} "echo "${HOSTIP}:/var/lib/nova/instances /var/lib/nova/instances nfs auto 0 0" >> /etc/fstab"
 ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@ospcompute0${COMP} "setsebool -P virt_use_nfs=1"
## Needed because of bug mounting nfs with selinux in osp10 BZ: 1402561 -
 ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@ospcompute0${COMP}  "sed -i 's|^#stdio_handler.*$|stdio_handler = \"file\"|g'  /etc/libvirt/qemu.conf"
 ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@ospcompute0${COMP} "systemctl restart libvirtd"
 ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@ospcompute0${COMP}  "mount /var/lib/nova/instances"
done
