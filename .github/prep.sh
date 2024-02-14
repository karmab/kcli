apt-get update
apt-get -y install python3-pip python3-wheel python3-setuptools python3-all dh-python debhelper build-essential fakeroot libkrb5-dev binutils
pip3 install misspellings cloudsmith-cli pycodestyle stdeb copr-cli
pip3 install -U Jinja2
apt-get -y install libvirt-daemon libvirt0 qemu-system-x86 qemu-utils qemu-kvm libvirt-daemon-system curl genisoimage python3-libvirt qemu-user-static podman
setfacl -m u:runner:rwx /var/run/libvirt/libvirt-sock
