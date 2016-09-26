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
        name = self.name
        counter = random.randint(1, 254)
        k.create_network(name=name, cidr='10.0.%s.0/24' % counter, dhcp=True)
        assert True

    def test_create_pool(self):
        k = self.conn
        name = self.name
        os.system("ssh %s@%s 'mkdir /%s; chown qemu.qemu /%s'" % (self.user, self.host, name, name))
        k.create_pool(name=name, path='/%s' % name)
        assert True

    def test_create_vm(self):
        k = self.conn
        name = self.name
        time.sleep(10)
        k.create(name, numcpus=1, memory=512, pool=name, nets=[name])
        status = k.status(name)
        print status
        assert status is not None

    def test_delete_vm(self):
        k = self.conn
        name = self.name
        k.delete(name)
        status = k.status(name)
        assert status is None

    @classmethod
    def teardown_class(self):
        print "Cleaning stuff"
        k = self.conn
        name = self.name
        time.sleep(10)
        k.delete_network(name)
        k.delete_pool(name, full=True)
