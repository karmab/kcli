export CERTMANAGER_VERSION={{ 'jetstack/cert-manager' | github_version(certmanager_version) }}                                     
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/$CERTMANAGER_VERSION/cert-manager.yaml
kubectl wait -n cert-manager $(kubectl get pod -n cert-manager -l app.kubernetes.io/name=cert-manager -o name) --for=condition=Ready
