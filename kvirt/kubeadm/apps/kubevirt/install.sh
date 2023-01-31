export KUBEVIRT_VERSION={{ 'kubevirt/kubevirt' | github_version(kubevirt_version) }}
kubectl create -f https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-operator.yaml
kubectl create -f https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-cr.yaml
{% if cdi %}
export CDI_VERSION={{ 'kubevirt/containerized-data-importer' | github_version(cdi_version) }}
kubectl create -f https://github.com/kubevirt/containerized-data-importer/releases/download/$CDI_VERSION/cdi-operator.yaml
kubectl create -f https://github.com/kubevirt/containerized-data-importer/releases/download/$CDI_VERSION/cdi-cr.yaml
{% endif %}
