#!/usr/bin/python
# coding=utf-8

import functools
from kvirt.bottle import Bottle, request, static_file, jinja2_view, response, redirect
from kvirt.config import Kconfig
from kvirt.common import print_info, get_free_port
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt.defaults import IMAGES, WEBSOCKIFYCERT
from kvirt import nameutils
import os
from shutil import which
from time import sleep
from threading import Thread

app = Bottle()
config = {'PORT': os.environ.get('PORT', 9000)}
debug = config['DEBUG'] if 'DEBUG' in list(config) else True
port = int(config['PORT']) if 'PORT' in list(config) else 9000

basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/web"
view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])


@app.route('/static/<filename:path>')
def server_static(filename):
    return static_file(filename, root=f'{basedir}/static')

# VMS


@app.route('/vmstable')
@view('vmstable.html')
def vmstable():
    """
    retrieves all vms in table
    """
    config = Kconfig()
    k = config.k
    vms = []
    for vm in k.list():
        vm['info'] = print_info(vm, output='plain', pretty=True)
        vms.append(vm)
    return {'vms': vms}


@app.route("/")
@app.route('/vms')
@view('vms.html')
def vms():
    """

    :return:
    """
    baseconfig = Kbaseconfig()
    return {'title': 'Home', 'client': baseconfig.client}


@app.route('/vmcreate')
@view('vmcreate.html')
def vmcreate():
    """
    create vm
    """
    config = Kconfig()
    images = [os.path.basename(v) for v in config.k.volumes()]
    disks = []
    for disk in config.disks:
        if isinstance(disk, int):
            disks.append(str(disk))
        else:
            disks.append(str(disk['size']))
    disks = ','.join(disks)
    nets = []
    for net in config.nets:
        if isinstance(net, str):
            nets.append(net)
        else:
            nets.append(net['name'])
    nets = ','.join(nets)
    parameters = {'memory': config.memory, 'numcpus': config.numcpus, 'disks': disks, 'nets': nets}
    return {'title': 'CreateVm', 'images': images, 'parameters': parameters, 'client': config.client}


@app.route('/vmprofilestable')
@view('vmprofilestable.html')
def vmprofilestable():
    """
    retrieves vm profiles in table
    """
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_profiles()
    return {'profiles': profiles}


@app.route('/vmprofiles')
@view('vmprofiles.html')
def vmprofiles():
    """

    :return:
    """
    baseconfig = Kbaseconfig()
    return {'title': 'VmProfiles', 'client': baseconfig.client}


@app.route("/diskaction", method='POST')
def diskaction():
    """
    add/delete disk to vm
    """
    config = Kconfig()
    k = config.k
    if 'action' in request.forms:
        action = request.forms['action']
        if action not in ['create', 'delete']:
            result = {'result': 'failure', 'reason': "Incorrect action"}
            response.status = 400
        else:
            if action == 'add':
                name = request.forms['name']
                size = int(request.forms['size'])
                pool = request.forms['pool']
                result = k.add_disk(name, size, pool)
            elif action == 'delete':
                name = request.forms['name']
                diskname = request.forms['disk']
                result = k.delete_disk(name, diskname)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/nicaction", method='POST')
def nicaction():
    """
    add/delete nic to vm
    """
    config = Kconfig()
    k = config.k
    if 'action' in request.forms:
        action = request.forms['action']
        if action not in ['create', 'delete']:
            result = {'result': 'failure', 'reason': "Incorrect action"}
            response.status = 400
        else:
            if action == 'add':
                name = request.forms['name']
                network = request.forms['network']
                result = k.add_nic(name, network)
            elif action == 'delete':
                name = request.forms['name']
                nicname = request.forms['nic']
                result = k.delete_nic(name, nicname)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


# CONTAINERS


@app.route('/containercreate')
@view('containercreate.html')
def containercreate():
    """
    create container
    """
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_containerprofiles()
    return {'title': 'CreateContainer', 'profiles': profiles, 'client': baseconfig.client}


# POOLS


@app.route('/poolcreate')
@view('poolcreate.html')
def poolcreate():
    """
    pool form
    """
    config = Kconfig()
    return {'title': 'CreatePool', 'client': config.client}


