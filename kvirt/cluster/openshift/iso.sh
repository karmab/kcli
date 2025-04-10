#!/bin/bash
{% set nics = [] %}
{% if disable_nics is defined %}
{% for nic in disable_nics %}
{% do nics.append("ip=" + nic + ":off") %}
{% endfor %}
{% endif %}

for vg in $(vgs -o name --noheadings) ; do vgremove -y $vg ; done
for pv in $(pvs -o name --noheadings) ; do pvremove -y $pv ; done
for disk in $(lsblk -dno NAME,TYPE | awk '$2=="disk" {print $1}') ; do
  wipefs -a /dev/$disk
done
{% if install_disk is defined %}
install_device={{ install_disk|diskpath }}
{% else %}
install_device=/dev/$(lsblk | grep disk | head -1 | cut -d" " -f1)
if [ "$install_device" == "/dev/" ]; then
  echo "Can't find appropriate device to install to"
  exit 1
fi
{% endif %}

firstboot_args='console=tty0 rd.neednet=1 {{ nics | join(" ") }} {{ extra_args|default("") }}'

{% for net in nets|default([]) %}
{% set nic = nic if nic is defined else net.get('nic', 'ens' + (3 + loop.index0)|string) %}
{{ loop.index0 }}
{% set ip = net.get('ip') %}
{% set netmask = net.get('netmask') or net.get('prefix') %}
{% set gateway = net.get('gateway') %}
{% if dns is not defined %}
{% set dns = net.get('dns') or gateway %}
{% endif %}
{% if ip is defined and netmask is defined and gateway is defined %}
firstboot_args="$firstboot_args ip={{ "[" + ip + "]" if ':' in ip else ip }}::{{ "[" + gateway + "]" if ':' in gateway else gateway }}:{{ netmask }}:{{ hostname|default("") }}:{{ nic }}:none nameserver={{ "[" + dns + "]" if ':' in dns else dns }}"
{% endif %}
{% endfor %}

if [ -f /root/macs.txt ] ; then
    for dev in $(ls -1 /sys/class/net) ; do
        mac=$(cat /sys/class/net/$dev/address)
        line=$(grep $mac /root/macs.txt)
        [ -z "$line" ] && continue
        hostname=$(echo $line | cut -d";" -f2)
        ip=$(echo $line | cut -d";" -f3)
        echo $ip | grep -q : && ip=[$ip]
        netmask=$(echo $line | cut -d";" -f4)
        gateway=$(echo $line | cut -d";" -f5)
        echo $gateway | grep -q : && gateway=[$gateway]
        nameserver=$(echo $line | cut -d";" -f6)
        echo $nameserver | grep -q : && nameserver=[$nameserver]
        firstboot_args="$firstboot_args ip=$ip::$gateway:$netmask:$hostname:$dev:none nameserver=$nameserver"
        break
    done
fi

{% if disable_ipv6|default(False) %}
firstboot_args="$firstboot_args ipv6.disable=1"
cp /root/config.ign /root/config.ign.ori
while true ; do
  NIC=$(ip r | grep {{ baremetal_cidr|default('default') }} | head -1 | grep -oP '(?<=dev )[^ ]*')
  [ -z $NIC ] || break
  sleep 10
done
NM_DATA=$(echo -e "[connection]\ntype=ethernet\ninterface-name=$NIC\n[ipv6]\nmethod=disabled\n" | base64 -w0)
cat /root/config.ign.ori | jq ".storage.files |= . + [{\"mode\": 384, \"path\": \"/etc/NetworkManager/system-connections/$NIC.nmconnection\", \"contents\": {\"source\":\"data:text/plain;charset=utf-8;base64,$NM_DATA\",\"verification\": {}}}]" > /root/config.ign
{% endif %}

cmd="coreos-installer install --firstboot-args=\"${firstboot_args}\" --ignition=/root/config.ign {{ '--insecure --image-url=' + metal_url if metal_url != None else '' }} ${install_device}"
bash -c "$cmd"
if [ "$?" == "0" ] ; then
  echo "Install Succeeded!"
  if [ -d /sys/firmware/efi ] ; then
    NUM=$(efibootmgr -v | grep 'DVD\|CD' | cut -f1 -d' ' | sed 's/Boot000\([0-9]\)\*/\1/')
    efibootmgr -b 000$NUM -B $NUM
    mount /${install_device}2 /mnt
    efibootmgr -d ${install_device} -p 2 -c -L RHCOS -l \\EFI\\BOOT\\BOOTX64.EFI
  fi
  reboot
else
  echo "Install Failed!"
  exit 1
fi
