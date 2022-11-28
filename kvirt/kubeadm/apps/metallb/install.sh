kubectl get configmap kube-proxy -n kube-system -o yaml | sed -e "s/strictARP: false/strictARP: true/" | kubectl apply -f - -n kube-system
export METALLB_VERSION={{ 'metallb/metallb' | github_version(metallb_version|default("latest")) }}
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/${METALLB_VERSION}/config/manifests/metallb-native.yaml
while [ "$(kubectl get ipaddresspool -n metallb-system -o name)" == "" ] ;  do sleep 5 ; kubectl create -f metallb_cr.yml ; done
kubectl create -f metallb_advertisements.yml
