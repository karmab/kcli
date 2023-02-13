#!/usr/bin/env python3
# coding=utf-8

from kvirt.defaults import FAKECERT
from kvirt.bottle import Bottle, request, response, jinja2_view, server_names, ServerAdapter
from kvirt.common import pprint
from kvirt.config import Kconfig
import os
import subprocess
from datetime import datetime
import functools
from tempfile import NamedTemporaryFile


basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/sushy"
view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])


class SSLCherryPy(ServerAdapter):
    def run(self, handler):
        cert = NamedTemporaryFile(delete=False)
        cert.write(FAKECERT.encode())
        cert.close()
        from cheroot.ssl.pyopenssl import pyOpenSSLAdapter
        from cheroot import wsgi
        server = wsgi.Server((self.host, self.port), handler, request_queue_size=32)
        self.srv = server
        server.ssl_adapter = pyOpenSSLAdapter(cert.name, cert.name)
        try:
            server.start()
        finally:
            server.stop()
            os.unlink(cert.name)


class Ksushy():

    def __init__(self):
        app = Bottle()

        @app.route('/redfish/v1/')
        @view('root.json')
        def root_resource():
            return {}

        @app.route('/redfish/v1/Managers')
        @view('managers.json')
        def manager_collection_resource():
            return {}

        @app.route('/redfish/v1/Systems')
        @view('systems.json')
        def system_collection_resource():
            config = Kconfig()
            k = config.k
            vms = []
            for vm in k.list():
                vms.append({"@odata.id": f"/redfish/v1/Systems/{config.client}/{vm['name']}"})
            return {'vms': vms, 'count': len(vms)}

        @app.route('/redfish/v1/Systems/<client>/<name>')
        @view('system.json')
        def system_resource_get(client, name):
            config = Kconfig(client)
            k = config.k
            info = k.info(name)
            if not info:
                response.status = 404
                return f'VM {name} not found'
            status = 'On' if info['status'] == 'up' else 'Off'
            data = {'client': client, 'name': name, 'status': status, 'memory': info['memory'], 'cpus': info['cpus'],
                    'virt_type': config.type}
            return data

        @app.route('/redfish/v1/Systems/<client>/<name>', method='PATCH')
        def system_resource(client, name):
            pprint('ignoring patch request')
            boot = request.json.get('Boot', {})
            if not boot:
                response.status = 400
                return 'PATCH only works for Boot'
            return

        @app.route('/redfish/v1/Systems/<client>/<name>/EthernetInterfaces')
        @view('interfaces.json')
        def manage_interfaces(client, name):
            config = Kconfig(client)
            k = config.k
            info = k.info(name)
            if not info:
                response.status = 404
                return f'VM {name} not found'
            macs = []
            for nic in info.get('nets', []):
                mac = nic['mac']
                macs.append({"@odata.id": f"/redfish/v1/Systems/{client}/{name}/EthernetInterfaces/{mac}"})
            return {'client': client, 'name': name, 'macs': macs, 'count': len(macs)}

        @app.route('/redfish/v1/Systems/<client>/<name>/EthernetInterfaces/<mac>')
        @view('interface.json')
        def manage_interface(client, name, mac):
            return {'client': client, 'name': name, 'mac': mac}

        @app.route('/redfish/v1/Managers/<client>/<name>')
        @view('manager.json')
        def manager_resource(client, name):
            return {'client': client, 'name': name, 'date_time': datetime.now().strftime('%Y-%M-%dT%H:%M:%S+00:00')}

        @app.route('/redfish/v1/Systems/<client>/<name>/Actions/ComputerSystem.Reset', method='POST')
        def system_reset_action(client, name):
            config = Kconfig(client)
            k = config.k
            reset_type = request.json.get('ResetType', 'On')
            if reset_type in ['On', 'ForceRestart']:
                try:
                    pprint(f"Starting vm {name}")
                    k.start(name)
                except subprocess.CalledProcessError:
                    response.status = 400
                    return 'Failed to poweron the server'
            else:
                try:
                    pprint(f"Stopping vm {name}")
                    k.stop(name)
                except subprocess.CalledProcessError:
                    response.status = 400
                    return 'Failed to poweroff the server'
            response.status = 204
            return ''

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia')
        @view('virtualmedias.json')
        def virtualmedia_collection_resource(client, name):
            return {'client': client, 'name': name}

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd')
        @view('virtualmedia_cd.json')
        def virtualmedia_cd_resource(client, name):
            config = Kconfig(client)
            info = config.k.info(name)
            if not info:
                response.status = 404
                return f'VM {name} not found'
            inserted, image_url = False, ''
            if 'iso' in info:
                inserted = True
                image_url = os.path.basename(info['iso'])
            return {'client': client, 'name': name, 'inserted': inserted, 'image_url': image_url}

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia',
                   method='POST')
        def virtualmedia_insert(client, name):
            config = Kconfig(client)
            if not config.k.exists(name):
                response.status = 404
                return f'VM {name} not found'
            image = request.json.get('Image')
            if image is None:
                response.status = 400
                return 'POST only works for Image'
            try:
                pprint(f"Setting iso of vm {name} to {image}")
                iso = os.path.basename(image)
                token_iso = os.path.basename(image).split('?')[0]
                if token_iso != iso:
                    iso = f"boot-{token_iso}.iso"
                isos = [os.path.basename(i) for i in config.k.volumes(iso=True)]
                if iso not in isos:
                    config.handle_host(pool=config.pool, image=iso, download=True, url=image, update_profile=False)
                config.update_vm(name, {'iso': iso})
            except subprocess.CalledProcessError:
                response.status = 400
                return 'Failed to mount virtualcd'
            response.status = 204
            return ''

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia',
                   method='POST')
        def virtualmedia_eject(client, name):
            config = Kconfig(client)
            if not config.k.exists(name):
                response.status = 404
                return f'VM {name} not found'
            try:
                pprint(f"Setting iso of vm {name} to None")
                info = config.k.info(name)
                if 'iso' in info:
                    config.update_vm(name, {'iso': None})
            except subprocess.CalledProcessError:
                return ('Failed to unmount virtualcd', 400)
            response.status = 204
            return ''

        @app.route('/redfish/v1/Systems/<client>/<name>/BIOS')
        @view('bios.json')
        def bios_resource(client, name):
            return {'client': client, 'name': name}

        self.app = app
        self.port = os.environ.get('PORT', 9000)
        self.debug = 'DEBUG' in os.environ
        self.ipv6 = 'IPV6' in os.environ
        self.host = '::' if self.ipv6 else '0.0.0.0'

    def run(self):
        data = {'host': self.host, 'port': self.port, 'debug': self.debug}
        if 'KSUSHY_SSL' in os.environ:
            server_names['sslcherrypy'] = SSLCherryPy
            data['server'] = 'sslcherrypy'
        self.app.run(**data)
