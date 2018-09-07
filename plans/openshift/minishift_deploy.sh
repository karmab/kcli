minishift start --vm-driver=kvm --iso-url centos
eval $(minishift oc-env)
#oc login -u system:admin
oc adm policy add-cluster-role-to-user cluster-admin admin
oc adm policy add-cluster-role-to-user cluster-admin developer
