kubeadm init --pod-network-cidr=10.244.0.0/16
cp /etc/kubernetes/admin.conf /root/
chown root:root /root/admin.conf
export KUBECONFIG=/root/admin.conf
echo "export KUBECONFIG=/root/admin.conf" >>/root/.bashrc
kubectl taint nodes --all node-role.kubernetes.io/master-
kubectl create -f /root/kube-flannel-rbac.yml
kubectl apply -f /root/kube-flannel.yml
export TOKEN=`kubeadm token list  | tail -1 | cut -f1 -d' '`
export CMD="kubeadm join --token $TOKEN kumaster:6443"
echo $CMD > /root/join.sh
sleep 60
ssh-keyscan -H kunode01 >> ~/.ssh/known_hosts
ssh-keyscan -H kunode02 >> ~/.ssh/known_hosts
ssh root@kunode01 $CMD
ssh root@kunode02 $CMD
