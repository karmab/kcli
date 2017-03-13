#!/usr/bin/python

# import getpass
# from mock import patch
from flask import Flask, render_template
from defaults import NETS, POOL, NUMCPUS, MEMORY, DISKS, DISKSIZE, DISKINTERFACE, DISKTHIN, GUESTID, VNC, CLOUDINIT, RESERVEIP, RESERVEDNS, START, NESTED, TUNNEL
# from defaults import TEMPLATES
from kvm import Kvirt
from vbox import Kbox
import os
import yaml


class Config():
    def load(self):
        inifile = "%s/kcli.yml" % os.environ.get('HOME')
        if not os.path.exists(inifile):
            if os.path.exists('/Users'):
                _type = 'vbox'
            else:
                _type = 'kvm'
            ini = {'default': {'client': 'local'}, 'local': {'pool': 'default', 'type': _type}}
            print("Using local hypervisor as no kcli.yml was found...")
        else:
            with open(inifile, 'r') as entries:
                try:
                    ini = yaml.load(entries)
                except:
                    self.host = None
                    return
            if 'default' not in ini or 'client' not in ini['default']:
                print("Missing default section in config file. Leaving...")
                self.host = None
                return
        self.clients = [e for e in ini if e != 'default']
        defaults = {}
        default = ini['default']
        defaults['nets'] = default.get('nets', NETS)
        defaults['pool'] = default.get('pool', POOL)
        defaults['numcpus'] = int(default.get('numcpus', NUMCPUS))
        defaults['memory'] = int(default.get('memory', MEMORY))
        defaults['disks'] = default.get('disks', DISKS)
        defaults['disksize'] = default.get('disksize', DISKSIZE)
        defaults['diskinterface'] = default.get('diskinterface', DISKINTERFACE)
        defaults['diskthin'] = default.get('diskthin', DISKTHIN)
        defaults['guestid'] = default.get('guestid', GUESTID)
        defaults['vnc'] = bool(default.get('vnc', VNC))
        defaults['cloudinit'] = bool(default.get('cloudinit', CLOUDINIT))
        defaults['reserveip'] = bool(default.get('reserveip', RESERVEIP))
        defaults['reservedns'] = bool(default.get('reservedns', RESERVEDNS))
        defaults['nested'] = bool(default.get('nested', NESTED))
        defaults['start'] = bool(default.get('start', START))
        defaults['tunnel'] = default.get('tunnel', TUNNEL)
        self.default = defaults
        self.ini = ini
        profilefile = default.get('profiles', "%s/kcli_profiles.yml" % os.environ.get('HOME'))
        profilefile = os.path.expanduser(profilefile)
        if not os.path.exists(profilefile):
            self.profiles = {}
        else:
            with open(profilefile, 'r') as entries:
                self.profiles = yaml.load(entries)

    def get(self, client=None):
        if client is None:
            self.client = self.ini['default']['client']
        else:
            self.client = client
        if self.client not in self.ini:
            print("Missing section for client %s in config file. Leaving..." % self.client)
            os._exit(1)
        options = self.ini[self.client]
        self.host = options.get('host', '127.0.0.1')
        self.port = options.get('port', 22)
        self.user = options.get('user', 'root')
        self.protocol = options.get('protocol', 'ssh')
        self.url = options.get('url', None)
        self.tunnel = bool(options.get('tunnel', self.default['tunnel']))
        self.type = options.get('type', 'kvm')
        if self.type == 'vbox':
            k = Kbox()
        else:
            if self.host is None:
                print("Problem parsing your configuration file")
                os._exit(1)
            k = Kvirt(host=self.host, port=self.port, user=self.user, protocol=self.protocol, url=self.url, debug=self.debug)
        if k.conn is None:
            print("Couldnt connect to specify hypervisor %s. Leaving..." % self.host)
            os._exit(1)
        return k

app = Flask(__name__)
try:
    app.config.from_object('settings')
    config = app.config
except ImportError:
    config = {'PORT': os.environ.get('PORT', 9000)}

debug = config['DEBUG'] if 'DEBUG' in config.keys() else True
port = int(config['PORT']) if 'PORT'in config.keys() else 9000


class TABLE(object):
    pass


@app.route("/")
@app.route('/index')
def get():
    """
    retrieves all vms
    """
    vms = k.list()
    return render_template('index.html', title='Home', vms=vms)

if __name__ == '__main__':
    global k
    config = Config()
    config.load()
    config.debug = debug
    k = config.get()
    # with patch.object(getpass, "getuser", return_value='default'):
    app.run(host='0.0.0.0', port=port, debug=debug)
