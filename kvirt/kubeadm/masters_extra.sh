ready=false
while [ "$ready" != "true" ] ; do
 curl -Lk http://{{ api_ip }}/mastercmd.sh > /var/www/html/mastercmd.sh 
 grep -q kubeadm /var/www/html/mastercmd.sh
 if [ "$?" = "0" ] ; then ready=true ; fi
  sleep 10
done
curl -Lk http://{{ api_ip }}/admin.conf > /var/www/html/admin.conf
cp /var/www/html/admin.conf /etc/kubernetes/admin.conf 
bash /var/www/html/mastercmd.sh | tee /root/$(hostname).log 2>&1
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config
