#!/bin/bash
{% set nics = [] %}
{% if disable_nics is defined %}
{% for nic in disable_nics %}
{% do nics.append("ip=" + nic + ":off") %}
{% endfor %}
{% endif %}
firstboot_args='console=tty0 rd.neednet=1 {{ nics | join(" ") }} {{ extra_args|default("") }}'
for vg in $(vgs -o name --noheadings) ; do vgremove -y $vg ; done
for pv in $(pvs -o name --noheadings) ; do pvremove -y $pv ; done
if [ -b /dev/vda ]; then
  install_device='/dev/vda'
elif [ -b /dev/sda ]; then
  install_device='/dev/sda'
elif [ -b /dev/nvme0 ]; then
  install_device='/dev/nvme0'
else
  echo "Can't find appropriate device to install to"
  exit 1
fi

{% if ip is defined and netmask is defined and gateway is defined %}
firstboot_args="$firstboot_args ip={{ "[" + ip + "]" if ':' in ip else ip }}::{{ "[" + gateway + "]" if ':' in gateway else gateway }}:{{ netmask }}:{{ hostname|default("") }}:{{ nic|default("ens3") }}:none nameserver={{ "[" + dns|default(gateway) + "]" if ':' in dns|default(gateway) else dns|default(gateway) }}"
{% endif %}

cmd="coreos-installer install --firstboot-args=\"${firstboot_args}\" --ignition=/root/config.ign {{ '--insecure --image-url=' + metal_url if metal_url != None else '' }} ${install_device}"
bash -c "$cmd"
if [ "$?" == "0" ] ; then
  echo "Install Succeeded!"
  reboot
else
  echo "Install Failed!"
  exit 1
fi
