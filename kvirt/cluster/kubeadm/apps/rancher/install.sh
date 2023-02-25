HOSTNAME=${{ rancher_hostname or ""}}
{% if rancher_lb_ip != None %}
kubectl create -f rancher_ip.yml
kubectl create -f rancher_advertisements.yml
IP=$(echo {{ rancher_lb_ip }} | sed 's/./-/g')
HOSTNAME="${HOSTNAME:-rancher-$IP.sslip.io}"
{% elif rancher_ingress %}
IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' | sed 's/./-/g')
HOSTNAME="${HOSTNAME:-rancher-$IP.sslip.io}"
{% endif %}

if [ "$HOSTNAME" == "" ] ; then
echo Couldnt figure out which hostname to use. Set rancher_ingress or rancher_lb_ip
exit 1
else
echo Using $HOSTNAME as hostname
fi
RANCHER_VERSION="{{ rancher_version }}"
RANCHER_PASSWORD="{{ rancher_password }}"
RANCHER_DEV_OPTS={{ "--devel" if rancher_version == 'alpha' else "" }}
RANCHER_INGRESS_OPTS={{ "--set ingress.tls.source=rancher --set ingress.extraAnnotations.'kubernetes\.io/ingress\.class'=nginx" if rancher_ingress else "--set ingress.enabled false" }}
export PATH=$PWD:$PATH
which helm >/dev/null 2>&1 || kcli download helm
helm repo add rancher-$RANCHER_VERSION https://releases.rancher.com/server-charts/$RANCHER_VERSION
helm install rancher rancher-$RANCHER_VERSION/rancher --namespace cattle-system --create-namespace --set hostname=$HOSTNAME --set bootstrapPassword=$RANCHER_PASSWORD $RANCHER_INGRESS_OPTS $RANCHER_DEV_OPTS
kubectl wait -n cattle-system $(kubectl get pod -n cattle-system -l app=rancher -o name) --for=condition=Ready

{% if rancher_lb_ip != None %}
kubectl annotate svc rancher -n cattle-system metallb.universe.tf/address-pool='rancher-ip'
kubectl patch svc rancher -n cattle-system -p '{"spec":{"type":"LoadBalancer"}}'
{% endif %}
