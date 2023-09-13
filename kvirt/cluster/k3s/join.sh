{% set extra_args =  extra_worker_args or extra_args %}

{% if api_ip == None %}
{% set api_ip = '{0}-ctlplane-1'.format(cluster)|kcli_info('ip') if scale|default(False) and 'ctlplane-0' in name else first_ip %}
{% endif %}

curl -sfL https://get.k3s.io | K3S_URL=https://{{ api_ip }}:6443 K3S_TOKEN={{ token }} {{ install_k3s_args|default([])|join(' ') }} sh -s - agent {{ extra_args|join(' ') }}
