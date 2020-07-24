apt-get -y install curl
{% if masters > 1 %}
curl -sfL https://get.k3s.io | sh -s - server --datastore-endpoint="{{ datastore_endpoint }}"
export IP={{ api_ip }}
{% else %}
curl -sfL https://get.k3s.io | sh -
export IP=$(hostname -I | cut -f1 -d" ")
{% endif %}
export K3S_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
echo "curl -sfL https://get.k3s.io | K3S_URL=https://$IP:6443 K3S_TOKEN=$K3S_TOKEN sh -" > /root/join.sh
sed "s/127.0.0.1/$IP/" /etc/rancher/k3s/k3s.yaml > /root/kubeconfig
