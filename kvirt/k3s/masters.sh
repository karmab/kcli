{% set extra_args = [] %}
{% for component in k3s_extra_args_all %}
{% do extra_args.append(component) %}
{% endfor %}
{% for component in k3s_extra_args_masters %}
{% do extra_args.append(component) %}
{% endfor %}
apt-get -y install curl
curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL={{ install_k3s_channel }} INSTALL_K3S_VERSION={{ install_k3s_version if install_k3s_version != "latest" else '' }} K3S_TOKEN={{ token }} K3S_URL=https://{{ api_ip }}:6443 sh -s - server {{ extra_args|join(" ") }}
apt-get -y remove curl
