import os
import random
import string
import time
from kvirt import Kvirt


class TestK:
    @classmethod
    def setup_class(self):
        host = os.environ.get('KVIRT_HOST', '127.0.0.1')
        k = Kvirt(host)
        network = "test_%s" % ''.join(random.choice(string.lowercase) for i in range(5))
        pool = "test_%s" % ''.join(random.choice(string.lowercase) for i in range(5))
        name = "test_%s" % ''.join(random.choice(string.lowercase) for i in range(5))
        self.pool = pool
        self.name = name
        self.network = network
        self.conn = k

    def test_list(self):
        k = self.conn
        klist = k.list()
        assert klist is not None

    def test_create_network(self):
        k = self.conn
        network = self.network
        k.create_network(name=network, cidr='192.168.99.0/24', dhcp=True)
        assert True

    def test_create_pool(self):
        k = self.conn
        pool = self.pool
        k.create_pool(name=pool, path='/tmp')
        assert True

    def test_create(self):
        k = self.conn
        name = self.name
        network = self.network
        pool = self.pool
        time.sleep(10)
        k.create(name, numcpus=1, memory=512, pool=pool, nets=[network])
        status = k.status(name)
        print status
        assert status is not None

    def test_delete(self):
        k = self.conn
        name = self.name
        k.delete(name)
        status = k.status(name)
        assert status is None

    @classmethod
    def teardown_class(self):
        print "prout"
        k = self.conn
        network = self.network
        pool = self.pool
        k.delete_network(network)
        k.delete_pool(pool)
