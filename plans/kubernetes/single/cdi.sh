CDI="{{ cdi_version }}"
CDINAMESPACE="golden"
if [ "CDI" == 'latest' ] ; then
  CDI=`curl -s https://api.github.com/repos/kubevirt/containerized-data-importer/releases/latest| jq -r .tag_name`
fi
kubectl create ns $CDINAMESPACE
kubectl create clusterrolebinding cdi --clusterrole=edit --user=system:serviceaccount:$CDINAMESPACE:default
kubectl create clusterrolebinding cdi-apiserver --clusterrole=cluster-admin --user=system:serviceaccount:$CDINAMESPACE:cdi-apiserver
wget https://github.com/kubevirt/containerized-data-importer/releases/download/${CDI}/cdi-controller.yaml
sed -i "s/kube-system/$CDINAMESPACE/" cdi-controller.yaml
kubectl apply -f cdi-controller.yaml -n $CDINAMESPACE
kubectl expose svc cdi-uploadproxy -n $CDINAMESPACE