@app.route("/poolaction", method='POST')
def poolaction():
    """
    create/delete pool
    """
    config = Kconfig()
    k = config.k
    if 'pool' in request.forms:
        pool = request.forms['pool']
        action = request.forms['action']
        if action not in ['create', 'delete']:
            result = {'result': 'failure', 'reason': "Incorrect action"}
            response.status = 400
        else:
            if action == 'create':
                path = request.forms['path']
                pooltype = request.forms['type']
                result = k.create_pool(name=pool, poolpath=path, pooltype=pooltype)
            elif action == 'delete':
                result = k.delete_pool(name=pool)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


# REPOS

@app.route("/repoaction", method='POST')
def repoaction():
    """
    create/delete repo
    """
    config = Kconfig()
    if 'repo' in request.forms:
        repo = request.forms['repo']
        action = request.forms['action']
        if action not in ['create', 'delete', 'update']:
            result = {'result': 'failure', 'reason': "Incorrect action"}
            response.status = 400
        else:
            if action == 'create':
                url = request.forms['url']
                if url == '':
                    result = {'result': 'failure', 'reason': "Invalid Data"}
                    response.status = 400
                else:
                    result = config.create_repo(repo, url)
            elif action == 'update':
                result = config.update_repo(repo)
            elif action == 'delete':
                result = config.delete_repo(repo)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result

# NETWORKS


@app.route('/networkcreate')
@view('networkcreate.html')
def networkcreate():
    """
    network form
    """
    config = Kconfig()
    return {'title': 'CreateNetwork', 'client': config.client}


@app.route("/networkaction", method='POST')
def networkaction():
    """
    create/delete network
    """
    config = Kconfig()
    k = config.k
    if 'network' in request.forms:
        network = request.forms['network']
        action = request.forms['action']
        if action not in ['create', 'delete']:
            result = {'result': 'failure', 'reason': "Incorrect action"}
            response.status = 400
        else:
            if action == 'create':
                cidr = request.forms['cidr']
                dhcp = bool(request.forms['dhcp'])
                isolated = bool(request.forms['isolated'])
                nat = not isolated
                result = k.create_network(name=network, cidr=cidr, dhcp=dhcp, nat=nat)
            elif action == 'delete':
                result = k.delete_network(name=network)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


# PLANS


@app.route('/plancreate')
@view('plancreate.html')
def plancreate():
    """
    create plan
    """
    config = Kconfig()
    return {'title': 'CreatePlan', 'client': config.client}


@app.route("/vmaction", method='POST')
def vmaction():
    """
    start/stop/delete/create vm
    """
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        action = request.forms['action']
        if action not in ['start', 'stop', 'delete', 'create']:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
        else:
            if action == 'start':
                result = k.start(name)
            elif action == 'stop':
                result = k.stop(name)
            elif action == 'delete':
                result = k.delete(name)
            elif action == 'create' and 'profile' in request.forms:
                profile = request.forms['profile']
                parameters = {}
                for p in request.forms:
                    if p.startswith('parameters'):
                        value = request.forms[p]
                        key = p.replace('parameters[', '').replace(']', '')
                        parameters[key] = value
                parameters['nets'] = parameters['nets'].split(',')
                parameters['disks'] = [int(disk) for disk in parameters['disks'].split(',')]
                if name == '':
                    name = nameutils.get_random_name()
                result = config.create_vm(name, profile, overrides=parameters)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


# HOSTS

@app.route("/hostaction", method='POST')
def hostaction():
    """
    enable/disable/default host
    """
    baseconfig = Kbaseconfig()
    if 'name' in request.forms:
        name = request.forms['name']
        action = request.forms['action']
        if action not in ['enable', 'disable', 'switch']:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
        else:
            if action == 'enable':
                result = baseconfig.enable_host(name)
            elif action == 'disable':
                result = baseconfig.disable_host(name)
            elif action == 'switch':
                result = baseconfig.switch_host(name)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/snapshotaction", method='POST')
