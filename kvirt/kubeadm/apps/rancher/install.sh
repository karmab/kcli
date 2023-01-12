{% if rancher_hostname == None %}
echo rancher_hostname needs to be set && exit 1
{% endif %}
HOSTNAME={{ rancher_hostname }}
RANCHER_VERSION="{{ rancher_version }}"
RANCHER_PASSWORD="{{ rancher_password }}"
RANCHER_OPTS={{ "--devel" if rancher_version == 'alpha' else "" }}
NAMESPACE="cattle-system"
export PATH=$PWD:$PATH
which helm >/dev/null 2>&1 || kcli download helm
helm repo add rancher-$RANCHER_VERSION https://releases.rancher.com/server-charts/$RANCHER_VERSION
kubectl create namespace $NAMESPACE
helm install rancher rancher-$RANCHER_VERSION/rancher --namespace $NAMESPACE --set hostname=$HOSTNAME --set bootstrapPassword=$RANCHER_PASSWORD --set ingress.tls.source=rancher --set ingress.extraAnnotations.'kubernetes\.io/ingress\.class'=nginx $RANCHER_OPTS
