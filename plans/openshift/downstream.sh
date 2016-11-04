systemctl enable rhel-push-plugin
systemctl start rhel-push-plugin
yum -y install atomic-openshift-clients
systemctl start docker --ignore-dependencies
oc cluster up --image=registry.access.redhat.com/openshift3/ose
