#!/usr/bin/env bash

{% if api_ip == None %}
{% set api_ip = '{0}-ctlplane-1'.format(cluster)|kcli_info('ip') if scale|default(False) and 'ctlplane-0' in name else first_ip %}
{% endif %}

TOKEN={{ token }}
CTLPLANES="{{ '--control-plane --certificate-key %s' % cert_key if 'ctlplane' in name else '' }}"

echo {{ api_ip }} api.{{ cluster }}.{{ domain }} >> /etc/hosts
kubeadm join {{ api_ip }}:6443 --token $TOKEN --discovery-token-unsafe-skip-ca-verification $CTLPLANES

{% if registry %}
echo api.{{ cluster }}.{{ domain }} > /etc/containers/registries.conf.d/003-{{ cluster }}.conf
{% endif %}
