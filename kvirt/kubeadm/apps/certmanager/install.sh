export CERTMANAGER_VERSION={{ 'jetstack/cert-manager' | githubversion(certmanager_version) }}                                     
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/$CERTMANAGER_VERSION/cert-manager.yaml
