#!/usr/bin/env bash

if [ -d /root/manifests ] ; then
 mkdir -p /etc/microshift/manifests
 cp /root/manifests/*y*ml /etc/microshift/manifests
fi

{% set extra_packages = [] %}
{% if olm %}
{{ extra_packages.append("microshift-olm") or "" }}
{% endif %}

{% if multus %}
{{ extra_packages.append("microshift-multus") or "" }}
{% endif %}

dnf -y install microshift {{ extra_packages|join(", ") }}

BASEDOMAIN={{ "$(hostname)" if sslip else cluster + '.' + domain }}
IP=$(hostname -I | cut -d' ' -f1)

systemctl enable --now microshift
