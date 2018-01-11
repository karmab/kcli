oc new-project openfaas-fn
oc new-project openfaas
oc create sa faas-controller
oc policy add-role-to-user admin system:serviceaccount:openfaas:faas-controller --namespace=openfaas-fn
oc adm policy add-scc-to-user anyuid -z default -n openfaas-fn
git clone https://github.com/mhausenblas/faas-netes.git
cd faas-netes
git checkout openshift
cd yaml
oc apply --config=/root/.kube/config -f alertmanager_config.yml,alertmanager.yml,faasnetesd.yml,gateway.yml,nats.yml,prometheus_config.yml,prometheus.yml,queueworker.yml
oc expose --config=/root/.kube/config service/gateway
oc expose --config=/root/.kube/config service/faas-netesd
source /etc/profile.d/openfaas.sh
curl -sSL https://cli.openfaas.com | sh
export PATH="$PATH:/usr/local/bin"
echo export PATH="$PATH:/usr/local/bin" >> /root/.bashrc
sh /root/test.sh
