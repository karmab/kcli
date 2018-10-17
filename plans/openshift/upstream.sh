setenforce 0
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
sed -i 's@OPTIONS=.*@OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"@' /etc/sysconfig/docker
systemctl start docker --ignore-dependencies
[% if 'Fedora' in template %]
sleep 120
[% endif %]
export HOME=/root
[% if type == 'aws' or type == 'gcp' %]
export DNS=[[ name ]].[[ domain ]]
[% else %]
export DNS=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`.xip.io
[% endif %]
[% if openshift_version == '3.9' %]
oc cluster up --public-hostname ${DNS} --routing-suffix ${DNS}
[% elif asb %]
oc cluster up --public-hostname ${DNS} --routing-suffix ${DNS} --enable=service-catalog,router,registry,web-console,persistent-volumes,rhel-imagestreams,automation-service-broker --write-config=true
[% else %]
oc cluster up --public-hostname ${DNS} --routing-suffix ${DNS} --enable=router,registry,web-console,persistent-volumes,rhel-imagestreams
[% endif %]
oc login -u system:admin
oc adm policy add-cluster-role-to-user cluster-admin [[ admin_user ]]
docker update --restart=always origin
