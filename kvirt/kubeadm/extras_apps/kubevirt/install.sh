export KUBEVIRT_VERSION={{ 'kubevirt/kubevirt' | latestversion }}
echo "Deploying Kubevirt $KUBEVIRT_VERSION"
kubectl create -f https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-operator.yaml
kubectl create -f https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-cr.yaml
