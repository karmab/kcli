import argparse
import sys

from kvirt.config import Kconfig
from kvirt.common import pprint
import pyghmi.ipmi.bmc as bmc


class KBmc(bmc.Bmc):
    def __init__(self, authdata, port, name, client):
        super(KBmc, self).__init__(authdata, port)
        self.bootdevice = 'default'
        self.k = Kconfig(client=client).k
        if not self.k.exists(name):
            pprint('%s not found.Leaving' % name, color='red')
            sys.exit(1)
        else:
            status = self.k.info(name)['status']
            self.powerstate = 'off' if status.lower() not in ['up', 'poweredon'] else 'on'
            pprint('Handling vm %s on port %s' % (name, port))
            pprint('Initial state for vm %s: %s' % (name, self.powerstate), color='blue')
        self.name = name

    def get_boot_device(self):
        return self.bootdevice

    def set_boot_device(self, bootdevice):
        self.bootdevice = bootdevice

    def cold_reset(self):
        pprint('shutting down in response to BMC cold reset request', color='red')
        sys.exit(0)

    def get_power_state(self):
        return self.powerstate

    def power_off(self):
        result = self.k.stop(self.name)
        if result['result'] == 'success':
            pprint('%s powered off!' % self.name)
            self.powerstate = 'off'
        else:
            pprint('%s not powered off because %s' % (self.name, result['reason']), color='red')

    def power_on(self):
        result = self.k.start(self.name)
        if result['result'] == 'success':
            self.powerstate = 'on'
            pprint('%s powered on!' % self.name)
        else:
            pprint('%s not powered on because %s' % (self.name, result['reason']), color='red')

    def power_reset(self):
        pass

    def power_shutdown(self):
        self.power_off()

    def is_active(self):
        return self.powerstate == 'on'

    def iohandler(self, data):
        print(data)
        if self.sol:
            self.sol.send_data(data)


def main():
    parser = argparse.ArgumentParser(prog='kbmc', description='BMC using kcli')
    parser.add_argument('-C', '--client', dest='client', type=str, help='Client to use')
    parser.add_argument('--user', dest='user', type=str, default='admin', help='User to use. Defaults to admin')
    parser.add_argument('--password', dest='password', type=str, default='password',
                        help='Password to use. Defaults to password')
    parser.add_argument('--port', dest='port', type=int, default=6230, help='Port to listen on. Defaults to 6230')
    # parser.add_argument('-f', '--foreground', action='store_true', help='Stay in foreground')
    parser.add_argument('name', type=str, help='Vm to handle')
    args = parser.parse_args()
    kbmc = KBmc({args.user: args.password}, port=args.port, name=args.name, client=args.client)
    kbmc.listen()


if __name__ == '__main__':
    sys.exit(main())
