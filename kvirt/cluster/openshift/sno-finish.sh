#!/usr/bin/env bash

echo -e "#!/bin/sh\n exit 0" > /usr/local/bin/install-to-disk.sh
until ls /opt/openshift/.bootkube.done > /dev/null 2>&1 ; do
  echo "Waiting for /opt/openshift/.bootkube.done"
  sleep 5
done

for vg in $(vgs -o name --noheadings) ; do vgremove -y $vg ; done
for pv in $(pvs -o name --noheadings) ; do pvremove -y $pv ; done
{% if sno_disk != None %}
install_device={{ '/dev/%s' % sno_disk|basename if '/dev/' not in sno_disk else sno_disk }}
{% else %}
install_device=$(lsblk -f -r | grep xfs | grep root | head -1 | cut -d" " -f1 | sed 's/[0-9]\+$//' | sed 's/p$//' )
if [ -z $install_device ] ; then
install_device=$(lsblk | grep disk | head -1 | cut -d" " -f1)
fi
install_device=/dev/$install_device
{% endif %}
if [ ! -b $install_device ]; then
  echo "Can't find appropriate device to install to. $install_device not found"
  exit 1
fi

{% if sno_dns %}
[ -f /opt/openshift/master.ign.ori ] || cp /opt/openshift/master.ign /opt/openshift/master.ign.ori
cat /opt/openshift/master.ign.ori | jq ".storage.files |= . + [{\"mode\": 420, \"path\": \"/etc/hostname\", \"contents\": {\"source\":\"data:,{{ cluster }}-sno.{{ domain }}%0A\",\"verification\": {}}}]" > /opt/openshift/master.ign
{% endif %}

{% if disable_ipv6|default(False) %}
[ -f /opt/openshift/master.ign.ori ] || cp /opt/openshift/master.ign /opt/openshift/master.ign.ori
NIC=$(ip r | grep {{ baremetal_cidr or 'default' }} | head -1 | grep -oP '(?<=dev )[^ ]*')
NM_DATA=$(echo -e "[connection]\ntype=ethernet\ninterface-name=$NIC\n[ipv6]\nmethod=disabled\n" | base64 -w0)
cat /opt/openshift/master.ign.ori | jq ".storage.files |= . + [{\"mode\": 384, \"path\": \"/etc/NetworkManager/system-connections/$NIC.nmconnection\", \"contents\": {\"source\":\"data:text/plain;charset=utf-8;base64,$NM_DATA\",\"verification\": {}}}]" > /opt/openshift/master.ign
{% endif %}

if [ -f /root/kubeconfig ] ; then
 BASE64=$(cat /root/kubeconfig | base64 -w0)
 [ -f /opt/openshift/master.ign.ori ] || cp /opt/openshift/master.ign /opt/openshift/master.ign.ori
 cat /opt/openshift/master.ign.ori | jq ".storage.files |= . + [{\"mode\": 420, \"path\": \"/etc/kubernetes/kubeconfig.{{ cluster }}\", \"contents\": {\"source\":\"data:text/plain;charset=utf-8;base64,$BASE64\",\"verification\": {}}}]" > /opt/openshift/master.ign
fi

firstboot_args='console=tty0 rd.neednet=1 {{ sno_extra_args|default("") }}'
echo "Executing coreos-installer with ignition file /opt/openshift/master.ign and device $install_device"
coreos-installer install --firstboot-args="${firstboot_args}" --ignition=/opt/openshift/master.ign $install_device

if [ -d /sys/firmware/efi ] ; then
 for NUM in $(efibootmgr -v | grep 'DVD\|CD\|RHCOS' | cut -f1 -d' ' | sed 's/Boot\([0-9,A-F,a-f]\{4\}\)\*/\1/'); do
   efibootmgr -b $NUM -B
 done

 mount /${install_device}2 /mnt
 efibootmgr -d ${install_device} -p 2 -c -L RHCOS -l \\EFI\\BOOT\\BOOTX64.EFI
fi

{% if not sno_debug %}
shutdown -r now "Bootstrap completed, restarting node"
{% endif %}
