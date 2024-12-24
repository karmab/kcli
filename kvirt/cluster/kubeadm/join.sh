#!/usr/bin/env bash
{% set api_ip = api_ip or ('{0}-ctlplane-1'.format(cluster)|kcli_info('ip') if scale|default(False) and 'ctlplane-0' in name else first_ip) %}

echo {{ api_ip }} api.{{ cluster }}.{{ domain }} >> /etc/hosts
kubeadm join --config /root/config.yaml
