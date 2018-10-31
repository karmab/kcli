
apt-get -y install bind9utils wget
wget -q --https-only --timestamping https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64
chmod +x cfssl_linux-amd64 cfssljson_linux-amd64
mv cfssl_linux-amd64 /usr/local/bin/cfssl
mv cfssljson_linux-amd64 /usr/local/bin/cfssljson
wget https://storage.googleapis.com/kubernetes-release/release/[[ kubernetes_version ]]/bin/linux/amd64/kubectl
chmod +x kubectl
mv kubectl /usr/local/bin
KUBERNETES_PUBLIC_ADDRESS=$(dig +short kubernetes-the-hard-way.[[ domain ]])
cfssl gencert -initca ca-csr.json | cfssljson -bare ca
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes admin-csr.json | cfssljson -bare admin
for instance in worker-0 worker-1 worker-2; do
 sed "s/instance/$instance/" instance-csr.json > ${instance}-csr.json
 EXTERNAL_IP=$(dig + short ${instance}.[[ domain ]])
 INTERNAL_IP=$( dig +short ${instance})
 cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -hostname=${instance},${EXTERNAL_IP},${INTERNAL_IP} -profile=kubernetes ${instance}-csr.json | cfssljson -bare ${instance}
done
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes kube-controller-manager-csr.json | cfssljson -bare kube-controller-manager
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes kube-proxy-csr.json | cfssljson -bare kube-proxy
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes kube-scheduler-csr.json | cfssljson -bare kube-scheduler
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -hostname=10.32.0.1,10.240.0.10,10.240.0.11,10.240.0.12,${KUBERNETES_PUBLIC_ADDRESS},127.0.0.1,kubernetes.default -profile=kubernetes kubernetes-csr.json | cfssljson -bare kubernetes
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes service-account-csr.json | cfssljson -bare service-account
for instance in worker-0 worker-1 worker-2; do
  ssh-keyscan -H ${instance} >> ~/.ssh/known_hosts
  scp ca.pem ${instance}-key.pem ${instance}.pem ${instance}:
done
for instance in controller-0 controller-1 controller-2; do
  ssh-keyscan -H ${instance} >> ~/.ssh/known_hosts
  scp ca.pem ca-key.pem kubernetes-key.pem kubernetes.pem service-account-key.pem service-account.pem ${instance}:
done
# lab5
for instance in worker-0 worker-1 worker-2; do
  kubectl config set-cluster kubernetes-the-hard-way --certificate-authority=ca.pem --embed-certs=true --server=https://${KUBERNETES_PUBLIC_ADDRESS}:6443 --kubeconfig=${instance}.kubeconfig
  kubectl config set-credentials system:node:${instance} --client-certificate=${instance}.pem --client-key=${instance}-key.pem --embed-certs=true --kubeconfig=${instance}.kubeconfig
  kubectl config set-context default --cluster=kubernetes-the-hard-way --user=system:node:${instance} --kubeconfig=${instance}.kubeconfig
  kubectl config use-context default --kubeconfig=${instance}.kubeconfig
done
kubectl config set-cluster kubernetes-the-hard-way --certificate-authority=ca.pem --embed-certs=true --server=https://${KUBERNETES_PUBLIC_ADDRESS}:6443 --kubeconfig=kube-proxy.kubeconfig
kubectl config set-credentials system:kube-proxy --client-certificate=kube-proxy.pem --client-key=kube-proxy-key.pem --embed-certs=true --kubeconfig=kube-proxy.kubeconfig
kubectl config set-context default --cluster=kubernetes-the-hard-way --user=system:kube-proxy --kubeconfig=kube-proxy.kubeconfig
kubectl config use-context default --kubeconfig=kube-proxy.kubeconfig
kubectl config set-cluster kubernetes-the-hard-way --certificate-authority=ca.pem --embed-certs=true --server=https://127.0.0.1:6443 --kubeconfig=kube-controller-manager.kubeconfig
kubectl config set-credentials system:kube-controller-manager --client-certificate=kube-controller-manager.pem --client-key=kube-controller-manager-key.pem --embed-certs=true --kubeconfig=kube-controller-manager.kubeconfig
kubectl config set-context default --cluster=kubernetes-the-hard-way --user=system:kube-controller-manager --kubeconfig=kube-controller-manager.kubeconfig
kubectl config use-context default --kubeconfig=kube-controller-manager.kubeconfig
kubectl config set-cluster kubernetes-the-hard-way --certificate-authority=ca.pem --embed-certs=true --server=https://127.0.0.1:6443 --kubeconfig=kube-scheduler.kubeconfig
kubectl config set-credentials system:kube-scheduler --client-certificate=kube-scheduler.pem --client-key=kube-scheduler-key.pem --embed-certs=true --kubeconfig=kube-scheduler.kubeconfig
kubectl config set-context default --cluster=kubernetes-the-hard-way --user=system:kube-scheduler --kubeconfig=kube-scheduler.kubeconfig
kubectl config use-context default --kubeconfig=kube-scheduler.kubeconfig
kubectl config set-cluster kubernetes-the-hard-way --certificate-authority=ca.pem --embed-certs=true --server=https://127.0.0.1:6443 --kubeconfig=admin.kubeconfig
kubectl config set-credentials admin --client-certificate=admin.pem --client-key=admin-key.pem --embed-certs=true --kubeconfig=admin.kubeconfig
kubectl config set-context default --cluster=kubernetes-the-hard-way --user=admin --kubeconfig=admin.kubeconfig
kubectl config use-context default --kubeconfig=admin.kubeconfig
for instance in worker-0 worker-1 worker-2; do
  scp ${instance}.kubeconfig kube-proxy.kubeconfig ${instance}:
done
for instance in controller-0 controller-1 controller-2; do
  scp admin.kubeconfig kube-controller-manager.kubeconfig kube-scheduler.kubeconfig ${instance}:
done
#lab6
ENCRYPTION_KEY=$(head -c 32 /dev/urandom | base64)
sed "s/ENCRYPTION_KEY/$ENCRYPTION_KEY/" encryption-config.yaml
for instance in controller-0 controller-1 controller-2; do
  scp encryption-config.yaml ${instance}:
done
#lab7
wget -q --show-progress --https-only --timestamping "https://github.com/coreos/etcd/releases/download/v3.3.9/etcd-v3.3.9-linux-amd64.tar.gz"
tar -xvf etcd-v3.3.9-linux-amd64.tar.gz
mv etcd-v3.3.9-linux-amd64/etcd* /usr/local/bin
mkdir -p /etc/etcd /var/lib/etcd
cp ca.pem kubernetes-key.pem kubernetes.pem /etc/etcd
for instance in controller-0 controller-1 controller-2; do
 INTERNAL_IP=$( dig +short ${instance})
 ETCD_NAME=${instance}
 sed "s/INTERNAL_IP/$INTERNAL_IP/" etcd.service> etcd.service_X
 sed "s/ETCD_NAME/$ETCD_NAME/" etcd.service_X > etcd.service_$instance
 scp etcd.service_$instance $instance:/etc/systemd/system/
 systemctl daemon-reload
 systemctl enable etcd
 systemctl start etcd
done
