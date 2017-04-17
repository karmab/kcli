systemctl start docker --ignore-dependencies
oc cluster up
oadm policy add-cluster-role-to-user cluster-admin admin --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
