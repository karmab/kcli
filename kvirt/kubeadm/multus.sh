kubectl apply -f https://raw.githubusercontent.com/intel/multus-cni/master/images/multus-daemonset.yml
# iptables -I FORWARD 1 -s 10.10.0.0/16 -j ACCEPT
