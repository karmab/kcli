source /etc/profile.d/openfaas.sh
docker login -u developer -p `oc whoami -t --config=/root/.kube/config` 172.30.1.1:5000
cd /root/faas-netes/yaml
faas-cli new hellojs --lang node -g ${OPENFAAS_URL}
cp /root/hello.js hellojs/handler.js
sed -i "s@    image:.*@    image: 172.30.1.1:5000/openfaas-fn/hellojs@" hellojs.yml
faas-cli build -f hellojs.yml
docker login -u developer -p `oc whoami -t --config=/root/.kube/config` 172.30.1.1:5000
faas-cli push -f hellojs.yml
faas-cli deploy -f hellojs.yml
faas-cli new hellopy --lang python -g ${OPENFAAS_URL}
sed -i "s@    image:.*@    image: 172.30.1.1:5000/openfaas-fn/hellopy@" hellopy.yml
cp /root/hello.py hellopy/handler.py
faas-cli build -f hellopy.yml
docker login -u developer -p `oc whoami -t --config=/root/.kube/config` 172.30.1.1:5000
faas-cli push -f hellopy.yml
faas-cli deploy -f hellopy.yml
#faas-cli invoke -f hellopy.yml hellopy -g $OPENFAAS_URL
#curl $OPENFAAS_URL/function/hellopy
