export METALLB_VERSION={{ 'metallb/metallb' | github_version(metallb_version) }}
kubectl delete -f cr.yml
kubectl delete -f https://raw.githubusercontent.com/metallb/metallb/${METALLB_VERSION}/config/manifests/metallb-native.yaml
