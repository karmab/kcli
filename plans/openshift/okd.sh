yum -y install libvirt-client libvirt-devel gcc-c++ git unzip wget
ssh-keyscan -H 192.168.122.1 >> ~/.ssh/known_hosts
scp root@192.168.122.1:[[ rhcos_path ]] /root/rhcos.qcow2
wget https://dl.google.com/go/go[[ go_version ]].linux-amd64.tar.gz
tar -C /usr/local -xzf go[[ go_version ]].linux-amd64.tar.gz
export GOPATH=/root/go
export PATH=$PATH:/usr/local/go/bin:${GOPATH}/bin:${GOPATH}/src/github/openshift/installer/bin
echo export GOPATH=/root/go >> ~/.bashrc
echo export PATH=\$PATH:/usr/local/go/bin:\$GOPATH/bin:\$GOPATH/src/github/openshift/installer/bin >> ~/.bashrc
echo alias go_okd=\"cd \$GOPATH/src/github.com/openshift/installer\">> ~/.bashrc
mkdir -p ${GOPATH}/{bin,pkg,src}
mkdir -p ${GOPATH}/src/github.com/openshift
cd ${GOPATH}/src/github.com/openshift
curl https://glide.sh/get | sh
go get github.com/sgotti/glide-vc
git clone https://github.com/openshift/installer.git
cd installer
rm -f glide.lock
glide install --strip-vendor
glide-vc --use-lock-file --no-tests --only-code
hack/get-terraform.sh
#hack/build.sh
TAGS=libvirt_destroy hack/build.sh
GOBIN=~/.terraform.d/plugins go get -u github.com/dmacvicar/terraform-provider-libvirt
PUBKEY=`cat ~/.ssh/authorized_keys`
echo export OPENSHIFT_INSTALL_SSH_PUB_KEY=\"${PUBKEY}\" >> ~/env.sh
source ~/env.sh
# bin/openshift-install ignition-configs --dir ${WORKSPACE}
# bin/openshift-install manifests --dir ${WORKSPACE}
# bin/openshift-install cluster --log-level=debug
