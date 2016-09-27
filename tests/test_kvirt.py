import os
import random
import string
import time
from kvirt import Kvirt


class TestK:
    @classmethod
    def setup_class(self):
        self.host = os.environ.get('KVIRT_HOST', '127.0.0.1')
        self.user = os.environ.get('KVIRT_USER', 'root')
        self.path = os.environ.get('KVIRT_PATH', '')
        self.virttype = os.environ.get('KVIRT_TYPE', 'kvm')
        self.libvirt_user = os.environ.get('KVIRT_LIBVIRTUSER', 'qemu')
        k = Kvirt(self.host)
        name = "test_%s" % ''.join(random.choice(string.lowercase) for i in range(5))
        self.name = name
        self.conn = k

    def test_list(self):
        k = self.conn
        klist = k.list()
        assert klist is not None

    def test_create_network(self):
        k = self.conn
        counter = random.randint(1, 254)
        k.create_network(name=self.name, cidr='10.0.%s.0/24' % counter, dhcp=True)
        assert True

    def test_create_pool(self):
        k = self.conn
        if self.host == '127.0.0.1' or self.host == 'localhost':
                cmd = "mkdir %s/%s; chgrp %s %s/%s" % (self.path, self.name, self.libvirt_user, self.path, self.name)
        else:
                cmd = "ssh %s@%s 'mkdir %s/%s; chgrp %s %s/%s'" % (self.user, self.host, self.path, self.name, self.libvirt_user, self.path, self.name)
        os.system(cmd)
        k.create_pool(name=self.name, poolpath='%s/%s' % (self.path, self.name))
        assert True

    def test_create_vm(self):
        k = self.conn
        time.sleep(10)
        k.create(self.name, virttype=self.virttype, numcpus=1, memory=512, pool=self.name, nets=[self.name])
        status = k.status(self.name)
        print(status)
        assert status is not None

    def test_delete_vm(self):
        k = self.conn
        k.delete(self.name)
        status = k.status(self.name)
        assert status is None

    @classmethod
    def teardown_class(self):
        print("Cleaning stuff")
        k = self.conn
        time.sleep(10)
        k.delete_network(self.name)
        k.delete_pool(self.name, full=True)
