systemctl start docker --ignore-dependencies
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
oc cluster up --public-hostname $IP.xip.io
docker exec -it origin oadm policy add-cluster-role-to-user cluster-admin admin --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
