kubectl create ns multus
kubectl apply -f /root/multus.yml
kubectl apply -f /root/cni-plugins.yml
kubectl apply -f /root/l2-bridge.yml
