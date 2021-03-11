{% set extra_args = [] %}
{% for component in disabled_components %}
{% do extra_args.append("--disable " + component) %}
{% endfor %}
apt-get -y install curl
{% if sdn == 'cilium' %}
mount bpffs -t bpf /sys/fs/bpf
{% endif %}
curl -sfL https://get.k3s.io | {{ "INSTALL_K3S_EXEC='--disable-network-policy --no-flannel'" if sdn != "flannel" else '' }} K3S_TOKEN={{ token }} K3S_URL=https://{{ api_ip }}:6443 sh -s - server {{ extra_args|join(" ") }}
