URI="qemu+ssh://root@192.168.122.1/system"
virsh -c $URI destroy master0
virsh -c $URI undefine master0
virsh -c $URI destroy bootstrap
virsh -c $URI undefine bootstrap
ssh root@192.168.122.1 rm -rf /var/lib/libvirt/images/bootstrap* /var/lib/libvirt/images/coreos_base /var/lib/libvirt/images/master* /var/lib/libvirt/images/worker.ign master-0.ign
virsh -c $URI pool-refresh default
virsh -c $URI net-undefine testk
rm -rf terraform.*
