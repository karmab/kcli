kubeadm init --pod-network-cidr=10.244.0.0/16
cp /etc/kubernetes/admin.conf /root/
chown root:root /root/admin.conf
export KUBECONFIG=/root/admin.conf
echo "export KUBECONFIG=/root/admin.conf" >>/root/.bashrc
kubectl taint nodes --all node-role.kubernetes.io/master-
kubectl create -f /root/kube-flannel-rbac.yml
kubectl apply -f /root/kube-flannel.yml
#export TOKEN=`kubeadm token list  | tail -1 | cut -f1 -d' '`
#export CMD="kubeadm join --token $TOKEN kumaster:6443"
export CMD=`kubeadm token create --print-join-command`
echo $CMD > /root/join.sh
sleep 160
[% if nodes > 0 %]
[% for number in range(0,nodes) %]
ssh-keyscan -H kunode0[[ number +1 ]] >> ~/.ssh/known_hosts
scp /etc/kubernetes/admin.conf root@kunode0[[ number + 1 ]]:/etc/kubernetes/
ssh root@kunode0[[ number +1 ]] $CMD > kunode0[[ number +1 ]].log
[% endfor %]
[% endif %]
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config
[% if skydive %]
kubectl create ns skydive
kubectl create -n skydive -f https://raw.githubusercontent.com/skydive-project/skydive/master/contrib/kubernetes/skydive.yaml
[% endif %]
