apt-get -y install curl
curl -sfL https://get.k3s.io | K3S_TOKEN={{ token }} K3S_URL=https://{{ api_ip }}:6443 sh -s - server
