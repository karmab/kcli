{% if extra_master_args %}
{% set extra_args = extra_master_args %}
{% endif %}

apt-get -y install curl
curl -sfL https://get.k3s.io | {{ install_k3s_args }} K3S_TOKEN={{ token }} sh -s - server {{ '--cluster-init' if masters > 1 else '' }} {{ extra_args|join(" ") }}
export IP={{ api_ip if masters > 1 else '$(hostname -I | cut -f1 -d" ")' }}
export K3S_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
sed "s/127.0.0.1/$IP/" /etc/rancher/k3s/k3s.yaml > /root/kubeconfig
if [ -d /root/manifests ] ; then
 mkdir -p /var/lib/rancher/k3s/server
 mv /root/manifests /var/lib/rancher/k3s/server
fi
{% if sdn != None and sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
kubectl create -f https://raw.githubusercontent.com/cilium/cilium/{{ 'cilium/cilium' | github_version(cilium_version|default('latest')) }}/install/kubernetes/quick-install.yaml
{% endif %}
apt-get -y remove curl
