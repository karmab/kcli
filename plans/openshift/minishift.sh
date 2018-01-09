export MINISHIFT_VERSION="[[ minishift_version ]]"
export OPENSHIFT_VERSION="v[[ openshift_version ]]"
export REMOTE_HOST="192.168.122.1"
yum -y install libvirt-libs
echo 'export PATH=/usr/local/bin:$PATH' >> /root/.bashrc
export PATH=/usr/local/bin:$PATH
curl -L https://github.com/minishift/minishift/releases/download/v$MINISHIFT_VERSION/minishift-$MINISHIFT_VERSION-linux-amd64.tgz > /root/minishift-$MINISHIFT_VERSION-linux-amd64.tgz
tar zxvf /root/minishift-$MINISHIFT_VERSION-linux-amd64.tgz
mv minishift-$MINISHIFT_VERSION-linux-amd64/minishift /usr/bin/
chmod u+x /usr/bin/minishift
curl -L https://github.com/docker/machine/releases/download/v$DOCKER_MACHINE_VERSION/docker-machine-`uname -s`-`uname -m` >  /usr/bin/docker-machine
chmod u+x /usr/bin/docker-machine
curl -L https://github.com/karmab/docker-machine-kvm-patched/raw/master/docker-machine-driver-kvm-centos7 > /usr/bin/docker-machine-driver-kvm
chmod u+x /usr/bin/docker-machine-driver-kvm
ssh-keyscan -H $REMOTE_HOST >> ~/.ssh/known_hosts
export KVM_CONNECTION_URL=qemu+ssh://root@$REMOTE_HOST/system
echo export KVM_CONNECTION_URL=qemu+ssh://root@$REMOTE_HOST/system >>/root/.bashrc
export HOME=/root
cd /root
minishift config set warn-check-kvm-driver true
sh /root/minishift_no_config.sh
minishift start --memory 6144 --disk-size 20000 --openshift-version $OPENSHIFT_VERSION
##docker-machine create -d kvm --kvm-connection-url qemu+ssh://root@192.168.122.1/system minishify-docker
#eval $(minishift oc-env)
#oc login -u system:admin
#oc adm policy add-cluster-role-to-user cluster-admin admin
#oc adm policy add-cluster-role-to-user cluster-admin developer