def snapshotaction():
    """
    create/delete/revert snapshot
    """
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        action = request.forms['action']
        if action not in ['list', 'revert', 'delete', 'create']:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
        else:
            if action == 'list':
                result = k.snapshot(None, name, listing=True)
            elif action == 'create':
                snapshot = request.forms['snapshot']
                result = k.snapshot(snapshot, name)
            elif action == 'delete':
                snapshot = request.forms['snapshot']
                result = k.snapshot(snapshot, name, delete=True)
            elif action == 'revert':
                snapshot = request.forms['snapshot']
                name = request.forms['name']
                result = k.snapshot(snapshot, name, revert=True)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/planaction", method='POST')
def planaction():
    """
    start/stop/delete plan
    """
    config = Kconfig()
    if 'name' in request.forms:
        plan = request.forms['name']
        action = request.forms['action']
        if action not in ['start', 'stop', 'delete', 'create']:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
        else:
            if action == 'start':
                result = config.start_plan(plan)
            elif action == 'stop':
                result = config.stop_plan(plan)
            elif action == 'delete':
                result = config.delete_plan(plan)
            elif action == 'create':
                print(request.forms)
                url = request.forms['url']
                if plan == '':
                    plan = nameutils.get_random_name()
                result = config.plan(plan, url=url)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route('/containerstable')
@view('containerstable.html')
def containerstable():
    """
    retrieves all containers in table
    """
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    containers = cont.list_containers()
    return {'containers': containers}


@app.route('/containers')
@view('containers.html')
def containers():
    """
    retrieves all containers
    """
    config = Kconfig()
    return {'title': 'Containers', 'client': config.client}


@app.route('/networkstable')
@view('networkstable.html')
def networkstable():
    """
    retrieves all networks in table
    """
    config = Kconfig()
    k = config.k
    networks = k.list_networks()
    return {'networks': networks}


@app.route('/networks')
@view('networks.html')
def networks():
    """
    retrieves all networks
    """
    config = Kconfig()
    return {'title': 'Networks', 'client': config.client}


@app.route('/poolstable')
@view('poolstable.html')
def poolstable():
    """
    retrieves all pools in table
    """
    config = Kconfig()
    k = config.k
    pools = []
    for pool in k.list_pools():
        poolpath = k.get_pool_path(pool)
        pools.append([pool, poolpath])
    return {'pools': pools}


@app.route('/pools')
@view('pools.html')
def pools():
    """
    retrieves all pools
    """
    config = Kconfig()
    return {'title': 'Pools', 'client': config.client}


# REPOS

@app.route('/repostable')
@view('repostable.html')
def repostable():
    """
    retrieves all repos in table
    """
    config = Kconfig()
    repos = []
    repoinfo = config.list_repos()
    for repo in repoinfo:
        url = repoinfo[repo]
        repos.append([repo, url])
    return {'repos': repos}


@app.route('/repos')
@view('repos.html')
def repos():
    """

    :return:
    """
    config = Kconfig()
    return {'title': 'Repos', 'client': config.client}


@app.route('/repocreate')
@view('repocreate.html')
def repocreate():
    """
    repo form
    """
    config = Kconfig()
    return {'title': 'CreateRepo', 'client': config.client}

# PRODUCTS


@app.route('/productstable')
@view('productstable.html')
def productstable():
    """
    retrieves all products in table
    """
    baseconfig = Kbaseconfig()
    products = []
    for product in baseconfig.list_products():
        repo = product['repo']
        group = product.get('group', 'None')
        name = product['name']
        description = product.get('description', 'N/A')
        numvms = product.get('numvms', 'N/A')
        products.append([repo, group, name, description, numvms])
    return {'products': products}


@app.route('/products')
@view('products.html')
def products():
    """

    :return:
    """
    baseconfig = Kbaseconfig()
    return {'title': 'Products', 'client': baseconfig.client}


@app.route('/productcreate/<prod>')
@view('productcreate.html')
def productcreate(prod):
    """
    product form
    """
    config = Kbaseconfig()
    productinfo = config.info_product(prod, web=True)
    parameters = productinfo.get('parameters', {})
    description = parameters.get('description', '')
    info = parameters.get('info', '')
    return {'title': 'CreateProduct', 'client': config.client, 'product': prod, 'parameters': parameters,
            'description': description, 'info': info}


