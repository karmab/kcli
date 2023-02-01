#!/usr/bin/env bash

if [ -d /root/manifests ] ; then
 mkdir -p /etc/microshift/manifests
 cp /root/manifests/*y*ml /etc/microshift/manifests
fi

dnf -y install microshift
BASEDOMAIN={{ "$(hostname)" if sslip else cluster + '.' + domain }}
sed -i "s@#baseDomain: .*@baseDomain: $BASEDOMAIN@" /etc/microshift/config.yaml.default
sed -i "s@#subjectAltNames:.*@subjectAltNames: \[\"api.$BASEDOMAIN\"\]@" /etc/microshift/config.yaml.default
mv /etc/microshift/config.yaml.default /etc/microshift/config.yaml
systemctl enable --now microshift
