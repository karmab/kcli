#!/usr/bin/python
# coding=utf-8

from ast import literal_eval
import functools
from kvirt.bottle import Bottle, request, static_file, jinja2_view, response, redirect
from kvirt.config import Kconfig
from kvirt.common import print_info, get_free_port, get_parameters, delete_lastvm
from kvirt.baseconfig import Kbaseconfig
from kvirt.containerconfig import Kcontainerconfig
from kvirt.defaults import IMAGES, FAKECERT
from kvirt import nameutils
from kvirt.cluster import microshift
from kvirt.cluster import k3s
from kvirt.cluster import kubeadm
from kvirt.cluster import hypershift
from kvirt.cluster import openshift
import os
from shutil import which
from time import sleep
from threading import Thread


class Kweb():

    def __init__(self, readonly=False):
        app = Bottle()

        app = Bottle()
        basedir = f"{os.path.dirname(Bottle.run.__code__.co_filename)}/web"
        view = functools.partial(jinja2_view, template_lookup=[f"{basedir}/templates"])

        @app.route('/static/<filename:path>')
        def server_static(filename):
            return static_file(filename, root=f'{basedir}/static')

        # VMS
        @app.route('/vms')
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
            return {'vms': vms, 'readonly': readonly}

        @app.route("/")
        @app.route('/vmsindex')
        @view('vms.html')
        def vms():
            baseconfig = Kbaseconfig()
            return {'title': 'Home', 'client': baseconfig.client, 'readonly': readonly}

        @app.route('/vmcreateform')
        @view('vmcreate.html')
        def vmcreateform():
            config = Kconfig()
            profiles = list(config.profiles.keys())
            profiles.extend([os.path.basename(v) for v in config.k.volumes()])
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
            return {'title': 'CreateVm', 'profiles': sorted(profiles), 'parameters': parameters,
                    'client': config.client}

        @app.route('/vmprofiles')
        def vmprofileslist():
            baseconfig = Kbaseconfig()
            profiles = baseconfig.list_profiles()
            return {'profiles': profiles}

        @app.route('/vmprofilestable')
        @view('vmprofilestable.html')
        def vmprofilestable():
            baseconfig = Kbaseconfig()
            profiles = baseconfig.list_profiles()
            return {'profiles': profiles, 'readonly': readonly}

        @app.route('/vmprofilesindex')
        @view('vmprofiles.html')
        def vmprofiles():
            baseconfig = Kbaseconfig()
            return {'title': 'VmProfiles', 'client': baseconfig.client}

        @app.route("/disks/<name>", method='POST')
        def diskcreate(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            size = int(data['size'])
            pool = data['pool']
            result = k.add_disk(name, size, pool)
            return result

        @app.route("/disks/<name>", method='DELETE')
        def diskdelete(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid json'
            config = Kconfig()
            k = config.k
            diskname = data['disk']
            result = k.delete_disk(name, diskname)
            response.status = 200
            # result = {'result': 'failure', 'reason': "Invalid Data"}
            # response.status = 400
            return result

        @app.route("/nics/<name>", method='POST')
        def niccreate(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            network = data['network']
            model = data.get('model', 'virtio')
            result = k.add_nic(name, network, model)
            return result

        @app.route("/nics/<name>", method='DELETE')
        def nicdelete(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            nicname = data['nic']
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

        @app.route("/pools", method='POST')
        def poolcreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            args = {'name': data['pool'], 'poolpath': data['path']}
            if 'type' in data:
                args['pooltype'] = data['type']
            result = k.create_pool(**args)
            return result

        @app.route("/pools/<pool>", method='DELETE')
        def pooldelete(pool):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            k = config.k
            result = k.delete_pool(name=pool)
            return result

        # REPOS

        @app.route("/repos", method='POST')
        def repocreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            if 'repo' in data:
                repo = data['repo']
                url = data['url']
                if url == '':
                    result = {'result': 'failure', 'reason': "Invalid Data"}
                    response.status = 400
                else:
                    result = config.create_repo(repo, url)
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route("/repos/<repo>", method='DELETE')
        def repodelete(repo):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            result = config.delete_repo(repo)
            response.status = 200
            return result

        @app.route("/repos/<repo>", method='PATCH')
        def repoupdate(repo):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            result = config.update_repo(repo)
            response.status = 200
            return result

        # NETWORKS

        @app.route('/networkcreateform')
        @view('networkcreate.html')
        def networkcreateform():
            config = Kconfig()
            return {'title': 'CreateNetwork', 'client': config.client}

        @app.route("/networks", method='POST')
        def networkcreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            if 'network' in data:
                network = data['network']
                cidr = data['cidr']
                dhcp = bool(data['dhcp'])
                isolated = bool(data['isolated'])
                nat = not isolated
                result = k.create_network(name=network, cidr=cidr, dhcp=dhcp, nat=nat)
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route("/networks/<network>", method='DELETE')
        def networkdelete(network):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            k = config.k
            result = k.delete_network(name=network)
            response.status = 200
            return result

        @app.route("/networks/<network>", method='UPDATE')
        def networkupdate(network):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            parameters = {'name': network}
            if 'dhcp' in data:
                parameters['dhcp'] = bool(data['dhcp'])
            if 'nat' in data:
                parameters['nat'] = bool(data['nat'])
            elif 'isolated' in data:
                parameters['nat'] = not bool(data['isolated'])
            if 'domain' in data:
                parameters['domain'] = data['domain']
            if 'plan' in data:
                parameters['plan'] = data['plan']
            if 'overrides' in data:
                parameters['overrides'] = data['overrides']
            config = Kconfig()
            k = config.k
            result = k.update_network(**parameters)
            response.status = 200
            return result

        # PLANS

        @app.route('/plancreateform')
        @view('plancreate.html')
        def plancreateform():
            config = Kconfig()
            return {'title': 'CreatePlan', 'client': config.client}

        @app.route("/vms/<name>/start", method='POST')
        def vmstart(name):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            k = config.k
            result = k.start(name)
            response.status = 200
            return result

        @app.route("/vms/<name>/stop", method='POST')
        def vmstop(name):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            k = config.k
            result = k.stop(name)
            response.status = 200
            return result

        @app.route("/vms", method='POST')
        def vmcreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            if 'name' in data:
                name = data['name']
                profile = data['profile']
                parameters = {}
                for p in data:
                    key = p
                    value = data[p]
                    if p.startswith('parameters'):
                        key = p.replace('parameters[', '').replace(']', '')
                    parameters[key] = value
                if 'nets' in parameters:
                    if isinstance(parameters['nets'], str):
                        parameters['nets'] = parameters['nets'].split(',')
                else:
                    parameters['nets'] = []
                if 'disks' in parameters:
                    if isinstance(parameters['disks'], str):
                        parameters['disks'] = parameters['disks'].split(',')
                else:
                    parameters['disks'] = [10]
                if name == '':
                    name = nameutils.get_random_name()
                result = config.create_vm(name, profile, overrides=parameters)
                response.status = 200
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route("/vms/<name>", method='GET')
        def vminfo(name):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            k = config.k
            result = k.info(name)
            response.status = 200
            return result

        @app.route("/vms/<name>", method='DELETE')
        def vmdelete(name):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            k = config.k
            data = request.json or request.forms
            snapshots = True if data is not None and 'snapshots' in data and bool(data['snapshots']) else False
            result = k.delete(name, snapshots=snapshots)
            delete_lastvm(name, config.client)
            response.status = 200
            return result

        @app.route("/vms/<name>", method='UPDATE')
        def vmupdate(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            parameters = {}
            for p in data:
                key = p
                value = data[p]
                if p.startswith('parameters'):
                    key = p.replace('parameters[', '').replace(']', '')
                parameters[key] = value
            if 'nets' in parameters:
                if isinstance(parameters, str):
                    parameters['nets'] = parameters['nets'].split(',')
            if 'disks' in parameters:
                if isinstance(parameters, str):
                    parameters['disks'] = parameters['disks'].split(',')
            result = config.update_vm(name, parameters)
            response.status = 200
            return result

        # HOSTS

        @app.route("/hosts/<name>/enable", method='POST')
        def hostenable(name):
            if readonly:
                response.status = 403
                return {}
            baseconfig = Kbaseconfig()
            result = baseconfig.enable_host(name)
            response.status = 200
            return result

        @app.route("/hosts/<name>/disable", method='POST')
        def hostdisable(name):
            if readonly:
                response.status = 403
                return {}
            baseconfig = Kbaseconfig()
            result = baseconfig.disable_host(name)
            response.status = 200
            return result

        @app.route("/hosts/<name>/switch", method='POST')
        def hostswitch(name):
            if readonly:
                response.status = 403
                return {}
            baseconfig = Kbaseconfig()
            result = baseconfig.switch_host(name)
            response.status = 200
            return result

        @app.route('/host')
        def hostinfo():
            config = Kconfig()
            k = config.k
            response.status = 200
            return k.info_host()

        @app.route("/snapshots/<name>")
        def snapshotlist(name):
            config = Kconfig()
            k = config.k
            snapshots = k.list_snapshots(name)
            result = {'snapshots': [snapshot for snapshot in snapshots]}
            response.status = 200
            return result

        @app.route("/snapshots/<name>/revert", method='POST')
        def snapshotrevert(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            if 'snapshot' in data:
                snapshot = data['snapshot']
                result = k.revert_snapshot(snapshot, name)
                response.status = 200
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route("/snapshots/<name>", method='DELETE')
        def snapshotdelete(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            if 'snapshot' in data:
                snapshot = data['snapshot']
                result = k.delete_snapshot(snapshot, name)
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route("/snapshots/<name>", method='POST')
        def snapshotcreate(name):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            k = config.k
            if 'snapshot' in data:
                snapshot = data['snapshot']
                result = k.create_snapshot(snapshot, name)
                response.status = 200
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route("/plan/<plan>/start", method='POST')
        def planstart(plan):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            result = config.start_plan(plan)
            response.status = 200
            return result

        @app.route("/plan/<plan>/stop", method='POST')
        def planstop(plan):
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            plan = data['name']
            result = config.stop_plan(plan)
            response.status = 200
            return result

        @app.route("/plans/<plan>", method='DELETE')
        def plandelete(plan):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            result = config.delete_plan(plan)
            response.status = 200
            return result

        @app.route("/plans", method='POST')
        def plancreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            if 'name' in data:
                plan = data['name']
                url = data['url']
                if plan == '':
                    plan = nameutils.get_random_name()
                result = config.plan(plan, url=url)
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route('/containers')
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
            return {'containers': containers, 'readonly': readonly}

        @app.route('/containersindex')
        @view('containers.html')
        def containersindex():
            config = Kconfig()
            return {'title': 'Containers', 'client': config.client}

        @app.route('/networks')
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
            return {'networks': networks, 'readonly': readonly}

        @app.route('/networksindex')
        @view('networks.html')
        def networks():
            config = Kconfig()
            return {'title': 'Networks', 'client': config.client}

        @app.route('/pools')
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
            return {'pools': pools, 'readonly': readonly}

        @app.route('/poolsindex')
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
            return {'repos': repos, 'readonly': readonly}

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

        @app.route('/products')
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
            return {'products': products, 'readonly': readonly}

        @app.route('/productsindex')
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

        @app.route("/products", method='POST')
        def productcreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            if 'product' in data:
                product = data['product']
                if 'plan' in data:
                    plan = data['plan']
                    parameters = {}
                    for p in data:
                        key = p
                        value = data[p]
                        if p.startswith('parameters'):
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

        @app.route("/kubes", method='POST')
        def kubecreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            _type = data.get('type') or data.get('kubetype')
            parameters = {}
            for key in data:
                value = data[key]
                if not isinstance(value, str):
                    parameters[key] = value
                    continue
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
                if key.startswith('parameters'):
                    key = key.replace('parameters[', '').replace(']', '')
                parameters[key] = value
            cluster = parameters['cluster']
            if 'pull_secret' in parameters and parameters['pull_secret'] == 'openshift_pull.json':
                if self.pull_secret is not None and os.path.exists(self.pull_secret):
                    parameters['pull_secret'] = self.pull_secret
                else:
                    result = {'result': 'failure', 'reason': "Specify an absolute path to an existing pull secret"}
                    response.status = 400
                    return result
            if _type in ['openshift', 'hypershift']:
                parameters['sno_wait'] = True
                parameters['async'] = True
            if _type == 'generic':
                thread = Thread(target=config.create_kube_generic, kwargs={'cluster': cluster, 'overrides': parameters})
            elif _type == 'openshift':
                thread = Thread(target=config.create_kube_openshift, kwargs={'cluster': cluster,
                                                                             'overrides': parameters})
            elif _type == 'k3s':
                thread = Thread(target=config.create_kube_k3s, kwargs={'cluster': cluster, 'overrides': parameters})
            elif _type == 'microshift':
                thread = Thread(target=config.create_kube_microshift, kwargs={'cluster': cluster,
                                                                              'overrides': parameters})
            elif _type == 'hypershift':
                thread = Thread(target=config.create_kube_hypershift, kwargs={'cluster': cluster,
                                                                              'overrides': parameters})
            thread.start()
            result = {'result': 'success'}
            response.status = 200
            return result

        @app.route("/kubes/<kube>", method='DELETE')
        def kubedelete(kube):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            result = config.delete_kube(kube)
            response.status = 200
            return result

        @app.route('/hosts')
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
            return {'clients': clients, 'readonly': readonly}

        @app.route('/hostsindex')
        @view('hosts.html')
        def hosts():
            config = Kconfig()
            return {'title': 'Hosts', 'client': config.client}

        @app.route('/plans')
        def planslist():
            config = Kconfig()
            return {'plans': config.list_plans()}

        @app.route('/planstable')
        @view('planstable.html')
        def planstable():
            config = Kconfig()
            return {'plans': config.list_plans(), 'readonly': readonly}

        @app.route('/plansindex')
        @view('plans.html')
        def plans():
            config = Kconfig()
            return {'title': 'Plans', 'client': config.client}

        @app.route('/kubes')
        def kubeslist():
            config = Kconfig()
            kubes = config.list_kubes()
            return {'kubes': kubes}

        @app.route('/kubestable')
        @view('kubestable.html')
        def kubestable():
            config = Kconfig()
            kubes = config.list_kubes()
            return {'kubes': kubes, 'readonly': readonly}

        @app.route('/kubes/<kube>')
        def kubeinfo(kube):
            config = Kconfig()
            data = {}
            kubes = config.list_kubes()
            if kube in kubes:
                openshift = kubes[kube]['type'] == 'openshift'
                data = config.info_specific_kube(kube, openshift=openshift)
            return data

        @app.route('/kubeconfig/kubeconfig.<kube>')
        def kubeconfigfile(kube):
            kubeconfig = os.path.expanduser(f'~/.kcli/clusters/{kube}/auth/kubeconfig')
            if os.path.exists(kubeconfig):
                return static_file('kubeconfig', root=os.path.dirname(kubeconfig), mimetype='application/octet-stream')
            else:
                response.status = 404
                return {}

        @app.route('/kubes/<kube>/kubeconfig')
        def kubeconfig(kube):
            kubeconfig = os.path.expanduser(f'~/.kcli/clusters/{kube}/auth/kubeconfig')
            if os.path.exists(kubeconfig):
                return open(kubeconfig).read()
            else:
                response.status = 404
                return {}

        @app.route('/kubeinfo/<kube>')
        @view('kubeinfo.html')
        def kubeinfoview(kube):
            config = Kconfig()
            data = {'kube': kube, 'readonly': readonly}
            if kube in config.list_kubes():
                data.update(config.info_specific_kube(kube))
            return data

        @app.route('/kubesindex')
        @view('kubes.html')
        def kubes():
            config = Kconfig()
            return {'title': 'Kubes', 'client': config.client}

        @app.route('/kubeprofiles/<profile>')
        def kubeprofileinfo(profile):
            baseconfig = Kbaseconfig()
            if profile not in baseconfig.clusterprofiles:
                response.status = 404
                result = {'result': 'failure', 'reason': "Clusterprofile {profile} not found"}
                return result
            else:
                return baseconfig.clusterprofiles[profile]

        @app.route('/kubeprofiles')
        def kubeprofileslist():
            baseconfig = Kbaseconfig()
            profiles = baseconfig.list_clusterprofiles()
            return {'profiles': profiles}

        @app.route('/kubeprofilestable')
        @view('kubeprofilestable.html')
        def kubeprofilestable():
            baseconfig = Kbaseconfig()
            profiles = baseconfig.list_clusterprofiles()
            return {'profiles': profiles, 'readonly': readonly}

        @app.route('/kubeprofilesindex')
        @view('kubeprofiles.html')
        def kubeprofiles():
            baseconfig = Kbaseconfig()
            return {'title': 'KubeProfiles', 'client': baseconfig.client}

        @app.route("/container/<name>/start", method='POST')
        def containerstart(name):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            cont = Kcontainerconfig(config).cont
            result = cont.start_container(name)
            response.status = 200
            return result

        @app.route("/containers/<name>/stop", method='POST')
        def containerstop(name):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            cont = Kcontainerconfig(config).cont
            result = cont.stop_container(name)
            response.status = 200
            return result

        @app.route("/container/<name>", method='DELETE')
        def containerdelete(name):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            cont = Kcontainerconfig(config).cont
            result = cont.delete_container(name)
            response.status = 200
            return result

        @app.route("/containers", method='POST')
        def containercreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid data'
            config = Kconfig()
            cont = Kcontainerconfig(config).cont
            k = config.k
            if 'name' in data:
                name = data['name']
                if 'profile' in data:
                    profile = [prof for prof in config.list_containerprofiles() if prof[0] == data['profile']][0]
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

        @app.route('/images')
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
            return {'images': images, 'readonly': readonly}

        @app.route('/imagesindex')
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

        @app.route("/images", method='POST')
        def imagecreate():
            if readonly:
                response.status = 403
                return {}
            data = request.json or request.forms
            if data is None:
                response.status = 400
                return 'Invalid json'
            config = Kconfig()
            if 'pool' in data:
                pool = data['pool']
                if 'pool' in data and 'image' in data:
                    pool = data['pool']
                    image = data['image']
                    url = data['url']
                    cmd = data.get('cmd')
                    if url == '':
                        url = None
                    if cmd == '':
                        cmd = None
                    result = config.download_image(pool=pool, image=image, url=url, cmd=cmd)
                    response.status = 200
                else:
                    result = {'result': 'failure', 'reason': "Invalid Action"}
                    response.status = 400
            else:
                result = {'result': 'failure', 'reason': "Invalid Data"}
                response.status = 400
            return result

        @app.route("/images/<image>", method='DELETE')
        def imagedelete(image):
            if readonly:
                response.status = 403
                return {}
            config = Kconfig()
            k = config.k
            data = request.json or request.forms
            pool = data.get('pool') or config.pool
            result = k.delete_image(image, pool=pool)
            response.status = 200
            return result

        @app.route('/isos')
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
            return {'isos': isos, 'readonly': readonly}

        @app.route('/isosindex')
        @view('isos.html')
        def isos():
            config = Kconfig()
            return {'title': 'Isos', 'client': config.client}

        @app.route('/containerprofiles')
        def containerprofiles():
            baseconfig = Kbaseconfig()
            profiles = baseconfig.list_containerprofiles()
            return {'profiles': profiles}

        @app.route('/containerprofilestable')
        @view('containerprofilestable.html')
        def containerprofilestable():
            baseconfig = Kbaseconfig()
            profiles = baseconfig.list_containerprofiles()
            return {'profiles': profiles, 'readonly': readonly}

        @app.route('/containerprofilesindex')
        @view('containerprofiles.html')
        def containerprofilesindexl():
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
                        websocketcommand = f"websockify {websocketport} -vD --idle-timeout=30"
                        websocketcommand += f" --cert {cert} --ssl-target {host}:{port}"
                    else:
                        websocketcommand = "websockify {websocketport} -vD --idle-timeout=30 {host}:{port}"
                os.popen(websocketcommand)
                sleep(5)
                return {'protocol': protocol, 'title': 'Vm console', 'port': websocketport, 'password': password,
                        'scheme': scheme}
            elif consoleurl is not None:
                return redirect(consoleurl)
            else:
                response.status = 404
                return "consoleurl couldnt be evaluated"

        self.app = app
        self.port = os.environ.get('KWEB_PORT', 8000)
        self.debug = 'KWEB_DEBUG' in os.environ
        self.ipv6 = 'KWEB_IPV6' in os.environ
        self.host = '::' if self.ipv6 else '0.0.0.0'
        self.pull_secret = os.environ.get('PULL_SECRET')

    def run(self):
        data = {'host': self.host, 'port': self.port, 'debug': self.debug}
        self.app.run(**data)
