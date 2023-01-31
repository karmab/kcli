export PATH=$PWD:$PATH
which helm >/dev/null 2>&1 || kcli download helm
helm uninstall falco -n falco
kubectl delete namespace falco
