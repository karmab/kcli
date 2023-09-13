{% set extra_args =  extra_worker_args or extra_args %}

{% if api_ip != None %}
echo {{ api_ip }} api.{{ cluster }}.{{ domain }} >> /etc/hosts
{% endif %}

curl -sfL https://get.k3s.io | K3S_URL=https://api.{{ cluster }}.{{ domain }}:6443 K3S_TOKEN={{ token }} {{ install_k3s_args|default([])|join(' ') }} sh -s - agent {{ extra_args|join(' ') }}
