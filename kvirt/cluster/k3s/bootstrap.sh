{% if extra_ctlplane_args %}
{% set extra_args = extra_ctlplane_args %}
{% endif %}

{% if 'ubuntu' in image %}
apt-get -y install curl
{% endif %}

export IP={{ api_ip if cloud_lb else "$(curl -s ifconfig.me)" if config_type in ['aws', 'gcp', 'ibmcloud'] else '$(hostname -I | cut -f1 -d" ")' }}
curl -sfL https://get.k3s.io | {{ install_k3s_args }} K3S_TOKEN={{ token }} sh -s - server {{ '--cluster-init' if ctlplanes > 1 else '' }} {{ extra_args|join(" ") }} {{ '--tls-san $IP' }}
export K3S_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
sed "s/127.0.0.1/$IP/" /etc/rancher/k3s/k3s.yaml > /root/kubeconfig
if [ -d /root/manifests ] ; then
  mv /root/manifests {{ data_dir|default("/var/lib/rancher/k3s/server") }}
fi
{% if sdn != None and sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
curl -LO https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm -f cilium-linux-amd64.tar.gz
cilium install
{% endif %}
