#!/usr/bin/env bash

if [ -d /root/manifests ] ; then
 mkdir -p /etc/microshift/manifests
 cp /root/manifests/*y*ml /etc/microshift/manifests
fi

dnf -y install microshift {{ 'microshift-olm' if olm|default(False) else '' }} microshift-olm microshift-multus
BASEDOMAIN={{ "$(hostname)" if sslip else cluster + '.' + domain }}
IP=$(hostname -I | cut -d' ' -f1)

microshift show-config > /etc/microshift/config.yaml
python /root/scripts/config.py $BASEDOMAIN $IP
systemctl enable --now microshift
