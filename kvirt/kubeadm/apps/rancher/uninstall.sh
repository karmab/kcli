NAMESPACE="cattle-system"
export PATH=$PWD:$PATH
which helm >/dev/null 2>&1 || kcli download helm
helm uninstall rancher -n $NAMESPACE
kubectl delete namespace $NAMESPACE
