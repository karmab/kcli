#!/bin/bash
{% set nics = [] %}
{% if disable_nics is defined %}
{% for nic in disable_nics %}
{% do nics.append("ip=" + nic + ":off") %}
{% endfor %}
{% endif %}

for vg in $(vgs -o name --noheadings) ; do vgremove -y $vg ; done
for pv in $(pvs -o name --noheadings) ; do pvremove -y $pv ; done
{% if install_disk is defined %}
install_device='/dev/{{ install_disk | basename }}'
{% else %}
install_device=/dev/$(lsblk | grep disk | head -1 | cut -d" " -f1)
if [ "$install_device" == "/dev/" ]; then
  echo "Can't find appropriate device to install to"
  exit 1
fi
{% endif %}

firstboot_args='console=tty0 rd.neednet=1 {{ nics | join(" ") }} {{ extra_args|default("") }}'

{% if ip is defined and netmask is defined and gateway is defined %}
firstboot_args="$firstboot_args ip={{ "[" + ip + "]" if ':' in ip else ip }}::{{ "[" + gateway + "]" if ':' in gateway else gateway }}:{{ netmask }}:{{ hostname|default("") }}:{{ nic|default("ens3") }}:none nameserver={{ "[" + dns|default(gateway) + "]" if ':' in dns|default(gateway) else dns|default(gateway) }}"
{% endif %}

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

cmd="coreos-installer install --firstboot-args=\"${firstboot_args}\" --ignition=/root/config.ign {{ '--insecure --image-url=' + metal_url if metal_url != None else '' }} ${install_device}"
bash -c "$cmd"
if [ "$?" == "0" ] ; then
  echo "Install Succeeded!"
  reboot
else
  echo "Install Failed!"
  exit 1
fi
