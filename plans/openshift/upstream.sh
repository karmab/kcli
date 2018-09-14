setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
sed -i 's@OPTIONS=.*@OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"@' /etc/sysconfig/docker
systemctl start docker --ignore-dependencies
[% if 'Fedora' in template %]
sleep 120
[% endif %]
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
[% if openshift_version == '3.9' %]
oc cluster up --public-hostname $IP.xip.io --routing-suffix $IP.xip.io
[% elif asb %]
oc cluster up --public-hostname $IP.xip.io --routing-suffix $IP.xip.io --enable=service-catalog,router,registry,web-console,persistent-volumes,rhel-imagestreams,automation-service-broker
[% else %]
oc cluster up --public-hostname $IP.xip.io --routing-suffix $IP.xip.io --enable=router,registry,web-console,persistent-volumes,rhel-imagestreams
[% endif %]
oc login -u system:admin
docker update --restart=always origin
oc adm policy add-cluster-role-to-user cluster-admin developer
