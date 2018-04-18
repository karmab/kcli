sed -i '/OPTIONS=.*/c\OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"' /etc/sysconfig/docker
systemctl start docker --ignore-dependencies
[% if 'Fedora' in template %]
sleep 120
[% endif %]
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
oc cluster up --public-hostname $IP.xip.io --routing-suffix $IP.xip.io
oc login -u system:admin
[% if initializer %]
grep -q Initializers /var/lib/origin/openshift.local.config/master/master-config.yaml || sed  -i "/GenericAdmissionWebhook/i\ \ \ \ `cat /root/initializer.txt`" /var/lib/origin/openshift.local.config/master/master-config.yaml
docker restart origin
[% endif %]
docker update --restart=always origin
oc adm policy add-cluster-role-to-user cluster-admin developer
