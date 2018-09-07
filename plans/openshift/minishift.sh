export MINISHIFT_VERSION="[[ minishift_version ]]"
export OPENSHIFT_VERSION="v[[ openshift_version ]]"
curl -L https://github.com/minishift/minishift/releases/download/v$MINISHIFT_VERSION/minishift-$MINISHIFT_VERSION-linux-amd64.tgz > /root/minishift-$MINISHIFT_VERSION-linux-amd64.tgz
tar zxvf /root/minishift-$MINISHIFT_VERSION-linux-amd64.tgz
mv minishift-$MINISHIFT_VERSION-linux-amd64/minishift /usr/bin/
chmod u+x /usr/bin/minishift
minishift start --vm-driver=none --iso-url centos
#eval $(minishift oc-env)
#oc login -u system:admin
#oc adm policy add-cluster-role-to-user cluster-admin admin
#oc adm policy add-cluster-role-to-user cluster-admin developer
