apt-get update
apt-get -y install python3-pip python3-wheel python3-setuptools python3-all python3-distutils dh-python debhelper build-essential fakeroot python3-bcrypt
pip3 install misspellings cloudsmith-cli pep8 stdeb
pip3 install -U Jinja2
apt-get -y install libvirt-daemon libvirt0 qemu-system-x86 qemu-utils qemu-kvm libvirt-daemon-system curl genisoimage python3-libvirt
setfacl -m u:runner:rwx /var/run/libvirt/libvirt-sock
