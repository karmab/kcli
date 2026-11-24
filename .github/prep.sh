apt-get update
apt-get -y install python3-pip python3-wheel python3-setuptools python3-all dh-python debhelper build-essential fakeroot libkrb5-dev binutils pycodestyle codespell libvirt-dev pkg-config 
python3 -m venv venv
. venv/bin/activate
pip3 install cloudsmith-cli stdeb copr-cli build twine libvirt-python
pip3 install -U Jinja2
pip3 install -e .

apt-get update && apt-get -y install libvirt-daemon libvirt0 libvirt-daemon-system libvirt-clients qemu-system-x86 qemu-utils qemu-user-binfmt curl genisoimage podman rpm acl
[ -S /var/run/libvirt/libvirt-sock ] && setfacl -m u:runner:rwx /var/run/libvirt/libvirt-sock
