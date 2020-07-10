kubectl get configmap kube-proxy -n kube-system -o yaml | sed -e "s/strictARP: false/strictARP: true/" | kubectl apply -f - -n kube-system
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/{{ metallb_version }}/manifests/namespace.yaml
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/{{ metallb_version }}/manifests/metallb.yaml
kubectl create secret generic -n metallb-system memberlist --from-literal=secretkey="$(openssl rand -base64 128)"
kubectl create -f /root/metal_lb_cm.yml
