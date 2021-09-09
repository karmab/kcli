# set global variable
CIDR="10.244.0.0/16"

# initialize cluster
kubeadm init --control-plane-endpoint "{{ api_ip }}:6443" --pod-network-cidr $CIDR --upload-certs {{ '--image-repository public.ecr.aws/eks-distro/kubernetes --kubernetes-version $EKSD_API_VERSION' if eksd else '' }}

# config cluster credentials
cp /etc/kubernetes/admin.conf /root/
chown root:root /root/admin.conf
export KUBECONFIG=/root/admin.conf
echo "export KUBECONFIG=/root/admin.conf" >> /root/.bashrc

# taint master node(s)
kubectl taint nodes --all node-role.kubernetes.io/master-

{% if sdn != None %}
# install Container Network Interface (CNI)
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
{% elif sdn == 'opencontrail' %}
K8S_MASTER_IP={{ api_ip }}
CONTRAIL_REPO="docker.io\/opencontrailnightly"
CONTRAIL_RELEASE="latest"
mkdir -pm 777 /var/lib/contrail/kafka-logs
TARGET_OS={{ 'ubuntu' if ubuntu else 'centos' }}
curl https://raw.githubusercontent.com/Juniper/contrail-kubernetes-docs/master/install/kubernetes/templates/contrail-single-step-cni-install-$TARGET_OS.yaml | sed "s/{% raw %}{{ K8S_MASTER_IP }}{% endraw %}/$K8S_MASTER_IP/g; s/{% raw %}{{ CONTRAIL_REPO }}{% endraw %}/$CONTRAIL_REPO/g; s/{% raw %}{{ CONTRAIL_RELEASE }}{% endraw %}/$CONTRAIL_RELEASE/g" | kubectl apply -f -
{% elif sdn == 'cilium' %}
curl -LO https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm -f cilium-linux-amd64.tar.gz
cilium install
{% endif %}
{% endif %}

# config cluster credentials
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config

# join worker(s) to cluster
#IP=`hostname -I | cut -f1 -d" "`
IP={{ api_ip }}
TOKEN=`kubeadm token create --ttl 0`
HASH=`openssl x509 -in /etc/kubernetes/pki/ca.crt -noout -pubkey | openssl rsa -pubin -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1`
CMD="kubeadm join $IP:6443 --token $TOKEN --discovery-token-ca-cert-hash sha256:$HASH"

sleep 60

LOGFILE="{{ '/var/log/cloud-init-output.log' if ubuntu else '/var/log/messages' }}"
CERTKEY=$(grep certificate-key $LOGFILE | head -1 | sed 's/.*certificate-key \(.*\)/\1/')
MASTERCMD="$CMD --control-plane --certificate-key $CERTKEY"
cp /root/admin.conf /var/www/html
echo $MASTERCMD > /var/www/html/mastercmd.sh
chmod o+r /var/www/html/*

echo ${CMD} > /root/join.sh

{% if metallb %}
# (addon) install Metal Load Balancer (LB)
bash /root/metal_lb.sh
{% endif %}

{% if ingress %}
# (addon) install Ingress Controller
{% if ingress_method == 'nginx' %}
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/{{ 'cloud' if metallb else 'baremetal' }}/deploy.yaml
{% endif %}
{% endif %}

{% if policy_as_code %}
# (addon) install Policy-as-Code (PaC) Controller
{% if policy_as_code_method == 'gatekeeper' %}
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
{% elif policy_as_code_method == 'kyverno' %}
kubectl apply -f https://raw.githubusercontent.com/kyverno/kyverno/main/definitions/release/install.yaml
{% endif %}
{% endif %}

{% if autolabel %}
# (addon) install Autolabeler
kubectl apply -f https://raw.githubusercontent.com/karmab/autolabeller/master/autorules.yml
{% endif %}

{% if registry %}
# (addon) install Registry
mkdir -p /opt/registry/{auth,certs,data,conf}
REGISTRY_NAME="api.{{ cluster }}.{{ domain }}"
REGISTRY_USER={{ registry_user }}
REGISTRY_PASSWORD={{ registry_password }}
openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 365 -out /opt/registry/certs/domain.crt -subj "/C=US/ST=Madrid/L=San Bernardo/O=Karmalabs/OU=Guitar/CN=$REGISTRY_NAME" -addext "subjectAltName=DNS:$REGISTRY_NAME"
cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust extract
htpasswd -bBc /opt/registry/auth/htpasswd $REGISTRY_USER $REGISTRY_PASSWORD
kubectl apply -f /root/registry.yml
cp /opt/registry/certs/domain.{key,crt} /var/www/html
cp /opt/registry/auth/htpasswd /var/www/html
{% endif %}

{% if multus %}
multus.sh
{% endif %}
{% if nfs %}
nfs.sh
{% endif %}
