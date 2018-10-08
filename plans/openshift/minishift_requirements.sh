export MINISHIFT_VERSION="[[ minishift_version ]]"
export OPENSHIFT_VERSION="v[[ openshift_version ]]"
curl -L https://github.com/minishift/minishift/releases/download/v${MINISHIFT_VERSION}/minishift-${MINISHIFT_VERSION}-linux-amd64.tgz > /root/minishift-${MINISHIFT_VERSION}-linux-amd64.tgz
tar zxvf /root/minishift-${MINISHIFT_VERSION}-linux-amd64.tgz
mv minishift-${MINISHIFT_VERSION}-linux-amd64/minishift /usr/bin/
chmod u+x /usr/bin/minishift
[% if driver == 'kvm' %]
echo options kvm-intel nested=1 >> /etc/modprobe.d/kvm-intel.conf
modprobe -r kvm_intel
modprobe kvm_intel
curl -L https://github.com/dhiltgen/docker-machine-kvm/releases/download/v0.7.0/docker-machine-driver-kvm -o /usr/local/bin/docker-machine-driver-kvm
chmod +x /usr/local/bin/docker-machine-driver-kvm
yum -y install libvirt qemu wget jq
systemctl enable libvirtd
systemctl start libvirtd
[% endif %]
