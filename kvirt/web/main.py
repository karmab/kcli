#!/usr/bin/python
# coding=utf-8

from ast import literal_eval
import functools
from kvirt.bottle import Bottle, request, static_file, jinja2_view, response, redirect
from kvirt.config import Kconfig
from kvirt.common import print_info, get_free_port, get_parameters
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt.defaults import IMAGES, FAKECERT
from kvirt import nameutils
from kvirt import kind
from kvirt import microshift
from kvirt import k3s
from kvirt import kubeadm
from kvirt import hypershift
from kvirt import openshift
import os
from shutil import which
from time import sleep
from threading import Thread

app = Bottle()
config = {'PORT': os.environ.get('PORT', 9000)}
debug = config['DEBUG'] if 'DEBUG' in list(config) else True
port = int(config['PORT']) if 'PORT' in list(config) else 9000
global_pull_secret = os.environ.get('PULL_SECRET')

basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/web"
view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])


@app.route('/static/<filename:path>')
def server_static(filename):
    return static_file(filename, root=f'{basedir}/static')

# VMS


@app.route('/vmslist')
def vmslist():
    config = Kconfig()
    k = config.k
    vms = []
    for vm in k.list():
        vm['info'] = print_info(vm, output='plain', pretty=True)
        vms.append(vm)
    return {'vms': vms}


@app.route('/vmstable')
@view('vmstable.html')
def vmstable():
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
    baseconfig = Kbaseconfig()
    return {'title': 'Home', 'client': baseconfig.client}


@app.route('/vmcreateform')
@view('vmcreate.html')
def vmcreateform():
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


@app.route('/vmprofileslist')
def vmprofileslist():
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_profiles()
    return {'profiles': profiles}


@app.route('/vmprofilestable')
@view('vmprofilestable.html')
def vmprofilestable():
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_profiles()
    return {'profiles': profiles}


@app.route('/vmprofiles')
@view('vmprofiles.html')
def vmprofiles():
    baseconfig = Kbaseconfig()
    return {'title': 'VmProfiles', 'client': baseconfig.client}


@app.route("/diskcreate", method='POST')
def diskcreate():
    config = Kconfig()
    k = config.k
    name = request.forms['name']
    size = int(request.forms['size'])
    pool = request.forms['pool']
    result = k.add_disk(name, size, pool)
    return result


@app.route("/diskdelete", method='DELETE')
def diskdelete():
    config = Kconfig()
    k = config.k
    name = request.forms['name']
    diskname = request.forms['disk']
    result = k.delete_disk(name, diskname)
    response.status = 200
    # result = {'result': 'failure', 'reason': "Invalid Data"}
    # response.status = 400
    return result


@app.route("/niccreate", method='POST')
def niccreate():
    config = Kconfig()
    k = config.k
    name = request.forms['name']
    network = request.forms['network']
    result = k.add_nic(name, network)
    return result


@app.route("/nicdelete", method='DELETE')
def nicdelete():
    config = Kconfig()
    k = config.k
    name = request.forms['name']
    nicname = request.forms['nic']
    result = k.delete_nic(name, nicname)
    response.status = 200
    return result


# CONTAINERS


@app.route('/containercreateform')
@view('containercreate.html')
def containercreateform():
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_containerprofiles()
    return {'title': 'CreateContainer', 'profiles': profiles, 'client': baseconfig.client}


# POOLS


@app.route('/poolcreateform')
@view('poolcreate.html')
def poolcreateform():
    config = Kconfig()
    return {'title': 'CreatePool', 'client': config.client}


@app.route("/poolcreate", method='POST')
def poolcreate():
    config = Kconfig()
    k = config.k
    pool = request.forms['pool']
    path = request.forms['path']
    pooltype = request.forms['type']
    result = k.create_pool(name=pool, poolpath=path, pooltype=pooltype)
    return result


@app.route("/pooldelete", method='DELETE')
def pooldelete():
    config = Kconfig()
    k = config.k
    pool = request.forms['pool']
    result = k.delete_pool(name=pool)
    return result

# REPOS


@app.route("/repocreate", method='POST')
def repocreate():
    config = Kconfig()
    if 'repo' in request.forms:
        repo = request.forms['repo']
        url = request.forms['url']
        if url == '':
            result = {'result': 'failure', 'reason': "Invalid Data"}
            response.status = 400
        else:
            result = config.create_repo(repo, url)
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/repodelete", method='DELETE')
def repodelete():
    config = Kconfig()
    if 'repo' in request.forms:
        repo = request.forms['repo']
        result = config.delete_repo(repo)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/repoupdate", method='POST')