@app.route("/productaction", method='POST')
def productaction():
    """
    create product
    """
    config = Kconfig()
    if 'product' in request.forms:
        product = request.forms['product']
        action = request.forms['action']
        if action == 'create' and 'plan' in request.forms:
            plan = request.forms['plan']
            parameters = {}
            for p in request.forms:
                if p.startswith('parameters'):
                    value = request.forms[p]
                    key = p.replace('parameters[', '').replace(']', '')
                    parameters[key] = value
            if plan == '':
                plan = None
            result = config.create_product(product, plan=plan, overrides=parameters)
        else:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


# KUBE

@app.route('/kubegenericcreate')
@view('kubecreate.html')
def kubegenericcreate():
    """
    create generic kube
    """
    config = Kconfig()
    parameters = config.info_kube_generic(quiet=True, web=True)
    _type = 'generic'
    return {'title': 'CreateGenericKube', 'client': config.client, 'parameters': parameters, '_type': _type}


@app.route('/kubeopenshiftcreate')
@view('kubecreate.html')
def kubeopenshiftcreate():
    """
    create openshift kube
    """
    config = Kconfig()
    parameters = config.info_kube_openshift(quiet=True, web=True)
    _type = 'openshift'
    return {'title': 'CreateOpenshiftKube', 'client': config.client, 'parameters': parameters, '_type': _type}


@app.route("/kubeaction", method='POST')
def kubeaction():
    """
    create kube
    """
    config = Kconfig()
    if 'cluster' in request.forms:
        cluster = request.forms['cluster']
        _type = request.forms['type']
        action = request.forms['action']
        if action == 'create':
            parameters = {}
            for p in request.forms:
                if p.startswith('parameters'):
                    value = request.forms[p]
                    if value == 'None':
                        value = None
                    elif value.isdigit():
                        value = int(value)
                    elif value == 'False':
                        value = False
                    elif value == 'True':
                        value = True
                    key = p.replace('parameters[', '').replace(']', '')
                    parameters[key] = value
            del parameters['cluster']
            if _type == 'generic':
                thread = Thread(target=config.create_kube_generic, kwargs={'cluster': cluster,
                                                                           'overrides': parameters})
            elif _type == 'openshift':
                thread = Thread(target=config.create_kube_openshift, kwargs={'cluster': cluster,
                                                                             'overrides': parameters})
            thread.start()
            result = {'result': 'success'}
            response.status = 200
        else:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route('/hoststable')
@view('hoststable.html')
def hoststable():
    """
    retrieves all clients in table
    """
    baseconfig = Kbaseconfig()
    clients = []
    for client in sorted(baseconfig.clients):
        enabled = baseconfig.ini[client].get('enabled', True)
        _type = baseconfig.ini[client].get('type', 'kvm')
        if client == baseconfig.client:
            clients.append([client, _type, enabled, 'X'])
        else:
            clients.append([client, _type, enabled, ''])
    return {'clients': clients}


@app.route('/hosts')
@view('hosts.html')
def hosts():
    """
    retrieves all hosts
    """
    config = Kconfig()
    return {'title': 'Hosts', 'client': config.client}


@app.route('/planstable')
@view('planstable.html')
def planstable():
    """
    retrieves all plans in table
    """
    config = Kconfig()
    return {'plans': config.list_plans()}


@app.route('/plans')
@view('plans.html')
def plans():
    """

    :return:
    """
    config = Kconfig()
    return {'title': 'Plans', 'client': config.client}


@app.route('/kubestable')
@view('kubestable.html')
def kubestable():
    """
    retrieves all kubes in table
    """
    config = Kconfig()
    kubes = config.list_kubes()
    return {'kubes': kubes}


@app.route('/kubes')
@view('kubes.html')
def kubes():
    """

    :return:
    """
    config = Kconfig()
    return {'title': 'Kubes', 'client': config.client}


@app.route("/containeraction", method='POST')
def containeraction():
    """
    start/stop/delete container
    """
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        action = request.forms['action']
        if action not in ['start', 'stop', 'delete', 'create']:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
        else:
            if action == 'start':
                result = cont.start_container(name)
            elif action == 'stop':
                result = cont.stop_container(name)
            elif action == 'delete':
                result = cont.delete_container(name)
            elif action == 'create' and 'profile' in request.forms:
                profile = [prof for prof in config.list_containerprofiles() if prof[0] == request.forms['profile']][0]
                if name is None:
                    name = nameutils.get_random_name()
                image, nets, ports, volumes, cmd = profile[1:]
                result = cont.create_container(k, name=name, image=image, nets=nets, cmds=[cmd], ports=ports,
                                               volumes=volumes)
                result = cont.create_container(name, profile)
            response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route('/imagestable')
