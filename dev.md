1. Install requirements. you will also need to grab *genisoimage* (or *mkisofs* on OSX) for cloudinit isos to get generated
Console access is based on remote-viewer
For instance if using a RHEL based distribution:

```bash
yum -y install gcc libvirt-devel python-devel genisoimage qemu-kvm nmap-ncat python-pip libguestfs-tools
```

On Fedora, you' will need an additional package

```Shell
yum -y install redhat-rpm-config
```

If using a Debian based distribution:

```Shell
apt-get -y install python-pip pkg-config libvirt-dev genisoimage qemu-kvm netcat libvirt-bin python-dev libyaml-dev
```

If you want to use virtualbox, you ll need the following too:

```Shell
curl -O http://download.virtualbox.org/virtualbox/5.1.14/VirtualBoxSDK-5.1.14-112924.zip
unzip VirtualBoxSDK-5.1.14-112924.zip
cd sdk/installer
VBOX_INSTALL_PATH=/usr/lib/virtualbox python vboxapisetup.py install
```

If you want to use virtualbox on macosx, you will also need :

```Shell
brew install qemu
```

2. Install kcli from pypi

```Shell
pip install kcli
```
