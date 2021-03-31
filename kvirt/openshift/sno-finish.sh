#!/usr/bin/env bash

echo -e "#/bin/sh\n exit 0" > /usr/local/bin/install-to-disk.sh
echo "Waiting for /opt/openshift/.bootkube.done"
until ls /opt/openshift/.bootkube.done; do
  sleep 5
done

IP=$(hostname -I | cut -d" " -f1)

sed -i "s/None/$IP/" /root/Corefile

COREDNS="$(cat /root/coredns.yml | base64 -w0)"
COREFILE="$(cat /root/Corefile | base64 -w0)"
FORCEDNS="$(cat /root/99-forcedns | base64 -w0)"
cat /opt/openshift/master.ign | jq ".storage.files |= . + [{\"filesystem\": \"root\", \"mode\": 448, \"path\": \"/etc/kubernetes/manifests/coredns.yml\", \"contents\": {\"source\": \"data:text/plain;charset=utf-8;base64,$COREDNS\", \"verification\": {}}},{\"filesystem\": \"root\", \"mode\": 448, \"path\": \"/etc/kubernetes/Corefile\", \"contents\": {\"source\":\"data:text/plain;charset=utf-8;base64,$COREFILE\",\"verification\": {}}},{\"filesystem\": \"root\", \"mode\": 448, \"path\": \"/etc/NetworkManager/dispatcher.d/99-forcedns\", \"contents\": {\"source\":\"data:text/plain;charset=utf-8;base64,$FORCEDNS\",\"verification\": {}}}]" > /root/master.ign

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

firstboot_args='console=tty0 rd.neednet=1 {{ extra_args|default("") }}'
echo "Executing coreos-installer with ignition file /root/master.ign and device $install_device"
coreos-installer install --firstboot-args="${firstboot_args}" --ignition=/root/master.ign $install_device && shutdown -r now "Bootstrap completed, restarting node"
