#!/usr/bin/env python3
# coding=utf-8

from kvirt.bottle import Bottle, request, response, jinja2_view
from kvirt.common import pprint
from kvirt.config import Kconfig
import os
import subprocess
from datetime import datetime
import functools

app = Bottle()
config = {'PORT': os.environ.get('PORT', 9000)}
debug = config['DEBUG'] if 'DEBUG' in list(config) else True
port = int(config['PORT']) if 'PORT' in list(config) else 9000

basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/ksushy"
view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])


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
    vms = [vm['name'] for vm in k.list()]
    return {'client': config.client, 'vms': vms, 'count': len(vms)}


@app.route('/redfish/v1/Systems/<client>/<name>')
@view('system.json')
def system_resource_get(client, name):
    config = Kconfig(client)
    k = config.k
    info = k.info(name)
    power_state = 'On' if info['status'] == 'up' else 'Off'
    return {'client': client, 'name': name, 'power_state': power_state}


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
    macs = []
    for nic in info.get('nets', []):
        macs.append(nic['mac'])
    return {'client': client, 'name': name, 'macs': macs, 'count': len(macs)}


@app.route('/redfish/v1/Managers/<client>/<name>')
@view('manager.json')
def manager_resource(client, name):
    return {'client': client, 'name': name, 'date_time': datetime.now().strftime('%Y-%M-%dT%H:%M:%S+00:00')}


@app.route('/redfish/v1/Systems/<client>/<name>/Actions/ComputerSystem.Reset', method='POST')
def system_reset_action(client, name):
    config = Kconfig(client)
    k = config.k
    reset_type = request.json.get('ResetType', 'On')
    if reset_type == 'On':
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
    inserted, image_url = False, ''
    if 'iso' in info:
        inserted = True
        image_url = os.path.basename(info['iso'])
    return {'client': client, 'name': name, 'inserted': inserted, 'image_url': image_url}


@app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia', method='POST')
def virtualmedia_insert(client, name):
    config = Kconfig(client)
    image = request.json.get('Image')
    if image is None:
        response.status = 400
        return 'POST only works for Image'
    try:
        pprint(f"Setting iso of vm {name} to {image}")
        iso = os.path.basename(image)
        if iso not in config.k.volumes(iso=True):
            config.handle_host(pool=config.pool, image=iso, download=True, url=image, update_profile=False)
        config.update_vm(name, {'iso': iso})
    except subprocess.CalledProcessError:
        response.status = 400
        return 'Failed to mount virtualcd'
    response.status = 204
    return ''


@app.route('/redfish/v1/Managers/<client>/<name>/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia', method='POST')
def virtualmedia_eject(client, name):
    config = Kconfig(client)
    try:
        pprint(f"Setting iso of vm {name} to None")
        info = config.k.info(name)
        if 'iso' in info:
            config.update_vm(name, {'iso': None})
    except subprocess.CalledProcessError:
        return ('Failed to unmount virtualcd', 400)
    response.status = 204
    return ''


def run():
    """

    """
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    run()
