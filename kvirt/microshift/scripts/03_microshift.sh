#!/usr/bin/env bash

dnf -y install microshift
BASEDOMAIN={{ "$(hostname)" if sslip else cluster + '.' + domain }}
sed -i "s@#baseDomain: .*@baseDomain: $BASEDOMAIN@" /etc/microshift/config.yaml.default
sed -i "s@#subjectAltNames:.*@subjectAltNames: \[\"api.$BASEDOMAIN\"\]@" /etc/microshift/config.yaml.default
systemctl enable --now microshift
