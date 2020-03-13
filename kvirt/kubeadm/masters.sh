{% if sdn == 'calico' %}
CIDR="192.168.0.0/16"
{% else %} 
CIDR="10.244.0.0/16"
{% endif %} 
{% if masters > 1 %}
kubeadm init --control-plane-endpoint "{{ cluster }}-master.{{ network }}:6443" --pod-network-cidr $CIDR --upload-certs
{% else %}
kubeadm init --pod-network-cidr $CIDR
{% endif %}
cp /etc/kubernetes/admin.conf /root/
chown root:root /root/admin.conf
export KUBECONFIG=/root/admin.conf
echo "export KUBECONFIG=/root/admin.conf" >>/root/.bashrc
kubectl taint nodes --all node-role.kubernetes.io/master-
{% if sdn == 'flannel' %}
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
{% elif sdn == 'weavenet' %}
kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=`kubectl version | base64 | tr -d '\n'`"
{% elif sdn == 'calico' %}
kubectl apply -f https://docs.projectcalico.org/v3.9/manifests/calico.yaml
{% elif sdn == 'canal' %}
kubectl apply -f https://docs.projectcalico.org/v3.1/getting-started/kubernetes/installation/hosted/canal/rbac.yaml
kubectl apply -f https://docs.projectcalico.org/v3.1/getting-started/kubernetes/installation/hosted/canal/canal.yaml
{% elif sdn == 'romana' %}
kubectl apply -f https://raw.githubusercontent.com/romana/romana/master/containerize/specs/romana-kubeadm.yml
{% endif %} 
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config
IP=`ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'`
TOKEN=`kubeadm token create --ttl 0`
HASH=`openssl x509 -in /etc/kubernetes/pki/ca.crt -noout -pubkey | openssl rsa -pubin -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1`
CMD="kubeadm join $IP:6443 --token $TOKEN --discovery-token-ca-cert-hash sha256:$HASH"

sleep 60

{% if masters > 1 %}
{% for number in range(1,masters) %}
CERTKEY=$(grep certificate-key /var/log/messages | head -1 | sed 's/.*certificate-key \(.*\)/\1/')
MASTERCMD="$CMD --control-plane --certificate-key $CERTKEY"
echo $MASTERCMD > /root/mastercmd.sh
ssh-keyscan -H {{ cluster }}-master-0{{ number }} >> ~/.ssh/known_hosts 
scp /etc/kubernetes/admin.conf root@{{ cluster }}-master-{{ number }}:/etc/kubernetes/
echo ssh root@{{ cluster }}-master-0{{ number }} $MASTERCMD > /root/{{ cluster }}-master-{{ number }}.log 2>&1
ssh root@{{ cluster }}-master-0{{ number }} $MASTERCMD >> /root/{{ cluster }}-master-{{ number }}.log 2>&1
scp /etc/kubernetes/admin.conf {{ cluster }}-master-{{ number }}:/root
ssh {{ cluster }}-master-0{{ number }} mkdir -p /root/.kube
ssh {{ cluster }}-master-0{{ number }} cp -i /root/admin.conf /root/.kube/config
ssh {{ cluster }}-master-0{{ number }} chown root:root /root/.kube/config
{% endfor %}
{% endif %}

echo ${CMD} > /root/join.sh
