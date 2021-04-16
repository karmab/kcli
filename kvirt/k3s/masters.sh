{% set extra_args = [] %}
{% for component in disabled_components %}
{% do extra_args.append("--disable " + component) %}
{% endfor %}
apt-get -y install curl
{% if sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
{% endif %}
curl -sfL https://get.k3s.io | {{ "INSTALL_K3S_EXEC='--disable-network-policy --no-flannel'" if sdn != "flannel" else '' }} INSTALL_K3S_CHANNEL={{ install_k3s_channel }} INSTALL_K3S_VERSION={{ install_k3s_version if install_k3s_version != "latest" else '' }} K3S_TOKEN={{ token }} K3S_URL=https://{{ api_ip }}:6443 sh -s - server {{ extra_args|join(" ") }}
