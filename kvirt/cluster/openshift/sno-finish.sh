#!/usr/bin/env bash

echo -e "#!/bin/sh\n exit 0" > /usr/local/bin/install-to-disk.sh
echo "Waiting for /opt/openshift/.bootkube.done"
until ls /opt/openshift/.bootkube.done; do
  sleep 5
done

for vg in $(vgs -o name --noheadings) ; do vgremove -y $vg ; done
for pv in $(pvs -o name --noheadings) ; do pvremove -y $pv ; done
{% if sno_disk != None %}
install_device='/dev/{{ sno_disk | basename }}'
{% else %}
install_device=/dev/$(lsblk | grep disk | head -1 | cut -d" " -f1)
if [ "$install_device" == "/dev/" ]; then
  echo "Can't find appropriate device to install to"
  exit 1
fi
{% endif %}

{% if sno_dns %}
[ -f /opt/openshift/master.ign.ori ] || cp /opt/openshift/master.ign /opt/openshift/master.ign.ori
cat /opt/openshift/master.ign.ori | jq ".storage.files |= . + [{\"mode\": 420, \"path\": \"/etc/hostname\", \"contents\": {\"source\":\"data:,{{ cluster }}-sno.{{ domain }}%0A\",\"verification\": {}}}]" > /opt/openshift/master.ign
{% endif %}

firstboot_args='console=tty0 rd.neednet=1 {{ extra_args|default("") }}'
echo "Executing coreos-installer with ignition file /opt/openshift/master.ign and device $install_device"
coreos-installer install --firstboot-args="${firstboot_args}" --ignition=/opt/openshift/master.ign $install_device

if [ -d /sys/firmware/efi ] ; then
 NUM=$(efibootmgr -v | grep 'DVD\|CD' | cut -f1 -d' ' | sed 's/Boot000\([0-9]\)\*/\1/')
 efibootmgr -b 000$NUM -B $NUM
 mount /${install_device}2 /mnt
 efibootmgr -d ${install_device} -p 2 -c -L RHCOS -l \\EFI\\BOOT\\BOOTX64.EFI
fi

shutdown -r now "Bootstrap completed, restarting node"
