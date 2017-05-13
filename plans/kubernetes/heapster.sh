yum -y install git
git clone https://github.com/kubernetes/heapster.git /root/heapster
kubectl create -f /root/heapster/deploy/kube-config/influxdb/
