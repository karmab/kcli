TMPDIR={{ tmpdir}}
NAMESPACE={{ namespace }}-{{ cluster }}
CALICO_VERSION={{ 'projectcalico/calico'|github_version(calico_version) }}
cd $TMPDIR
curl -Lk https://github.com/projectcalico/calico/releases/download/$CALICO_VERSION/ocp.tgz | tar xvz --strip-components=1
sed -i "s/tigera-operator/$NAMESPACE/" 00-namespace-tigera-operator.yaml
sed -i "s/namespace: tigera-operator/namespace: $NAMESPACE/" *yaml
oc create -f .
