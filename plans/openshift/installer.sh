echo 192.168.126.11 [[ cluster ]]-api.[[ domain ]] >> /etc/hosts
yum -y install libvirt-client libvirt-devel gcc-c++ git unzip wget jq
curl -OL https://github.com/openshift/origin/releases/download/v3.11.0/openshift-origin-client-tools-v3.11.0-0cbc58b-linux-64bit.tar.gz
tar -zxf openshift-origin-client-tools-v3.11.0-0cbc58b-linux-64bit.tar.gz
mv $HOME/openshift-origin-client-tools-v3.11.0-0cbc58b-linux-64bit/oc /usr/local/bin
ssh-keyscan -H 192.168.122.1 >> ~/.ssh/known_hosts
build=`curl -s https://releases-rhcos.svc.ci.openshift.org/storage/releases/maipo/builds.json | jq -r '.builds[0]'`
image=`curl -s https://releases-rhcos.svc.ci.openshift.org/storage/releases/maipo/$build/meta.json | jq -r '.images["qemu"].path'`
url="https://releases-rhcos.svc.ci.openshift.org/storage/releases/maipo/$build/$image"
curl --compressed -L -o /root/rhcos-qemu.qcow2 $url
wget https://dl.google.com/go/go[[ go_version ]].linux-amd64.tar.gz
tar -C /usr/local -xzf go[[ go_version ]].linux-amd64.tar.gz
export GOPATH=/root/go
export PATH=$PATH:/usr/local/go/bin:${GOPATH}/bin:${GOPATH}/src/github/openshift/installer/bin
export KUBECONFIG=$HOME/clusters/nested/auth/kubeconfig
echo export GOPATH=/root/go >> ~/.bashrc
echo export PATH=\$PATH:/usr/local/go/bin:\$GOPATH/bin:\$GOPATH/src/github/openshift/installer/bin >> ~/.bashrc
echo export KUBECONFIG=\$GOPATH/src/github.com/openshift/installer/kubeconfig >> ~/.bashrc
echo alias go_installer=\"cd \$GOPATH/src/github.com/openshift/installer\">> ~/.bashrc
echo alias install=\"cd \$GOPATH/src/github.com/openshift/installer && bin/openshift-install create cluster --log-level=debug\">> ~/.bashrc
mkdir -p ${GOPATH}/{bin,pkg,src}
mkdir -p ${GOPATH}/src/github.com/openshift
cd ${GOPATH}/src/github.com/openshift
curl https://raw.githubusercontent.com/golang/dep/master/install.sh | sh
git clone https://github.com/openshift/installer.git
cd installer
dep ensure
hack/get-terraform.sh
TAGS=libvirt_destroy hack/build.sh
GOBIN=~/.terraform.d/plugins go get -u github.com/dmacvicar/terraform-provider-libvirt
PUBKEY=`cat ~/.ssh/authorized_keys`
echo export OPENSHIFT_INSTALL_SSH_PUB_KEY=\"${PUBKEY}\" >> ~/env.sh
source ~/env.sh
# bin/openshift-install create cluster --log-level=debug
## oc set volume deploy/clusterapi-manager-controllers --add --name=libvirt-socket --type=hostPath --path=/var/run/libvirt --mount-path=/var/run/libvirt -n openshift-cluster-api
