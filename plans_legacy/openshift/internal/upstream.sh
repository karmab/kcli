sed -i '/OPTIONS=.*/c\OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"' /etc/sysconfig/docker
sed -i 's/registry.fedoraproject.org/registry.ops.openshift.com/g' /etc/containers/registries.conf
systemctl start docker --ignore-dependencies
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
sleep 20
rm -rf /usr/share/rhel/secrets
#oc cluster up --public-hostname $IP.xip.io --routing-suffix $IP.xip.io --image=registry.ops.openshift.com/openshift3/ose --version='v3.7.0'
oc cluster up --public-hostname $IP.xip.io --routing-suffix $IP.xip.io --image=registry.reg-aws.openshift.com/openshift3/ose --version='latest'
docker exec origin oadm policy add-cluster-role-to-user cluster-admin admin --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
docker exec origin oadm policy add-cluster-role-to-user cluster-admin developer --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
