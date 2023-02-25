{% if falco_lb_ip != None %}
kubectl create -f falco_ip.yml
kubectl create -f falco_advertisements.yml
{% endif %}

export PATH=$PWD:$PATH
which helm >/dev/null 2>&1 || kcli download helm
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco --namespace falco --create-namespace --set falcosidekick.enabled=true --set falcosidekick.webui.enabled=true
kubectl wait -n falco $(kubectl get pod -n falco -l app.kubernetes.io/name=falco -o name) --for=condition=Ready

{% if falco_lb_ip != None %}
kubectl annotate svc falco-falcosidekick-ui -n falco metallb.universe.tf/address-pool='falco-ip'
kubectl patch svc falco-falcosidekick-ui -n falco -p '{"spec":{"type":"LoadBalancer"}}'
IP=$(echo {{ falco_lb_ip }} | sed 's/./-/g')
echo Access the deployment using falco-$IP.sslip.io
{% endif %}
