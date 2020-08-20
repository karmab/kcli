export PATH=.:$PATH
oc adm policy add-scc-to-group anyuid system:serviceaccounts:istio-system
curl -L https://istio.io/downloadIstio | sh -
mv istio-*/bin/istioctl .
istioctl install -f istio-cni.yaml
oc -n istio-system expose svc/istio-ingressgateway --port=http2
