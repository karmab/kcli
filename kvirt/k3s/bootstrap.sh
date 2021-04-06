{% set extra_args = [] %}
{% for component in disabled_components %}
{% do extra_args.append("--disable " + component) %}
{% endfor %}
apt-get -y install curl
{% if masters > 1 %}
curl -sfL https://get.k3s.io | {{ "INSTALL_K3S_EXEC='--flannel-backend=none'" if sdn != "flannel" else '' }} INSTALL_K3S_CHANNEL={{ install_k3s_channel }} INSTALL_K3S_VERSION={{ install_k3s_version if install_k3s_version != "latest" else '' }} K3S_TOKEN={{ token }} sh -s - server --cluster-init {{ extra_args|join(" ") }}
export IP={{ api_ip }}
{% else %}
curl -sfL https://get.k3s.io | {{ "INSTALL_K3S_EXEC='--flannel-backend=none'" if sdn != "flannel" else '' }} INSTALL_K3S_CHANNEL={{ install_k3s_channel }} INSTALL_K3S_VERSION={{ install_k3s_version if install_k3s_version != "latest" else '' }} sh -s - server {{ extra_args|join(" ") }}
export IP=$(hostname -I | cut -f1 -d" ")
{% endif %}
export K3S_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
sed "s/127.0.0.1/$IP/" /etc/rancher/k3s/k3s.yaml > /root/kubeconfig
if [ -d /root/manifests ] ; then
 mkdir -p /var/lib/rancher/k3s/server
 mv /root/manifests /var/lib/rancher/k3s/server
fi
{% if sdn == 'cilium' %}
echo bpffs /sys/fs/bpf bpf defaults 0 0 >> /etc/fstab
mount /sys/fs/bpf
kubectl create -f https://raw.githubusercontent.com/cilium/cilium/{{ 'cilium/cilium' | githubversion(cilium_version|default('latest')) }}/install/kubernetes/quick-install.yaml
{% endif %}
