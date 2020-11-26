#!/bin/bash
{%- set nics = [] -%}
{% if disable_nics is defined -%}
{%- for nic in disable_nics %}
{%- do nics.append("ip=" + nic + ":off") %}
{%- endfor -%}
{%- endif %}
firstboot_args='console=tty0 rd.neednet=1 {{ nics | join(" ") }}'
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

cmd="coreos-installer install --firstboot-args=\"${firstboot_args}\" --ignition=/root/config.ign ${install_device}"
bash -c "$cmd"
if [ "$?" == "0" ] ; then
  echo "Install Succeeded!"
  reboot
else
  echo "Install Failed!"
  exit 1
fi
