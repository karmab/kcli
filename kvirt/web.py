#!/usr/bin/python
# coding=utf-8

from distutils.spawn import find_executable
from flask import Flask, render_template, request, jsonify, redirect, Response
from kvirt.config import Kconfig
from kvirt.common import print_info, get_free_port
from kvirt.baseconfig import Kbaseconfig
from kvirt.defaults import IMAGES, WEBSOCKIFYCERT
from kvirt import nameutils
import os
from time import sleep

app = Flask(__name__)
try:
    app.config.from_object('settings')
    config = app.config
except ImportError:
    config = {'PORT': os.environ.get('PORT', 9000)}

debug = config['DEBUG'] if 'DEBUG' in list(config) else True
port = int(config['PORT']) if 'PORT'in list(config) else 9000


# VMS


@app.route('/vmstable')
def vmstable():
    """
    retrieves all vms in table
    """
    config = Kconfig()
    k = config.k
    reportdir = config.reportdir
    vms = []
    for vm in k.list():
        name = vm['name']
        if os.path.exists('%s/%s.txt' % (reportdir, name)):
            if os.path.exists('%s/%s.running' % (reportdir, name)):
                vm['report'] = 'Running'
            else:
                vm['report'] = 'OK'
        vm['info'] = print_info(vm, output='plain', pretty=True)
        vms.append(vm)
    return render_template('vmstable.html', vms=vms)


@app.route("/")
@app.route('/vms')
def vms():
    """

    :return:
    """
    baseconfig = Kbaseconfig()
    return render_template('vms.html', title='Home', client=baseconfig.client)


@app.route('/vmcreate')
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
    return render_template('vmcreate.html', title='CreateVm', images=images,
                           parameters=parameters, client=config.client)


@app.route('/vmprofilestable')
def vmprofilestable():
    """
    retrieves vm profiles in table
    """
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_profiles()
    return render_template('vmprofilestable.html', profiles=profiles)


@app.route('/vmprofiles')
def vmprofiles():
    """

    :return:
    """
    baseconfig = Kbaseconfig()
    return render_template('vmprofiles.html', title='VmProfiles', client=baseconfig.client)


@app.route("/diskaction", methods=['POST'])
def diskaction():
    """
    add/delete disk to vm
    """
    config = Kconfig()
    k = config.k
    if 'action' in request.form:
        action = request.form['action']
        if action == 'add':
            name = request.form['name']
            size = int(request.form['size'])
            pool = request.form['pool']
            result = k.add_disk(name, size, pool)
        elif action == 'delete':
            name = request.form['name']
            diskname = request.form['disk']
            result = k.delete_disk(name, diskname)
        response = jsonify(result)
        print(response)
        response.status_code = 200
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
    return response


@app.route("/nicaction", methods=['POST'])
def nicaction():
    """
    add/delete nic to vm
    """
    config = Kconfig()
    k = config.k
    if 'action' in request.form:
        action = request.form['action']
        if action == 'add':
            name = request.form['name']
            network = request.form['network']
            result = k.add_nic(name, network)
        elif action == 'delete':
            name = request.form['name']
            nicname = request.form['nic']
            result = k.delete_nic(name, nicname)
        response = jsonify(result)
        print(response)
        response.status_code = 200
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
    return response


# CONTAINERS


@app.route('/containercreate')
def containercreate():
    """
    create container
    """
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_containerprofiles()
    return render_template('containercreate.html', title='CreateContainer', profiles=profiles, client=baseconfig.client)


# POOLS


@app.route('/poolcreate')
def poolcreate():
    """
    pool form
    """
    config = Kconfig()
    return render_template('poolcreate.html', title='CreatePool', client=config.client)


@app.route("/poolaction", methods=['POST'])
def poolaction():
    """
    create/delete pool
    """
    config = Kconfig()
    k = config.k
    if 'pool' in request.form:
        pool = request.form['pool']
        action = request.form['action']
        if action == 'create':
            path = request.form['path']
            pooltype = request.form['type']
            print(pool, path, pooltype)
            result = k.create_pool(name=pool, poolpath=path, pooltype=pooltype)
            print(result)
        elif action == 'delete':
            result = k.delete_pool(name=pool)
        else:
            result = "Nothing to do"
        response = jsonify(result)
        print(response)
        response.status_code = 200
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
    return response


# REPOS

