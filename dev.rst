1. Install requirements. you will also need to grab *genisoimage* (or
   *mkisofs* on OSX) for cloudinit isos to get generated Console access
   is based on remote-viewer For instance if using a RHEL based
   distribution:

.. code:: bash

    yum -y install gcc libvirt-devel python-devel genisoimage qemu-kvm nmap-ncat python-pip libguestfs-tools

On Fedora, you' will need an additional package

.. code:: shell

    yum -y install redhat-rpm-config

If using a Debian based distribution:

.. code:: shell

    apt-get -y install python-pip pkg-config libvirt-dev genisoimage qemu-kvm netcat libvirt-bin python-dev libyaml-dev

2. Install kcli from pypi

.. code:: shell

    pip install kcli
