NAMESPACE="cattle-system"
export PATH=$PWD:$PATH
which helm || kcli download helm
helm uninstall rancher -n $NAMESPACE
kubectl delete namespace $NAMESPACE
