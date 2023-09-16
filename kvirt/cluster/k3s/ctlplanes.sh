{% if extra_ctlplane_args %}
{% set extra_args = extra_ctlplane_args %}
{% endif %}

{% if 'ubuntu' in image %}
apt-get -y install curl
{% endif %}
{% if sdn != None and sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
{% endif %}
curl -sfL https://get.k3s.io | {{ install_k3s_args|default("") }} K3S_TOKEN={{ token }} sh -s - server --server https://{{ first_ip }}:6443 {{ extra_args|join(" ") }} --tls-san {{ first_ip }}
