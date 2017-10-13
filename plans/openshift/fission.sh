oc new-project fission
export TILLER_NAMESPACE=helm
oc adm policy add-cluster-role-to-user cluster-admin -z fission-svc
helm install --namespace fission https://github.com/fission/fission/releases/download/0.3.0/fission-core-0.3.0.tgz
curl -Lo fission https://github.com/fission/fission/releases/download/0.3.0/fission-cli-linux && chmod +x fission && mv fission /usr/bin/
oc expose svc controller
oc expose svc router
