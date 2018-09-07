export MINISHIFT_VERSION="[[ minishift_version ]]"
export OPENSHIFT_VERSION="v[[ openshift_version ]]"
[% if driver == 'generic' %]
yum -y install docker
systemctl enable docker
systemctl start docker
[% else %]
curl -L https://github.com/dhiltgen/docker-machine-kvm/releases/download/v0.7.0/docker-machine-driver-kvm -o /usr/local/bin/docker-machine-driver-kvm
chmod +x /usr/local/bin/docker-machine-driver-kvm
yum -y install libvirt qemu
systemctl enable libvirtd
systemctl start libvirtd
[% endif %]
curl -L https://github.com/minishift/minishift/releases/download/v$MINISHIFT_VERSION/minishift-$MINISHIFT_VERSION-linux-amd64.tgz > /root/minishift-$MINISHIFT_VERSION-linux-amd64.tgz
tar zxvf /root/minishift-$MINISHIFT_VERSION-linux-amd64.tgz
mv minishift-$MINISHIFT_VERSION-linux-amd64/minishift /usr/bin/
chmod u+x /usr/bin/minishift
minishift start --vm-driver=[[ driver ]] --iso-url centos
#eval $(minishift oc-env)
#oc login -u system:admin
#oc adm policy add-cluster-role-to-user cluster-admin admin
#oc adm policy add-cluster-role-to-user cluster-admin developer
