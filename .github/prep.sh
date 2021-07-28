apt-get update
apt-get -y install python3-pip python3-wheel python3-setuptools python3-all python3-distutils dh-python debhelper build-essential fakeroot 
pip3 install misspellings cloudsmith-cli pep8 stdeb
apt-get -y install libvirt-daemon libvirt0 qemu-system-x86 qemu-utils qemu-kvm libvirt-daemon-system curl genisoimage
