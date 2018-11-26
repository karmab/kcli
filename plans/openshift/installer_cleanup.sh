URI="qemu+ssh://root@192.168.122.1/system"
virsh -c ${URI} destroy testk-master-0
virsh -c ${URI} undefine testk-master-0
virsh -c ${URI} destroy testk-bootstrap
virsh -c ${URI} undefine testk-bootstrap
ssh root@192.168.122.1 rm -rf /var/lib/libvirt/images/testk-* /var/lib/libvirt/images/coreos_base
virsh -c ${URI} pool-refresh default
virsh -c ${URI} net-destroy [[ cluster ]]
virsh -c ${URI} net-undefine [[ cluster ]]
rm -rf terraform.*
rm -rf /tmp/openshift-install-*
rm -rf  ~/.cache/openshift-install
