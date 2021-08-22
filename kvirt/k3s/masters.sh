{% if extra_master_args %}
{% set extra_args = extra_master_args %}
{% endif %}

apt-get -y install curl
curl -sfL https://get.k3s.io | {{ install_k3s_args }} K3S_TOKEN={{ token }} K3S_URL=https://{{ api_ip }}:6443 sh -s - server {{ extra_args|join(" ") }}
apt-get -y remove curl
