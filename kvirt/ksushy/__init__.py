#!/usr/bin/env python3
# coding=utf-8

from kvirt.defaults import FAKECERT
from kvirt.bottle import Bottle, request, response, jinja2_view, server_names, ServerAdapter, auth_basic
from kvirt.common import pprint, error
from kvirt.baseconfig import Kbaseconfig
from kvirt.config import Kconfig
import os
import subprocess
from datetime import datetime
import functools
from tempfile import NamedTemporaryFile


basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/ksushy"
view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])

default_user = os.environ.get('KSUSHY_USER')
default_password = os.environ.get('KSUSHY_PASSWORD')


def credentials(user, password):
    if default_user is None or default_password is None:
        return True
    elif user is None or password is None:
        return False
    elif user == default_user or password == default_password:
        return True
    else:
        return False


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

        @app.route('/redfish/v1')
        @app.route('/redfish/v1/')
        @auth_basic(credentials)
        @view('root.json')
        def root_resource():
            return {}

        @app.route('/redfish/v1/Managers')
        @auth_basic(credentials)
        @view('managers.json')
        def manager_collection_resource():
            return {}

        @app.route('/redfish/v1/Systems')
        @auth_basic(credentials)
        @view('systems.json')
        def system_collection_resource():
            clients = []
            baseconfig = Kbaseconfig()
            for client in baseconfig.clients:
                clients.append({"@odata.id": f"/redfish/v1/Systems/{client}"})
            return {'vms': clients, 'count': len(clients)}

        @app.route('/redfish/v1/Systems/<client>')
        @auth_basic(credentials)
        @view('systems.json')
        def system_collection_client_resource(client):
            baseconfig = Kbaseconfig()
            if client not in baseconfig.clients:
                response.status = 404
                msg = f'Client {client} not found'
                error(msg)
                return msg
            config = Kconfig(client)
            k = config.k
            vms = []
            for vm in k.list():
                vms.append({"@odata.id": f"/redfish/v1/Systems/{client}/{vm['name']}"})
            return {'vms': vms, 'count': len(vms)}

        @app.route('/redfish/v1/Systems/<client>/<name>')
        @auth_basic(credentials)
        @view('system.json')
        def system_resource_get(client, name):
            baseconfig = Kbaseconfig()
            if client not in baseconfig.clients:
                response.status = 404
                msg = f'Client {client} not found'
                error(msg)
                return msg
            config = Kconfig(client)
            k = config.k
            info = k.info(name)
            if not info:
                response.status = 404
                msg = f'VM {name} not found'
                error(msg)
                return msg
            status = 'On' if info['status'] == 'up' else 'Off'
            data = {'client': client, 'name': name, 'status': status, 'memory': info['memory'], 'cpus': info['cpus'],
                    'virt_type': config.type}
            if 'id' in info:
                data['uuid'] = info['id']
            return data

        @app.route('/redfish/v1/Systems/<client>/<name>', method='PATCH')
        @auth_basic(credentials)
        def system_resource(client, name):
            if not self.bootonce:
                return
            boot = request.json.get('Boot', {})
            if not boot:
                response.status = 400
                msg = 'PATCH only works for Boot'
                error(msg)
                return msg
            target = boot.get('BootSourceOverrideTarget')
            mode = boot.get('BootSourceOverrideMode')
            if not target and not mode:
                response.status = 400
                msg = 'Missing the BootSourceOverrideTarget and/or BootSourceOverrideMode element'
                error(msg)
                return msg
            else:
                baseconfig = Kbaseconfig()
                if client not in baseconfig.clients:
                    response.status = 404
                    msg = f'Client {client} not found'
                    error(msg)
                    return msg
                config = Kconfig(client)
                k = config.k
                info = k.info(name)
                pprint('Forcing to boot from ISO by deleting primary disk')
                try:
                    pool = config.pool
                    diskname = f"{name}_0.img"
                    size = info['disks'][0]['size']
                    interface = info['disks'][0]['format']
                    k.stop(name)
                    k.delete_disk(name=name, diskname=diskname, pool=pool)
                    k.add_disk(name=name, size=size, pool=pool, interface=interface, diskname=diskname)
                except Exception as e:
                    msg = f'Failed to set boot from virtualcd once. Hit {e}'
                    error(msg)
                    response.status = 400
                    return msg
                response.status = 204
                return ''

        @app.route('/redfish/v1/Systems/<client>/<name>/EthernetInterfaces')
        @auth_basic(credentials)
        @view('interfaces.json')
        def manage_interfaces(client, name):
            baseconfig = Kbaseconfig()
            if client not in baseconfig.clients:
                response.status = 404
                msg = f'Client {client} not found'
                error(msg)
                return msg
            config = Kconfig(client)
            k = config.k
            info = k.info(name)
            if not info:
                response.status = 404
                msg = f'VM {name} not found'
                error(msg)
                return msg
            macs = []
            for nic in info.get('nets', []):
                mac = nic['mac']
                macs.append({"@odata.id": f"/redfish/v1/Systems/{client}/{name}/EthernetInterfaces/{mac}"})
            return {'client': client, 'name': name, 'macs': macs, 'count': len(macs)}

        @app.route('/redfish/v1/Systems/<client>/<name>/EthernetInterfaces/<mac>')
        @auth_basic(credentials)
        @view('interface.json')
        def manage_interface(client, name, mac):
            return {'client': client, 'name': name, 'mac': mac}

        @app.route('/redfish/v1/Managers/<client>/<name>')
        @auth_basic(credentials)
        @view('manager.json')
        def manager_resource(client, name):
            return {'client': client, 'name': name, 'date_time': datetime.now().strftime('%Y-%M-%dT%H:%M:%S+00:00')}

        @app.route('/redfish/v1/Systems/<client>/<name>/Actions/ComputerSystem.Reset', method='POST')
        @auth_basic(credentials)
        def system_reset_action(client, name):
            baseconfig = Kbaseconfig()
            if client not in baseconfig.clients:
                response.status = 404
                msg = f'Client {client} not found'
                error(msg)
                return msg
            config = Kconfig(client)
            k = config.k
            reset_type = request.json.get('ResetType', 'On')
            if reset_type in ['On', 'ForceRestart']:
                try:
                    pprint(f"Starting vm {name}")
                    k.start(name)
                except subprocess.CalledProcessError as e:
                    error(e)
                    response.status = 400
                    return 'Failed to poweron the server'
            else:
                try:
                    pprint(f"Stopping vm {name}")
                    k.stop(name)
                except subprocess.CalledProcessError as e:
                    error(e)
                    response.status = 400
                    return 'Failed to poweroff the server'
            response.status = 204
            return ''

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia')
        @auth_basic(credentials)
        @view('virtualmedias.json')
        def virtualmedia_collection_resource(client, name):
            return {'client': client, 'name': name}

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd')
        @auth_basic(credentials)
        @view('virtualmedia_cd.json')
        def virtualmedia_cd_resource(client, name):
            baseconfig = Kbaseconfig()
            if client not in baseconfig.clients:
                response.status = 404
                msg = f'Client {client} not found'
                error(msg)
                return msg
            config = Kconfig(client)
            info = config.k.info(name)
            if not info:
                response.status = 404
                msg = f'VM {name} not found'
                error(msg)
                return msg
            inserted, image_url = False, ''
            if 'iso' in info:
                inserted = True
                image_url = os.path.basename(info['iso'])
            return {'client': client, 'name': name, 'inserted': inserted, 'image_url': image_url}

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia',
                   method='POST')
        @auth_basic(credentials)
        def virtualmedia_insert(client, name):
            baseconfig = Kbaseconfig()
            if client not in baseconfig.clients:
                response.status = 404
                msg = f'Client {client} not found'
                error(msg)
                return msg
            config = Kconfig(client)
            if not config.k.exists(name):
                response.status = 404
                msg = f'VM {name} not found'
                error(msg)
                return msg
            image = request.json.get('Image')
            if image is None:
                response.status = 400
                msg = 'POST only works for Image'
                error(msg)
                return msg
            try:
                pprint(f"Setting iso of vm {name} to {image}")
                info = config.k.info(name)
                if 'redfish_iso' in info:
                    iso = info['redfish_iso']
                else:
                    iso = os.path.basename(image)
                    token_iso = os.path.basename(image).split('?')[0]
                    if token_iso != iso:
                        iso = f"boot-{token_iso}.iso"
                isos = [os.path.basename(i) for i in config.k.volumes(iso=True)]
                if iso not in isos:
                    result = config.download_image(pool=config.pool, image=iso, url=image)
                    if result['result'] != 'success':
                        raise Exception(result['reason'])
                config.update_vm(name, {'iso': iso})
            except Exception as e:
                msg = f'Failed to mount virtualcd. Hit {e}'
                error(msg)
                response.status = 500
                return msg
            response.status = 204
            return ''

        @app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia',
                   method='POST')
        @auth_basic(credentials)
        def virtualmedia_eject(client, name):
            baseconfig = Kbaseconfig()
            if client not in baseconfig.clients:
                response.status = 404
                msg = f'Client {client} not found'
                error(msg)
                return msg
            config = Kconfig(client)
            if not config.k.exists(name):
                response.status = 404
                msg = f'VM {name} not found'
                error(msg)
                return msg
            try:
                pprint(f"Setting iso of vm {name} to None")
                info = config.k.info(name)
                if 'iso' in info:
                    config.update_vm(name, {'iso': None})
            except subprocess.CalledProcessError as e:
                error(e)
                return ('Failed to unmount virtualcd', 400)
            response.status = 204
            return ''

        @app.route('/redfish/v1/Systems/<client>/<name>/BIOS')
        @auth_basic(credentials)
        @view('bios.json')
        def bios_resource(client, name):
            return {'client': client, 'name': name}

        self.app = app
        self.port = os.environ.get('KSUSHY_PORT', 9000)
        self.debug = 'KSUSHY_DEBUG' in os.environ
        self.ipv6 = 'KSUSHY_IPV6' in os.environ
        self.host = '::' if self.ipv6 else '0.0.0.0'
        self.bootonce = 'KSUSHY_BOOTONCE' in os.environ

    def run(self):
        data = {'host': self.host, 'port': self.port, 'debug': self.debug}
        if 'KSUSHY_SSL' in os.environ:
            server_names['sslcherrypy'] = SSLCherryPy
            data['server'] = 'sslcherrypy'
        self.app.run(**data)
