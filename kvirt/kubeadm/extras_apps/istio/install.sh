export PATH=.:$PATH
curl -L https://istio.io/downloadIstio | sh -
mv istio-*/bin/istioctl .
istioctl install