@app.route("/repoaction", methods=['POST'])
def repoaction():
    """
    create/delete repo
    """
    config = Kconfig()
    if 'repo' in request.form:
        repo = request.form['repo']
        action = request.form['action']
        if action == 'create':
            url = request.form['url']
            print(repo, url)
            if url == '':
                failure = {'result': 'failure', 'reason': "Invalid Data"}
                response = jsonify(failure)
                response.status_code = 400
            else:
                result = config.create_repo(repo, url)
                print(result)
        elif action == 'update':
            result = config.update_repo(repo)
            print(result)
        elif action == 'delete':
            result = config.delete_repo(repo)
        else:
            result = "Nothing to do"
        response = jsonify(result)
        print(response)
        response.status_code = 200
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
    return response

# NETWORKS


@app.route('/networkcreate')
def networkcreate():
    """
    network form
    """
    config = Kconfig()
    return render_template('networkcreate.html', title='CreateNetwork', client=config.client)


@app.route("/networkaction", methods=['POST'])
def networkaction():
    """
    create/delete network
    """
    config = Kconfig()
    k = config.k
    if 'network' in request.form:
        network = request.form['network']
        action = request.form['action']
        if action == 'create':
            cidr = request.form['cidr']
            dhcp = bool(request.form['dhcp'])
            isolated = bool(request.form['isolated'])
            nat = not isolated
            print(network, cidr, dhcp, nat)
            result = k.create_network(name=network, cidr=cidr, dhcp=dhcp, nat=nat)
        elif action == 'delete':
            result = k.delete_network(name=network)
        else:
            result = "Nothing to do"
        response = jsonify(result)
        print(response)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
        return jsonify(failure)


# PLANS


@app.route('/plancreate')
def plancreate():
    """
    create plan
    """
    config = Kconfig()
    return render_template('plancreate.html', title='CreatePlan', client=config.client)


@app.route("/vmaction", methods=['POST'])
def vmaction():
    """
    start/stop/delete/create vm
    """
    config = Kconfig()
    k = config.k
    if 'name' in request.form:
        name = request.form['name']
        action = request.form['action']
        if action == 'start':
            result = k.start(name)
        elif action == 'stop':
            result = k.stop(name)
        elif action == 'delete':
            result = k.delete(name)
        elif action == 'create' and 'profile' in request.form:
            profile = request.form['profile']
            parameters = {}
            for p in request.form:
                if p.startswith('parameters'):
                    value = request.form[p]
                    key = p.replace('parameters[', '').replace(']', '')
                    parameters[key] = value
            parameters['nets'] = parameters['nets'].split(',')
            parameters['disks'] = [int(disk) for disk in parameters['disks'].split(',')]
            if name == '':
                name = nameutils.get_random_name()
            result = config.create_vm(name, profile, overrides=parameters)
        else:
            result = "Nothing to do"
        print(result)
        response = jsonify(result)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
        return jsonify(failure)


# HOSTS

@app.route("/hostaction", methods=['POST'])
def hostaction():
    """
    enable/disable/default host
    """
    baseconfig = Kbaseconfig()
    if 'name' in request.form:
        name = request.form['name']
        action = request.form['action']
        if action == 'enable':
            result = baseconfig.enable_host(name)
        elif action == 'disable':
            result = baseconfig.disable_host(name)
        elif action == 'switch':
            result = baseconfig.switch_host(name)
        else:
            result = "Nothing to do"
        response = jsonify(result)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
        return jsonify(failure)


@app.route("/snapshotaction", methods=['POST'])
def snapshotaction():
    """
    create/delete/revert snapshot
    """
    config = Kconfig()
    k = config.k
    if 'name' in request.form:
        name = request.form['name']
        action = request.form['action']
        if action == 'list':
            result = k.snapshot(None, name, listing=True)
        elif action == 'create':
            snapshot = request.form['snapshot']
            result = k.snapshot(snapshot, name)
        elif action == 'delete':
            snapshot = request.form['snapshot']
            result = k.snapshot(snapshot, name, delete=True)
        elif action == 'revert':
            snapshot = request.form['snapshot']
            name = request.form['name']
            result = k.snapshot(snapshot, name, revert=True)
        print(result)
        response = jsonify(result)
        print(response)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
        return jsonify(failure)


