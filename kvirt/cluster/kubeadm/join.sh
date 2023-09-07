#!/usr/bin/env bash

TOKEN={{ token }}
CTLPLANES="{{ '--control-plane --certificate-key %s' % cert_key if 'ctlplane' in name else '' }}"

echo {{ first_ip }} api.{{ cluster }}.{{ domain }} >> /etc/hosts
kubeadm join {{ first_ip }}:6443 --token $TOKEN --discovery-token-unsafe-skip-ca-verification $CTLPLANES

{% if registry %}
echo api.{{ cluster }}.{{ domain }} > /etc/containers/registries.conf.d/003-{{ cluster }}.conf
{% endif %}
