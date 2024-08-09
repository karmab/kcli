{% if extra_ctlplane_args %}
{% set extra_args = extra_ctlplane_args %}
{% endif %}

{% if 'ubuntu' in image %}
apt-get -y install curl
{% endif %}

# The logic below is to achieve the following
# - for cloud providers. If the API is internal and
# this is a HA cluster. Use the IP of the API load-balancer
# - for cloud providers. If the API is NOT internal.
# use the external IP. This in both the HA and single ctlplane case
# - The last to branches is for on-prem. E.g. vSphere/VMWare
# in HA or single ctlplane scenarios.
{% if cloud_api_internal and ctlplanes > 1 %}
export IP={{ api_ip }}
{% elif config_type in ['aws', 'gcp', 'ibmcloud'] %}
export IP={{ "$(curl -s ifconfig.me)" }}
{% elif ctlplanes > 1 %}
export IP={{ api_ip }}
{% else %}
export IP=$(hostname -I | cut -f1 -d" ")
{% endif %}

curl -sfL https://get.k3s.io | {{ install_k3s_args }} K3S_TOKEN={{ token }} sh -s - server {{ '--cluster-init' if ctlplanes > 1 else '' }} {{ extra_args|join(" ") }} {{ '--tls-san $IP' if not cloud_lb and config_type in ['aws', 'gcp', 'ibmcloud'] else '' }}
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