@app.route("/planaction", methods=['POST'])
def planaction():
    """
    start/stop/delete plan
    """
    config = Kconfig()
    if 'name' in request.form:
        plan = request.form['name']
        action = request.form['action']
        if action == 'start':
            result = config.plan(plan, start=True)
        elif action == 'stop':
            result = config.plan(plan, stop=True)
        elif action == 'delete':
            result = config.plan(plan, delete=True)
        elif action == 'create':
            print(request.form)
            url = request.form['url']
            if plan == '':
                plan = nameutils.get_random_name()
            result = config.plan(plan, url=url)
        else:
            result = "Nothing to do"
        print(result)
        response = jsonify(result)
        print(response)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400


@app.route("/report", methods=['POST'])
def report():
    """
    updatestatus
    """
    config = Kconfig()
    k = config.k
    reportdir = config.reportdir
    if 'name' in request.form and 'report' in request.form and 'status' in request.form:
        name = request.form['name']
        status = request.form['status']
        report = request.form['report']
    if not k.exists(name):
        return "KO"
    k.update_metadata(name, 'report', status)
    if not os.path.exists(reportdir):
        os.mkdir(reportdir)
    with open("%s/%s.txt" % (reportdir, name), 'w') as f:
        f.write(report)
    print("Name: %s Status: %s" % (name, status))
    if status == 'Running' and not os.path.exists("%s/%s.running" % (reportdir, name)):
        open("%s/%s.running" % (reportdir, name), 'a').close()
    if status == 'OK' and os.path.exists("%s/%s.running" % (reportdir, name)):
        os.remove("%s/%s.running" % (reportdir, name))
    return 'OK'


@app.route('/containerstable')
def containerstable():
    """
    retrieves all containers in table
    """
    from kvirt import dockerutils
    config = Kconfig()
    k = config.k
    containers = dockerutils.list_containers(k)
    return render_template('containerstable.html', containers=containers)


@app.route('/containers')
def containers():
    """
    retrieves all containers
    """
    config = Kconfig()
    return render_template('containers.html', title='Containers', client=config.client)


@app.route('/networkstable')
def networkstable():
    """
    retrieves all networks in table
    """
    config = Kconfig()
    k = config.k
    networks = k.list_networks()
    return render_template('networkstable.html', networks=networks)


@app.route('/networks')
def networks():
    """
    retrieves all networks
    """
    config = Kconfig()
    return render_template('networks.html', title='Networks', client=config.client)


@app.route('/poolstable')
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
    return render_template('poolstable.html', pools=pools)


@app.route('/pools')
def pools():
    """
    retrieves all pools
    """
    config = Kconfig()
    return render_template('pools.html', title='Pools', client=config.client)


# REPOS

@app.route('/repostable')
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
    return render_template('repostable.html', repos=repos)


@app.route('/repos')
def repos():
    """

    :return:
    """
    config = Kconfig()
    return render_template('repos.html', title='Repos', client=config.client)


@app.route('/repocreate')
def repocreate():
    """
    repo form
    """
    config = Kconfig()
    return render_template('repocreate.html', title='CreateRepo', client=config.client)

# PRODUCTS


@app.route('/productstable')
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
    return render_template('productstable.html', products=products)


@app.route('/products')
def products():
    """

    :return:
    """
    baseconfig = Kbaseconfig()
    return render_template('products.html', title='Products', client=baseconfig.client)


@app.route('/productcreate/<prod>')
def productcreate(prod):
    """
    product form
    """
    config = Kbaseconfig()
    info = config.info_product(prod, web=True)
    parameters = info['parameters']
    description = info['description']
    comments = info['comments']
    return render_template('productcreate.html', title='CreateProduct', client=config.client, product=prod,
                           parameters=parameters, description=description, comments=comments)


@app.route("/productaction", methods=['POST'])
def productaction():
    """
    create product
    """
    config = Kconfig()
    if 'product' in request.form:
        product = request.form['product']
        action = request.form['action']
        if action == 'create' and 'plan' in request.form:
            plan = request.form['plan']
            parameters = {}
            for p in request.form:
                if p.startswith('parameters'):
                    value = request.form[p]
                    key = p.replace('parameters[', '').replace(']', '')
                    parameters[key] = value
            if plan == '':
                plan = None
            result = config.create_product(product, plan=plan, overrides=parameters)
        else:
            result = "Nothing to do"
        print(result)
        response = jsonify(result)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400


@app.route('/hoststable')
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
    return render_template('hoststable.html', clients=clients)


