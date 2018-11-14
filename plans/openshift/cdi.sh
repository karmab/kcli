wget -P /root/ https://github.com/kubevirt/containerized-data-importer/releases/download/[[ cdi_version ]]/cdi-controller.yaml
wget -P /root https://github.com/kubevirt/containerized-data-importer/releases/download/[[ cdi_version ]]/golden-pvc.yaml
wget -P /root https://github.com/kubevirt/containerized-data-importer/releases/download/[[ cdi_version ]]/endpoint-secret.yaml
oc new-project golden
sed -i "s/namespace:.*/namespace: golden/" cdi-controller.yaml
oc adm policy add-scc-to-user privileged system:serviceaccount:golden:default
oc adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:golden:cdi-apiserver
oc create -f /root/cdi-controller.yaml
