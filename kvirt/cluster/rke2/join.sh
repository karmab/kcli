#!/usr/bin/env bash

{% if api_ip == None %}
{% set api_ip = '{0}-ctlplane-1'.format(cluster)|kcli_info('ip') if scale|default(False) and 'ctlplane-0' in name else first_ip %}
{% endif %}

TOKEN={{ token }}

echo {{ api_ip }} api.{{ cluster }}.{{ domain }} >> /etc/hosts

if [ -f /etc/redhat-release ] ; then
 setenforce 0
 sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
fi

ROLE={{ "agent" if 'worker' in name else "server" }}
curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE=$ROLE sh -
mkdir -p /etc/rancher/rke2
echo """server: https://api.{{ cluster }}.{{ domain }}:9345
token: $TOKEN""" > /etc/rancher/rke2/config.yaml

{% if 'ctlplane' in name %}
echo """tls-san:
- api.{{ cluster }}.{{ domain }}""" >> /etc/rancher/rke2/config.yaml
{% endif %}

systemctl enable --now rke2-$ROLE.service

echo "export PATH=/var/lib/rancher/rke2/bin:$PATH" >> /root/.bashrc