@app.route('/hosts')
def hosts():
    """
    retrieves all hosts
    """
    config = Kconfig()
    return render_template('hosts.html', title='Hosts', client=config.client)


@app.route('/planstable')
def planstable():
    """
    retrieves all plans in table
    """
    config = Kconfig()
    return render_template('planstable.html', plans=config.list_plans())


@app.route('/plans')
def plans():
    """

    :return:
    """
    config = Kconfig()
    return render_template('plans.html', title='Plans', client=config.client)


@app.route("/containeraction", methods=['POST'])
def containeraction():
    """
    start/stop/delete container
    """
    from kvirt import dockerutils
    config = Kconfig()
    k = config.k
    if 'name' in request.form:
        name = request.form['name']
        action = request.form['action']
        if action == 'start':
            result = dockerutils.start_container(k, name)
        elif action == 'stop':
            result = dockerutils.stop_container(k, name)
        elif action == 'delete':
            result = dockerutils.delete_container(k, name)
        elif action == 'create' and 'profile' in request.form:
            profile = [prof for prof in config.list_containerprofiles() if prof[0] == request.form['profile']][0]
            if name is None:
                name = nameutils.get_random_name()
            image, nets, ports, volumes, cmd = profile[1:]
            result = dockerutils.create_container(k, name=name, image=image, nets=nets, cmd=cmd, ports=ports,
                                                  volumes=volumes)
            result = dockerutils.create_container(k, name, profile)
        else:
            result = "Nothing to do"
        print(result)
        response = jsonify(result)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response.status_code = 400
        return jsonify(failure)


@app.route('/imagestable')
def imagestable():
    """
    retrieves images in table
    """
    config = Kconfig()
    k = config.k
    images = k.volumes()
    return render_template('imagestable.html', images=images)


@app.route('/images')
def images():
    """

    :return:
    """
    config = Kconfig()
    return render_template('images.html', title='Images', client=config.client)


@app.route('/imagecreate')
def imagecreate():
    """
    create image
    """
    config = Kconfig()
    k = config.k
    pools = k.list_pools()
    return render_template('imagecreate.html', title='CreateImage', pools=pools, images=sorted(IMAGES),
                           client=config.client)


@app.route("/imageaction", methods=['POST'])
def imageaction():
    """
    create/delete image
    """
    config = Kconfig()
    if 'pool' in request.form:
        pool = request.form['pool']
        action = request.form['action']
        if action == 'create' and 'pool' in request.form and 'image' in request.form:
            pool = request.form['pool']
            image = request.form['image']
            url = request.form['url']
            cmd = request.form['cmd']
            if url == '':
                url = None
            if cmd == '':
                cmd = None
            result = config.handle_host(pool=pool, image=image, download=True, url=url, cmd=cmd)
        else:
            result = "Nothing to do"
        print(result)
        response = jsonify(result)
        response.status_code = 200
        return response
    else:
        failure = {'result': 'failure', 'reason': "Invalid Data"}
        response = jsonify(failure)
        response.status_code = 400
        return response


@app.route('/isostable')
def isostable():
    """
    retrieves isos in table
    """
    config = Kconfig()
    k = config.k
    isos = k.volumes(iso=True)
    return render_template('isostable.html', isos=isos)


@app.route('/isos')
def isos():
    """

    :return:
    """
    config = Kconfig()
    return render_template('isos.html', title='Isos', client=config.client)


@app.route('/containerprofilestable')
def containerprofilestable():
    """
    retrieves container profiles in table
    """
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_containerprofiles()
    return render_template('containerprofilestable.html', profiles=profiles)


@app.route('/containerprofiles')
def containerprofiles():
    """
    retrieves all containerprofiles
    """
    baseconfig = Kbaseconfig()
    return render_template('containerprofiles.html', title='ContainerProfiles', client=baseconfig.client)


@app.route('/vmconsole/<string:name>')
def vmconsole(name):
    """
    Get url for console
    """
    config = Kconfig()
    k = config.k
    password = ''
    scheme = 'ws://'
    if find_executable('websockify') is None:
        return Response(status=404)
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
        return render_template('%s.html' % protocol, title='Vm console', port=websocketport, password=password,
                               scheme=scheme)
    elif consoleurl is not None:
        return redirect(consoleurl)
    else:
        return Response(status=404)


def run():
    """

    """
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    run()
