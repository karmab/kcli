yum -y install atomic-openshift-clients docker atomic-openshift
sed -i '/OPTIONS=.*/c\OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"' /etc/sysconfig/docker
systemctl enable docker
systemctl enable rhel-push-plugin
systemctl start rhel-push-plugin
systemctl start docker --ignore-dependencies
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
{% if metrics %}
oc cluster up --public-hostname ${IP}.xip.io --routing-suffix ${IP}.xip.io --image=registry.access.redhat.com/openshift3/ose --metrics
{% else %}
oc cluster up --public-hostname ${IP}.xip.io --routing-suffix ${IP}.xip.io --image=registry.access.redhat.com/openshift3/ose --enable=router,registry,web-console,persistent-volumes,rhel-imagestreams
{% endif %}
oc adm policy add-cluster-role-to-user cluster-admin admin --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
oc adm policy add-cluster-role-to-user cluster-admin developer --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