@view('imagestable.html')
def imagestable():
    """
    retrieves images in table
    """
    config = Kconfig()
    k = config.k
    images = k.volumes()
    return {'images': images}


@app.route('/images')
@view('images.html')
def images():
    """

    :return:
    """
    config = Kconfig()
    return {'title': 'Images', 'client': config.client}


@app.route('/imagecreate')
@view('imagecreate.html')
def imagecreate():
    """
    create image
    """
    config = Kconfig()
    k = config.k
    pools = k.list_pools()
    return {'title': 'CreateImage', 'pools': pools, 'images': sorted(IMAGES), 'client': config.client}


@app.route("/imageaction", method='POST')
def imageaction():
    """
    create/delete image
    """
    config = Kconfig()
    if 'pool' in request.forms:
        pool = request.forms['pool']
        action = request.forms['action']
        if action == 'create' and 'pool' in request.forms and 'image' in request.forms:
            pool = request.forms['pool']
            image = request.forms['image']
            url = request.forms['url']
            cmd = request.forms['cmd']
            if url == '':
                url = None
            if cmd == '':
                cmd = None
            result = config.handle_host(pool=pool, image=image, download=True, url=url, cmd=cmd)
            response.status = 200
        else:
            result = {'result': 'failure', 'reason': "Invalid Action"}
            response.status = 400
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route('/isostable')
@view('isostable.html')
def isostable():
    """
    retrieves isos in table
    """
    config = Kconfig()
    k = config.k
    isos = k.volumes(iso=True)
    return {'isos': isos}


@app.route('/isos')
@view('isos.html')
def isos():
    """

    :return:
    """
    config = Kconfig()
    return {'title': 'Isos', 'client': config.client}


@app.route('/containerprofilestable')
@view('containerprofilestable.html')
def containerprofilestable():
    """
    retrieves container profiles in table
    """
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_containerprofiles()
    return {'profiles': profiles}


@app.route('/containerprofiles')
@view('containerprofiles.html')
def containerprofiles():
    """
    retrieves all containerprofiles
    """
    baseconfig = Kbaseconfig()
    return {'title': 'ContainerProfiles', 'client': baseconfig.client}


@app.route('/vmconsole/<name>')
@view('console.html')
def vmconsole(name):
    """
    Get url for console
    """
    config = Kconfig()
    k = config.k
    password = ''
    scheme = 'ws://'
    if which('websockify') is None:
        response.status = 404
        return "missing websockify binary on server side"
    consoleurl = k.console(name, tunnel=config.tunnel, web=True)
    if consoleurl.startswith('spice') or consoleurl.startswith('vnc'):
        protocol = 'spice' if consoleurl.startswith('spice') else 'vnc'
        websocketport = get_free_port()
        host, port = consoleurl.replace('%s://' % protocol, '').split(':')
        websocketcommand = "websockify %s -vD --idle-timeout=30 %s:%s" % (websocketport, host, port)
        if config.type == 'ovirt':
            port, password = port.split('+')
            if protocol == 'spice':
                scheme = 'ws://'
                cert = os.path.expanduser('~/.kcli/websockify.pem')
                if not os.path.exists(cert):
                    with open(cert, 'w') as f:
                        f.write(WEBSOCKIFYCERT)
                websocketcommand = "websockify %s -vD --idle-timeout=30 --cert %s --ssl-target %s:%s" % (websocketport,
                                                                                                         cert, host,
                                                                                                         port)
            else:
                websocketcommand = "websockify %s -vD --idle-timeout=30 %s:%s" % (websocketport, host, port)
        os.popen(websocketcommand)
        sleep(5)
        return {'protocol': protocol, 'title': 'Vm console', 'port': websocketport, 'password': password,
                'scheme': scheme}
    elif consoleurl is not None:
        return redirect(consoleurl)
    else:
        response.status = 404
        return "consoleurl couldnt be evaluated"


def run():
    """

    """
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    run()
