CIDR="10.244.0.0/16"
{% if masters > 1 %}
kubeadm init --control-plane-endpoint "{{ api_ip }}:6443" --pod-network-cidr $CIDR --upload-certs
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
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml | sed -e "s/# - name: CALICO_IPV4POOL_CIDR/- name: CALICO_IPV4POOL_CIDR/" -e "s@#   value: \"192.168.0.0/16\"@  value: \"$CIDR\"@"
{% elif sdn == 'canal' %}
kubectl apply -f https://docs.projectcalico.org/v3.1/getting-started/kubernetes/installation/hosted/canal/rbac.yaml
kubectl apply -f https://docs.projectcalico.org/v3.1/getting-started/kubernetes/installation/hosted/canal/canal.yaml
{% elif sdn == 'romana' %}
kubectl apply -f https://raw.githubusercontent.com/romana/romana/master/containerize/specs/romana-kubeadm.yml
{% endif %} 
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config
IP=`hostname -I | cut -f1 -d" "`
TOKEN=`kubeadm token create --ttl 0`
HASH=`openssl x509 -in /etc/kubernetes/pki/ca.crt -noout -pubkey | openssl rsa -pubin -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1`
CMD="kubeadm join $IP:6443 --token $TOKEN --discovery-token-ca-cert-hash sha256:$HASH"

sleep 60

{% if masters > 1 %}
LOGFILE="{{ '/var/log/cloud-init-output.log' if ubuntu else '/var/log/messages' }}"
CERTKEY=$(grep certificate-key $LOGFILE | head -1 | sed 's/.*certificate-key \(.*\)/\1/')
MASTERCMD="$CMD --control-plane --certificate-key $CERTKEY"
echo $MASTERCMD > /root/mastercmd.sh
{% endif %}

echo ${CMD} > /root/join.sh

{%- if metallb %}
bash /root/metal_lb.sh
{%- endif %}

{%- if ingress %}
{% if ingress_method == 'nginx' %}
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/{{ 'cloud' if metallb else 'baremetal' }}/deploy.yaml
{%- endif %}
{%- endif %}
