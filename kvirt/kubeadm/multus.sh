kubectl create ns multus
kubectl apply -f /root/multus.yml
kubectl apply -f /root/cni-plugins.yml
kubectl apply -f /root/l2-bridge.yml
iptables -I FORWARD 1 -s 10.10.0.0/16 -j ACCEPT
