yum -y install libvirt qemu-kvm wget git
mv /usr/local/bin/docker-machine-driver-kvm /usr/bin/
curl -L https://github.com/dhiltgen/docker-machine-kvm/releases/download/v0.7.0/docker-machine-driver-kvm -o /usr/bin/docker-machine-driver-kvm
chmod +x /usr/bin/docker-machine-driver-kvm
wget -O /root/minishift-1.5.0-linux-amd64.tgz https://github.com/minishift/minishift/releases/download/v1.5.0/minishift-1.5.0-linux-amd64.tgz
tar zxvf minishift-1.5.0-linux-amd64.tgz
mv minishift /usr/bin/
groupadd libvirtd
usermod -a -G libvirtd root
newgrp libvirtd
systemctl start libvirtd
systemctl enable libvirtd
wget -O /root/oc.tar.gz https://github.com/openshift/origin/releases/download/v3.7.0-alpha.1/openshift-origin-client-tools-v3.7.0-alpha.1-fdbd3dc-linux-64bit.tar.gz
tar zxvf /root/oc.tar.gz
mv /root/openshift-origin-client-tools-*/oc /usr/bin