def repoupdate():
    config = Kconfig()
    if 'repo' in request.forms:
        repo = request.forms['repo']
        result = config.update_repo(repo)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result

# NETWORKS


@app.route('/networkcreateform')
@view('networkcreate.html')
def networkcreateform():
    config = Kconfig()
    return {'title': 'CreateNetwork', 'client': config.client}


@app.route("/networkcreate", method='POST')
def networkcreate():
    config = Kconfig()
    k = config.k
    if 'network' in request.forms:
        network = request.forms['network']
        cidr = request.forms['cidr']
        dhcp = bool(request.forms['dhcp'])
        isolated = bool(request.forms['isolated'])
        nat = not isolated
        result = k.create_network(name=network, cidr=cidr, dhcp=dhcp, nat=nat)
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/networkdelete", method='DELETE')
def networkdelete():
    config = Kconfig()
    k = config.k
    if 'network' in request.forms:
        network = request.forms['network']
        result = k.delete_network(name=network)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


# PLANS


@app.route('/plancreateform')
@view('plancreate.html')
def plancreateform():
    config = Kconfig()
    return {'title': 'CreatePlan', 'client': config.client}


@app.route("/vmstart", method='POST')
def vmstart():
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        result = k.start(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/vmstop", method='POST')
def vmstop():
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        result = k.stop(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/vmcreate", method='POST')
def vmcreate():
    config = Kconfig()
    if 'name' in request.forms:
        name = request.forms['name']
        profile = request.forms['profile']
        parameters = {}
        for p in request.forms:
            if p.startswith('parameters'):
                value = request.forms[p]
                key = p.replace('parameters[', '').replace(']', '')
                parameters[key] = value
        parameters['nets'] = parameters['nets'].split(',') if 'nets' in parameters else []
        parameters['disks'] = [int(disk) for disk in parameters['disks'].split(',')] if 'disks' in parameters else [10]
        if name == '':
            name = nameutils.get_random_name()
        result = config.create_vm(name, profile, overrides=parameters)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/vmdelete", method='DELETE')
def vmdelete():
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        result = k.delete(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


# HOSTS

@app.route("/hostenable", method='POST')
def hostenable():
    baseconfig = Kbaseconfig()
    if 'name' in request.forms:
        name = request.forms['name']
        result = baseconfig.enable_host(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/hostdisable", method='POST')
def hostdisable():
    baseconfig = Kbaseconfig()
    if 'name' in request.forms:
        name = request.forms['name']
        result = baseconfig.disable_host(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/hostswitch", method='POST')
def hostswitch():
    baseconfig = Kbaseconfig()
    if 'name' in request.forms:
        name = request.forms['name']
        result = baseconfig.switch_host(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/snapshotlist", method='POST')
def snapshotlist():
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        result = k.snapshot(None, name, listing=True)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/snapshotrevert", method='POST')
def snapshotrevert():
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        snapshot = request.forms['snapshot']
        name = request.forms['name']
        result = k.snapshot(snapshot, name, revert=True)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/snapshotdelete", method='DELETE')
def snapshotdelete():
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        snapshot = request.forms['snapshot']
        result = k.snapshot(snapshot, name, delete=True)
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/snapshotcreate", method='POST')
def snapshotcreate():
    config = Kconfig()
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        snapshot = request.forms['snapshot']
        name = request.forms['name']
        result = k.snapshot(snapshot, name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/planstart", method='POST')
def planstart():
    config = Kconfig()
    if 'name' in request.forms:
        plan = request.forms['name']
        result = config.start_plan(plan)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/planstop", method='POST')
def planstop():
    config = Kconfig()
    if 'name' in request.forms:
        plan = request.forms['name']
        result = config.stop_plan(plan)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/plandelete", method='DELETE')
def plandelete():
    config = Kconfig()
    if 'name' in request.forms:
        plan = request.forms['name']
        result = config.delete_plan(plan)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/plancreate", method='POST')
def plancreate():
    config = Kconfig()
    if 'name' in request.forms:
        plan = request.forms['name']
        url = request.forms['url']
        if plan == '':
            plan = nameutils.get_random_name()
        result = config.plan(plan, url=url)
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route('/containerslist')
def containerslist():
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    containers = cont.list_containers()
    return {'containers': containers}


@app.route('/containerstable')
@view('containerstable.html')
def containerstable():
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    containers = cont.list_containers()
    return {'containers': containers}


@app.route('/containers')
@view('containers.html')
def containers():
    config = Kconfig()
    return {'title': 'Containers', 'client': config.client}


@app.route('/networkslist')
def networkslist():
    config = Kconfig()
    k = config.k
    networks = k.list_networks()
    return {'networks': networks}


@app.route('/networkstable')
@view('networkstable.html')
def networkstable():
    config = Kconfig()
    k = config.k
    networks = k.list_networks()
    return {'networks': networks}


@app.route('/networks')
@view('networks.html')
def networks():
    config = Kconfig()
    return {'title': 'Networks', 'client': config.client}


@app.route('/poolslist')
def poolslist():
    config = Kconfig()
    k = config.k
    pools = []
    for pool in k.list_pools():
        poolpath = k.get_pool_path(pool)
        pools.append([pool, poolpath])
    return {'pools': pools}


@app.route('/poolstable')
@view('poolstable.html')
def poolstable():
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
    config = Kconfig()
    return {'title': 'Pools', 'client': config.client}


# REPOS


@app.route('/reposlist')
def reposlist():
    config = Kconfig()
    repos = []
    repoinfo = config.list_repos()
    for repo in repoinfo:
        url = repoinfo[repo]
        repos.append([repo, url])
    return {'repos': repos}


@app.route('/repostable')
@view('repostable.html')
def repostable():
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
    config = Kconfig()
    return {'title': 'Repos', 'client': config.client}


@app.route('/repocreateform')
@view('repocreate.html')
def repocreateform():
    config = Kconfig()
    return {'title': 'CreateRepo', 'client': config.client}

# PRODUCTS


@app.route('/productslist')
def productslist():
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


@app.route('/productstable')
@view('productstable.html')
def productstable():
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
    baseconfig = Kbaseconfig()
    return {'title': 'Products', 'client': baseconfig.client}


@app.route('/productcreateform/<prod>')
@view('productcreate.html')
def productcreateform(prod):
    config = Kbaseconfig()
    productinfo = config.info_product(prod, web=True)
    parameters = productinfo.get('parameters', {})
    description = parameters.get('description', '')
    info = parameters.get('info', '')
    return {'title': 'CreateProduct', 'client': config.client, 'product': prod, 'parameters': parameters,
            'description': description, 'info': info}


@app.route("/productcreate", method='POST')
def productcreate():
    config = Kconfig()
    if 'product' in request.forms:
        product = request.forms['product']
        if 'plan' in request.forms:
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

@app.route('/kubecreateform/<_type>')
@view('kubecreate.html')
def kubecreateform(_type):
    config = Kconfig()
    if _type == 'generic':
        plandir = os.path.dirname(kubeadm.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_default.yml'
    elif _type == 'k3s':
        plandir = os.path.dirname(k3s.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_default.yml'
    elif _type == 'kind':
        plandir = os.path.dirname(kind.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan_defauly.yml'
    elif _type == 'openshift':
        plandir = os.path.dirname(openshift.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_default.yml'
    elif _type == 'hypershift':
        plandir = os.path.dirname(hypershift.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan_default.yml'
    elif _type == 'microshift':
        plandir = os.path.dirname(microshift.create.__code__.co_filename)
        inputfile = f'{plandir}/kcli_plan_default.yml'
    else:
        result = {'result': 'failure', 'reason': f"Invalid kube type {_type}"}
        response.status = 400
        return result
    parameters = get_parameters(inputfile)
    del parameters['info']
    return {'title': 'CreateCluster{_type.capitalize()}', 'client': config.client, 'parameters': parameters,
            '_type': _type}


@app.route("/kubecreate", method='POST')
def kubecreate():
    config = Kconfig()
    _type = request.forms['type']
    parameters = {}
    for p in request.forms:
        if p.startswith('parameters'):
            value = request.forms[p]
            if value.isdigit():
                value = int(value)
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value == 'None':
                value = None
            elif value == '[]':
                value = []
            elif value.startswith('[') and value.endswith(']'):
                if '{' in value:
                    value = literal_eval(value)
                else:
                    value = value[1:-1].split(',')
                    for index, v in enumerate(value):
                        v = v.strip()
                        value[index] = v
            key = p.replace('parameters[', '').replace(']', '')
            parameters[key] = value
    cluster = parameters['cluster']
    if 'pull_secret' in parameters and parameters['pull_secret'] == 'openshift_pull.json':
        if global_pull_secret is not None and os.path.exists(global_pull_secret):
            parameters['pull_secret'] = global_pull_secret
        else:
            result = {'result': 'failure', 'reason': "Specify an absolute path to an existing pull secret"}
            response.status = 400
            return result
    if _type == 'generic':
        thread = Thread(target=config.create_kube_generic, kwargs={'cluster': cluster, 'overrides': parameters})
    elif _type == 'openshift':
        thread = Thread(target=config.create_kube_openshift, kwargs={'cluster': cluster, 'overrides': parameters})
    elif _type == 'k3s':
        thread = Thread(target=config.create_kube_k3s, kwargs={'cluster': cluster, 'overrides': parameters})
    elif _type == 'microshift':
        thread = Thread(target=config.create_kube_microshift, kwargs={'cluster': cluster, 'overrides': parameters})
    elif _type == 'hypershift':
        thread = Thread(target=config.create_kube_hypershift, kwargs={'cluster': cluster, 'overrides': parameters})
    elif _type == 'kind':
        thread = Thread(target=config.create_kube_kind, kwargs={'cluster': cluster, 'overrides': parameters})
    thread.start()
    result = {'result': 'success'}
    response.status = 200
    return result


@app.route('/hostslist')
def hostslist():
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


@app.route('/hoststable')
@view('hoststable.html')
def hoststable():
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
    config = Kconfig()
    return {'title': 'Hosts', 'client': config.client}


@app.route('/planslist')
def planslist():
    config = Kconfig()
    return {'plans': config.list_plans()}


@app.route('/planstable')
@view('planstable.html')
def planstable():
    config = Kconfig()
    return {'plans': config.list_plans()}


@app.route('/plans')
@view('plans.html')
def plans():
    config = Kconfig()
    return {'title': 'Plans', 'client': config.client}


@app.route('/kubeslist')
def kubeslist():
    config = Kconfig()
    kubes = config.list_kubes()
    return {'kubes': kubes}


@app.route('/kubestable')
@view('kubestable.html')
def kubestable():
    config = Kconfig()
    kubes = config.list_kubes()
    return {'kubes': kubes}


@app.route('/kubes')
@view('kubes.html')
def kubes():
    config = Kconfig()
    return {'title': 'Kubes', 'client': config.client}


@app.route("/containerstart", method='POST')
def containerstart():
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    if 'name' in request.forms:
        name = request.forms['name']
        result = cont.start_container(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/containerstop", method='POST')
def containerstop():
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    if 'name' in request.forms:
        name = request.forms['name']
        result = cont.stop_container(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/containerdelete", method='DELETE')
def containerdelete():
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    if 'name' in request.forms:
        name = request.forms['name']
        result = cont.delete_container(name)
        response.status = 200
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route("/containercreate", method='POST')
def containercreate():
    config = Kconfig()
    cont = Kcontainerconfig(config).cont
    k = config.k
    if 'name' in request.forms:
        name = request.forms['name']
        if 'profile' in request.forms:
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
    else:
        result = {'result': 'failure', 'reason': "Invalid Data"}
        response.status = 400
    return result


@app.route('/imageslist')
def imageslist():
    config = Kconfig()
    k = config.k
    images = k.volumes()
    return {'images': images}


@app.route('/imagestable')
@view('imagestable.html')
def imagestable():
    config = Kconfig()
    k = config.k
    images = k.volumes()
    return {'images': images}


@app.route('/images')
@view('images.html')
def images():
    config = Kconfig()
    return {'title': 'Images', 'client': config.client}


@app.route('/imagecreateform')
@view('imagecreate.html')
def imagecreateform():
    config = Kconfig()
    k = config.k
    pools = k.list_pools()
    return {'title': 'CreateImage', 'pools': pools, 'images': sorted(IMAGES), 'client': config.client}


@app.route("/imagecreate", method='POST')
def imagecreate():
    config = Kconfig()
    if 'pool' in request.forms:
        pool = request.forms['pool']
        if 'pool' in request.forms and 'image' in request.forms:
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


@app.route('/isoslist')
def isoslist():
    config = Kconfig()
    k = config.k
    isos = k.volumes(iso=True)
    return {'isos': isos}


@app.route('/isostable')
@view('isostable.html')
def isostable():
    config = Kconfig()
    k = config.k
    isos = k.volumes(iso=True)
    return {'isos': isos}


@app.route('/isos')
@view('isos.html')
def isos():
    config = Kconfig()
    return {'title': 'Isos', 'client': config.client}


@app.route('/containerprofileslist')
def containerprofileslist():
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_containerprofiles()
    return {'profiles': profiles}


@app.route('/containerprofilestable')
@view('containerprofilestable.html')
def containerprofilestable():
    baseconfig = Kbaseconfig()
    profiles = baseconfig.list_containerprofiles()
    return {'profiles': profiles}


@app.route('/containerprofiles')
@view('containerprofiles.html')
def containerprofiles():
    baseconfig = Kbaseconfig()
    return {'title': 'ContainerProfiles', 'client': baseconfig.client}


@app.route('/vmconsole/<name>')
@view('console.html')
def vmconsole(name):
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
                        f.write(FAKECERT)
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
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    run()
