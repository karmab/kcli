kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/master/deployments/multus-daemonset-thick.yml
# iptables -I FORWARD 1 -s 10.10.0.0/16 -j ACCEPT
