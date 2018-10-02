yum -y install libvirt-client libvirt-devel golang-bin gcc-c++ git unzip
tar -Cvf /usr/local -xzf go{{ version }}.linux-amd64.tar.gz
export GOPATH=/root/go
export PATH=$PATH:/usr/local/go/bin:$GOPATH/bin
echo export GOPATH=/root/go >> ~/.bashrc
echo export PATH=\$PATH:/usr/local/go/bin:\$GOPATH/bin >> ~/.bashrc
mkdir -p $GOPATH/{bin,pkg,src}
mkdir -p $GOPATH/src/github/openshift
cd $GOPATH/src/github/openshift
curl https://glide.sh/get | sh
go get github.com/sgotti/glide-vc
git clone https://github.com/openshift/installer.git
cd installer
rm -f glide.lock
glide install --strip-vendor
glide-vc --use-lock-file --no-tests --only-code
hack/get-terraform.sh
hack/build.sh
GOBIN=~/.terraform.d/plugins go get -u github.com/dmacvicar/terraform-provider-libvirt
ssh-keyscan -H 192.168.122.1 >> ~/.ssh/known_hosts
