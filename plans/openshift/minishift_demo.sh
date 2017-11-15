export MINISHIFT_VERSION="1.8.0"
export DOCKER_MACHINE_VERSION="0.13.0"
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
#ssh-keyscan -H $REMOTE_HOST >> ~/.ssh/known_hosts
#export KVM_CONNECTION_URL=qemu+ssh://root@$REMOTE_HOST/system
#echo export KVM_CONNECTION_URL=qemu+ssh://root@$REMOTE_HOST/system >>/root/.bashrc
#export HOME=/root
#cd /root
#minishift config set warn-check-kvm-driver true
#minishift start --memory 6144 --disk-size 20000
##docker-machine create -d kvm --kvm-connection-url qemu+ssh://root@192.168.122.1/system minishify-docker
