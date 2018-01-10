git clone https://github.com/mhausenblas/faas-netes.git
cd faas-netes
git checkout openshift
oc new-project openfaas-fn
oc new-project openfaas
oc create sa faas-controller
oc policy add-role-to-user admin system:serviceaccount:openfaas:faas-controller --namespace=openfaas-fn
oc adm policy add-scc-to-user anyuid -z default -n openfaas-fn
cd yaml/
oc apply -f alertmanager_config.yml,alertmanager.yml,faasnetesd.yml,gateway.yml,nats.yml,prometheus_config.yml,prometheus.yml,queueworker.yml
oc expose service/gateway
export OPENFAAS_URL=http://$(oc get route faas-netesd -o=jsonpath='{.spec.host}' --namespace=openfaas)
curl -sSL https://cli.openfaas.com | sh
export PATH="$PATH:/usr/local/bin"
echo export PATH="$PATH:/usr/local/bin" >> /root/.bashrc
unalias cp
faas-cli new hellojs --lang node -g $OPENFAAS_URL
cp hello.js hellojs/handler.js
sed -i "s@    image:.*@    image: 172.30.1.1:5000/openfaas-fn/hellojs@" hellojs.yml
faas-cli build -f hellojs.yml
faas-cli push -f hellojs.yml 
faas-cli deploy -f hellojs.yml
#docker login -u developer -p `oc whoami -t` 172.30.1.1:5000
#docker tag 172.30.1.1:5000/openfaas-fn/hellojs latest
#docker push 172.30.1.1:5000/openfaas-fn/hellojs
faas-cli new hellopy --lang python -g $OPENFAAS_URL
sed -i "s@    image:.*@    image: 172.30.1.1:5000/openfaas-fn/hellopy@" hellopy.yml
cp hello.py hellopy/handler.py
faas-cli build -f hellopy.yml
faas-cli push -f hellopy.yml 
faas-cli deploy -f hellopy.yml
#docker tag 172.30.1.1:5000/openfaas/hellopy latest
#docker push 172.30.1.1:5000/openfaas/hellopy
#faas-cli invoke -f hellopy.yml hellopy -g $OPENFAAS_URL
#curl $OPENFAAS_URL/function/frout
