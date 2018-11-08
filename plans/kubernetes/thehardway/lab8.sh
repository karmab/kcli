INTERNAL_IP=$( dig +short ${instance})
mkdir -p /etc/kubernetes/config
wget -q --show-progress --https-only --timestamping "https://storage.googleapis.com/kubernetes-release/release/v1.12.0/bin/linux/amd64/kube-apiserver" "https://storage.googleapis.com/kubernetes-release/release/v1.12.0/bin/linux/amd64/kube-controller-manager" "https://storage.googleapis.com/kubernetes-release/release/v1.12.0/bin/linux/amd64/kube-scheduler" "https://storage.googleapis.com/kubernetes-release/release/v1.12.0/bin/linux/amd64/kubectl"
chmod +x kube-apiserver kube-controller-manager kube-scheduler kubectl
mv kube-apiserver kube-controller-manager kube-scheduler kubectl /usr/local/bin
mkdir -p /var/lib/kubernetes
mv ca.pem ca-key.pem kubernetes-key.pem kubernetes.pem service-account-key.pem service-account.pem encryption-config.yaml /var/lib/kubernetes
sed -i "s/INTERNAL_IP/$INTERNAL_IP/"  /root/kube-apiserver.service
mv kube-apiserver.service /etc/systemd/system
mv kube-controller-manager.kubeconfig /var/lib/kubernetes
mv kube-controller-manager.service /etc/systemd/system
mv kube-scheduler.kubeconfig /var/lib/kubernetes
mv kube-scheduler.yaml /etc/kubernetes/config
mv kube-scheduler.service /etc/systemd/system
systemctl daemon-reload
systemctl enable kube-apiserver kube-controller-manager kube-scheduler
systemctl start kube-apiserver kube-controller-manager kube-scheduler
apt-get install -y nginx
mv kubernetes.default.svc.cluster.local /etc/nginx/sites-available/kubernetes.default.svc.cluster.local
ln -s /etc/nginx/sites-available/kubernetes.default.svc.cluster.local /etc/nginx/sites-enabled/
systemctl restart nginx
systemctl enable nginx
kubectl apply --kubeconfig admin.kubeconfig -f kubelet_cluster_role.yml
kubectl apply --kubeconfig admin.kubeconfig -f kubelet_cluster_role_bind.yml
