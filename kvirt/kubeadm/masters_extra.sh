ready=false
while [ "$ready" != "true" ] ; do
scp -o StrictHostKeyChecking=no root@{{ api_ip }}:/root/mastercmd.sh /root 2>/dev/null && ready=true
sleep 5
done
scp -o StrictHostKeyChecking=no root@{{ api_ip }}:/etc/kubernetes/admin.conf /etc/kubernetes
bash /root/mastercmd.sh >> /root/$(hostname).log 2>&1
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config
