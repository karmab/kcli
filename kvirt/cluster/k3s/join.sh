{% set extra_args =  extra_worker_args or extra_args %}
{% set firstctlplane = cluster + '-ctlplane-0' %}
{% set join_ip = firstctlplane|kcli_info('ip', client) %}
curl -sfL https://get.k3s.io | K3S_URL=https://{{ join_ip }}:6443 K3S_TOKEN={{ token }} {{ install_k3s_args|default([])|join(' ') }} sh -s - agent {{ extra_args|join(' ') }}
