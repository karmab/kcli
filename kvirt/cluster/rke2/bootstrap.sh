#!/usr/bin/env bash

{% if config_type in ['aws', 'gcp', 'ibm'] %}
API_IP={{ "api.%s.%s" % (cluster, domain) }}
echo $(hostname -I) api.{{ cluster }}.{{ domain }} >> /etc/hosts
{% elif sslip|default(False) %}
API_IP={{ "api.%s.sslip.io" % api_ip.replace('.', '-').replace(':', '-') }}
{% else %}
API_IP={{ api_ip }}
{% endif %}

DOMAIN={{ domain }}
SDN={{ sdn|lower }}
TOKEN={{ token }}

if [ -f /etc/redhat-release ] ; then
 setenforce 0
 sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
fi

curl -sfL https://get.rke2.io | sh -

mkdir -p /etc/rancher/rke2
echo """token: $TOKEN
cni:
{% if multus %}
- multus
{% endif %}
- $SDN
tls-san:
- api.{{ cluster }}.{{ domain }}
- ${API_IP}
{% if workers != 0 %}
node-taint:
- CriticalAddonsOnly=true:NoExecute
{% endif %}
""" > /etc/rancher/rke2/config.yaml

if [ -d /root/manifests ] ; then
  mkdir -p /var/lib/rancher/rke2/server
  mv /root/manifests /var/lib/rancher/rke2/server/manifests
fi
systemctl enable --now rke2-server.service

# config cluster credentials
cp /etc/rancher/rke2/rke2.yaml /root/kubeconfig
sed -i "s/127.0.0.1/$API_IP/" /root/kubeconfig
chown root:root /root/kubeconfig
export KUBECONFIG=/root/kubeconfig
echo "export KUBECONFIG=/root/kubeconfig" >> /root/.bashrc
echo "export PATH=/var/lib/rancher/rke2/bin:$PATH" >> /root/.bashrc
