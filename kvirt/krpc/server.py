import ast
import grpc
from concurrent import futures
import time
import kvirt.krpc.kcli_pb2 as kcli_pb2
import kvirt.krpc.kcli_pb2_grpc as kcli_pb2_grpc

from kvirt.config import Kconfig, Kbaseconfig, Kcontainerconfig
from kvirt import common, nameutils
from kvirt.common import pprint, error
from kvirt import version
from kvirt.defaults import VERSION
import os
import sys
import yaml


class KcliServicer(kcli_pb2_grpc.KcliServicer):

    def get_lastvm(self, request, context):
        print("Handling get_lastvm for:\n%s" % request)
        config = Kconfig()
        name = common.get_lastvm(config.client if request.client == '' else request.client)
        response = kcli_pb2.vm(name=name)
        return response

    def create_network(self, request, context):
        print("Handling create_network call for:\n%s" % request)
        config = Kconfig()
        k = config.k
        overrides = ast.literal_eval(request.overrides) if request.overrides != '' else {}
        result = k.create_network(name=request.network, cidr=request.cidr, dhcp=request.dhcp, nat=request.nat,
                                  domain=request.domain, overrides=overrides)
        response = kcli_pb2.result(**result)
        return response

    def create_pool(self, request, context):
        print("Handling create_pool call for:\n%s" % request)
        config = Kconfig()
        k = config.k
        result = k.create_pool(name=request.pool, poolpath=request.path, pooltype=request.type,
                               thinpool=request.thinpool)
        response = kcli_pb2.result(**result)
        return response

    def console(self, request, context):
        print("Handling console call for:\n%s" % request)
        config = Kconfig()
        tunnel = config.tunnel
        cmd = config.k.console(request.name, tunnel=tunnel, web=True)
        response = kcli_pb2.cmd(cmd=cmd)
        return response

    def serial_console(self, request, context):
        print("Handling serial_console call for:\n%s" % request)
        config = Kconfig()
        cmd = config.k.serialconsole(request.name, web=True)
        response = kcli_pb2.cmd(cmd=cmd)
        return response

    def delete(self, request, context):
        print("Handling delete call for:\n%s" % request)
        config = Kconfig()
        result = config.k.delete(request.name, snapshots=request.snapshots)
        response = kcli_pb2.result(**result)
        common.set_lastvm(request.name, config.client, delete=True)
        return response

    def delete_image(self, request, context):
        print("Handling delete_image call for:\n%s" % request)
        config = Kconfig()
        result = config.k.delete_image(request.image)
        response = kcli_pb2.result(**result)
        return response

    def delete_network(self, request, context):
        print("Handling delete_network call for:\n%s" % request)
        config = Kconfig()
        result = config.k.delete_network(request.network)
        response = kcli_pb2.result(**result)
        return response

    def delete_pool(self, request, context):
        print("Handing delete_pool call for:\n%s" % request)
        config = Kconfig()
        k = config.k
        result = k.delete_pool(name=request.pool, full=request.full)
        response = kcli_pb2.result(**result)
        return response

    def info(self, request, context):
        print("Handling info call for:\n%s" % request)
        config = Kconfig()
        result = config.k.info(request.name, debug=request.debug)
        response = kcli_pb2.vminfo(**result)
        return response

    def restart(self, request, context):
        print("Handling restart call for:\n%s" % request)
        config = Kconfig()
        result = config.k.restart(request.name)
        response = kcli_pb2.result(**result)
        return response

    def start(self, request, context):
        print("Handling start call for:\n%s" % request)
        config = Kconfig()
        result = config.k.start(request.name)
        response = kcli_pb2.result(**result)
        return response

    def scp(self, request, context):
        print("Handling scp call for:\n%s" % request)
        name = request.name
        recursive = request.recursive
        source = request.source
        destination = request.destination
        download = request.download
        user = request.user if request.user != '' else None
        config = Kconfig()
        k = config.k
        tunnel = config.tunnel
        tunnelhost = config.tunnelhost
        tunnelport = config.tunnelport
        tunneluser = config.tunneluser
        if tunnel and tunnelhost is None:
            error("Tunnel requested but invalid tunnelhost")
            sys.exit(1)
        insecure = config.insecure
        u, ip, vmport = common._ssh_credentials(k, name)
        if ip is None:
            return
        if user is None:
            user = config.vmuser if config.vmuser is not None else u
        if vmport is None and config.vmport is not None:
            vmport = config.vmport
        scpcommand = common.scp(name, ip=ip, user=user, source=source, destination=destination,
                                tunnel=tunnel, tunnelhost=tunnelhost, tunnelport=tunnelport, tunneluser=tunneluser,
                                download=download, recursive=recursive, insecure=insecure, vmport=vmport)
        response = kcli_pb2.sshcmd(sshcmd=scpcommand)
        return response

    def ssh(self, request, context):
        print("Handling ssh call for:\n%s" % request)
        config = Kconfig()
        k = config.k
        name = request.name
        l = request.l if request.l != '' else None
        r = request.r if request.r != '' else None
        X = request.X
        Y = request.Y
        D = request.D if request.D != '' else None
        user = request.user if request.user != '' else None
        cmd = request.cmd if request.cmd != '' else None
        tunnel = config.tunnel
        tunnelhost = config.tunnelhost
        if tunnel and tunnelhost is None:
            error("Tunnel requested but invalid tunnelhost")
            sys.exit(1)
        tunnelport = config.tunnelport
        tunneluser = config.tunneluser
        insecure = config.insecure
        if '@' in name and len(name.split('@')) == 2:
            user = name.split('@')[0]
            name = name.split('@')[1]
        if os.path.exists("/i_am_a_container") and not os.path.exists("/root/.kcli/config.yml")\
                and not os.path.exists("/root/.ssh/config"):
            insecure = True
        u, ip, vmport = common._ssh_credentials(k, name)
        if ip is None:
            return kcli_pb2.sshcmd(sshcmd='')
        if user is None:
            user = config.vmuser if config.vmuser is not None else u
        if vmport is None and config.vmport is not None:
            vmport = config.vmport
        sshcmd = common.ssh(name, ip=ip, user=user, local=l, remote=r, tunnel=tunnel, tunnelhost=tunnelhost,
                            tunnelport=tunnelport, tunneluser=tunneluser, insecure=insecure, cmd=cmd, X=X, Y=Y, D=D,
                            vmport=vmport)
        response = kcli_pb2.sshcmd(sshcmd=sshcmd)
        return response

    def stop(self, request, context):
        print("Handling stop call for:\n%s" % request)
        config = Kconfig()
        result = config.k.stop(request.name)
        response = kcli_pb2.result(**result)
        return response

    def list(self, request, context):
        print("Handling list call")
        config = Kconfig()
        vmlist = config.k.list()
        response = kcli_pb2.vmlist(vms=[kcli_pb2.vminfo(**x) for x in vmlist])
        return response

    def list_disks(self, request, context):
        print("Handling list_disks call")
        config = Kconfig()
        k = config.k
        disks = k.list_disks()
        diskslist = []
        for disk in disks:
            diskslist.append({'disk': disk, 'pool': disks[disk]['pool'], 'path': disks[disk]['path']})
        response = kcli_pb2.diskslist(disks=[kcli_pb2.disk(**d) for d in diskslist])
        return response

    def list_images(self, request, context):
        print("Handling list_images call")
        config = Kconfig()
        response = kcli_pb2.imageslist(images=config.k.volumes())
        return response

    def list_isos(self, request, context):
        print("Handling list call")
        config = Kconfig()
        response = kcli_pb2.isoslist(isos=config.k.volumes(iso=True))
        return response

    def list_networks(self, request, context):
        print("Handling list_networks call")
        config = Kconfig()
        k = config.k
        networks = k.list_networks()
        networkslist = []
        for network in networks:
            new_network = networks[network]
            new_network['network'] = network
            new_network['cidr'] = str(networks[network]['cidr'])
            new_network['dhcp'] = str(networks[network]['dhcp'])
            networkslist.append(kcli_pb2.network(**new_network))
        response = kcli_pb2.networkslist(networks=networkslist)
        return response

    def list_subnets(self, request, context):
        print("Handling list_subnets call")
        config = Kconfig()
        k = config.k
        subnets = k.list_subnets()
        subnetslist = []
        for subnet in subnets:
            new_subnet = subnets[subnet]
            new_subnet['subnet'] = subnet
            subnetslist.append(kcli_pb2.subnet(**new_subnet))
        response = kcli_pb2.subnetslist(subnets=subnetslist)
        return response

    def list_pools(self, request, context):
        print("Handling list_pool call")
        config = Kconfig()
        k = config.k
        response = kcli_pb2.poolslist(pools=[{'pool': pool, 'path': k.get_pool_path(pool)} for pool in k.list_pools()])
        return response

    def list_flavors(self, request, context):
        print("Handling list_flavors call")
        config = Kconfig()
        k = config.k
        flavorslist = []
        for flavor in k.flavors():
            flavorname, numcpus, memory = flavor
            flavorslist.append({'flavor': flavorname, 'numcpus': numcpus, 'memory': memory})
        response = kcli_pb2.flavorslist(flavors=[kcli_pb2.flavor(**f) for f in flavorslist])
        return response


class KconfigServicer(kcli_pb2_grpc.KconfigServicer):

    def create_vm(self, request, context):
        print("Handling create_vm call for:\n%s" % request)
        config = Kconfig()
        overrides = ast.literal_eval(request.overrides) if request.overrides != '' else {}
        profile = request.profile
        customprofile = ast.literal_eval(request.customprofile) if request.customprofile != '' else {}
        name = request.name
        if name == '':
            name = nameutils.get_random_name()
            if config.type in ['gcp', 'kubevirt']:
                name = name.replace('_', '-')
            if config.type != 'aws':
                pprint("Using %s as name of the vm" % name)
        if request.image != '':
            if request.image in config.profiles:
                pprint("Using %s as profile" % request.image)
            profile = request.image
        elif profile is not None:
            if profile.endswith('.yml'):
                profilefile = profile
                profile = None
                if not os.path.exists(profilefile):
                    error("Missing profile file %s" % profilefile)
                    result = {'result': 'failure', 'reason': "Missing profile file %s" % profilefile}
                    response = kcli_pb2.result(**result)
                    return response
                else:
                    with open(profilefile, 'r') as entries:
                        entries = yaml.safe_load(entries)
                        entrieskeys = list(entries.keys())
                        if len(entrieskeys) == 1:
                            profile = entrieskeys[0]
                            customprofile = entries[profile]
                            pprint("Using data from %s as profile" % profilefile)
                        else:
                            error("Cant' parse %s as profile file" % profilefile)
                            result = {'result': 'failure', 'reason': "Missing profile file %s" % profilefile}
                            response = kcli_pb2.result(**result)
                            return response
        elif overrides:
            profile = 'kvirt'
            config.profiles[profile] = {}
        else:
            error("You need to either provide a profile, an image or some parameters")
            result = {'result': 'failure',
                      'reason': "You need to either provide a profile, an image or some parameters"}
            response = kcli_pb2.result(**result)
            response = kcli_pb2.result(**result)
            return response
        if request.vmfiles:
            for _fil in request.vmfiles:
                origin = _fil.origin
                content = _fil.content
                with open(origin, 'w') as f:
                    f.write(content)
        if request.ignitionfile != '':
            with open("%s.ign" % name, 'w') as f:
                f.write(request.ignitionfile)
        result = config.create_vm(name, profile, overrides=overrides,
                                  customprofile=customprofile)
        result['vm'] = name
        response = kcli_pb2.result(**result)
        return response

    def get_version(self, request, context):
        print("Handling get_version call")
        versiondir = os.path.dirname(version.__file__)
        git_version = open('%s/git' % versiondir).read().rstrip() if os.path.exists('%s/git' % versiondir) else 'N/A'
        ver = {'version': VERSION, 'git_version': git_version}
        response = kcli_pb2.version(**ver)
        return response

    def create_host(self, request, context):
        print("Handling create_host call")
        data = {}
        if request.client != '':
            data['client'] = request.client
        if request.type != '':
            data['_type'] = request.type
        if request.current != '':
            data['current'] = request.current
        if request.name != '':
            data['name'] = request.name
        if request.access_key_id != '':
            data['access_key_id'] = request.access_key_id
        if request.access_key_secret != '':
            data['access_key_secret'] = request.access_key_secret
        if request.region != '':
            data['region'] = request.region
        if request.keypair != '':
            data['keypair'] = request.keypair
        if request.host != '':
            data['host'] = request.host
        if request.port != '':
            data['port'] = request.port
        if request.user != '':
            data['user'] = request.user
        if request.protocol != '':
            data['protocol'] = request.protocol
        if request.url != '':
            data['url'] = request.url
        if request.pool != '':
            data['pool'] = request.pool
        if request.datacenter != '':
            data['datacenter'] = request.datacenter
        if request.ca_file != '':
            data['ca_file'] = request.ca_file
        if request.cluster != '':
            data['cluster'] = request.cluster
        if request.org != '':
            data['org'] = request.org
        if request.password != '':
            data['password'] = request.password
        if request.credentials != '':
            data['credentials'] = request.credentials
        if request.project != '':
            data['project'] = request.project
        if request.zone != '':
            data['zone'] = request.zone
        if request.domain != '':
            data['domain'] = request.domain
        if request.auth_url != '':
            data['auth_url'] = request.auth_url
        if request.token != '':
            data['token'] = request.token
        if request.type == 'kubevirt':
            data['multus'] = request.multus
            data['cdi'] = request.cdi
        common.create_host(data)
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def get_config(self, request, context):
        print("Handling get_config call")
        config = Kconfig()
        configinfo = {'client': config.client, 'extraclients': [c for c in config.extraclients]}
        response = kcli_pb2.config(**configinfo)
        return response

    def delete_host(self, request, context):
        print("Handling delete_host call for:\n%s" % request)
        common.delete_host(request.client)
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def delete_container(self, request, context):
        print("Handling delete_container call for:\n%s" % request)
        config = Kconfig()
        cont = Kcontainerconfig(config).cont
        result = cont.delete_container(request.container)
        response = kcli_pb2.result(**result)
        return response

    def delete_plan(self, request, context):
        print("Handling delete_plan call for:\n%s" % request)
        config = Kconfig()
        result = config.plan(request.plan, delete=True)
        response = kcli_pb2.result(**result)
        return response

    def delete_profile(self, request, context):
        print("Handing delete_profile call for:\n%s" % request)
        baseconfig = Kconfig()
        result = baseconfig.delete_profile(request.name)
        response = kcli_pb2.result(**result)
        return response

    def delete_repo(self, request, context):
        print("Handing delete_profile call for:\n%s" % request)
        baseconfig = Kconfig()
        result = baseconfig.delete_repo(request.repo)
        response = kcli_pb2.result(**result)
        return response

    def delete_kube(self, request, context):
        print("Handling delete_kube call for:\n%s" % request)
        config = Kconfig()
        config.delete_kube(request.kube, overrides={})
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def delete_lb(self, request, context):
        print("Handling delete_lb call for:\n%s" % request)
        config = Kconfig()
        config.handle_loadbalancer(request.lb, delete=True)
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def list_containers(self, request, context):
        print("Handling list_containers call")
        config = Kconfig()
        # cont = Kcontainerconfig(config, client=args.containerclient).cont
        cont = Kcontainerconfig(config).cont
        containers = []
        for container in cont.list_containers():
            newcontainer = {}
            newcontainer['container'] = container[0]
            newcontainer['status'] = container[1]
            newcontainer['image'] = container[2]
            newcontainer['plan'] = container[3]
            newcontainer['command'] = container[4]
            newcontainer['ports'] = container[5]
            newcontainer['deploy'] = container[6]
            containers.append(kcli_pb2.container(**newcontainer))
        response = kcli_pb2.containerslist(containers=containers)
        return response

    def list_container_images(self, request, context):
        print("Handling list_container_images call")
        config = Kconfig()
        # cont = Kcontainerconfig(config, client=args.containerclient).cont
        cont = Kcontainerconfig(config).cont
        response = kcli_pb2.imageslist(images=cont.list_images())
        return response

    def list_profiles(self, request, context):
        print("Handling list_profiles call")
        baseconfig = Kbaseconfig()
        profiles = []
        for profile in baseconfig.list_profiles():
            newprofile = {}
            newprofile['name'] = profile[0]
            newprofile['flavor'] = profile[1]
            newprofile['pool'] = profile[2]
            newprofile['disks'] = profile[3]
            newprofile['image'] = profile[4]
            newprofile['nets'] = profile[5]
            newprofile['cloudinit'] = profile[6]
            newprofile['nested'] = profile[7]
            newprofile['reservedns'] = profile[8]
            newprofile['reservehost'] = profile[9]
            profiles.append(kcli_pb2.profile(**newprofile))
        response = kcli_pb2.profileslist(profiles=profiles)
        return response

    def list_hosts(self, request, context):
        print("Handling list_hosts call")
        baseconfig = Kbaseconfig()
        clients = []
        for client in sorted(baseconfig.clients):
            newclient = {}
            newclient['client'] = client
            newclient['type'] = baseconfig.ini[client].get('type', 'kvm')
            newclient['enabled'] = baseconfig.ini[client].get('enabled', True)
            newclient['enabled'] = baseconfig.ini[client].get('enabled', True)
            newclient['current'] = True if client == baseconfig.client else False
            clients.append(kcli_pb2.client(**newclient))
        response = kcli_pb2.clientslist(clients=clients)
        return response

    def list_plans(self, request, context):
        print("Handling list_plans call")
        config = Kconfig()
        planslist = []
        for plan in config.list_plans():
            planslist.append({'plan': plan[0], 'vms': plan[1]})
        response = kcli_pb2.planslist(plans=[kcli_pb2.plan(**p) for p in planslist])
        return response

    def list_kubes(self, request, context):
        print("Handling list_kubes call")
        config = Kconfig()
        kubeslist = []
        for kubename in config.list_kubes():
            kube = config.list_kubes()[kubename]
            kubetype = kube['type']
            kubevms = kube['vms']
            kubeslist.append({'kube': kubename, 'type': kubetype, 'vms': kubevms})
        response = kcli_pb2.kubeslist(kubes=[kcli_pb2.kube(**p) for p in kubeslist])
        return response

    def list_keywords(self, request, context):
        print("Handling list_keywords call")
        baseconfig = Kbaseconfig()
        keywords = baseconfig.list_keywords()
        keywordslist = []
        for keyword in keywords:
            keywordslist.append({'keyword': keyword, 'value': str(keywords[keyword])})
        response = kcli_pb2.keywordslist(keywords=[kcli_pb2.keyword(**k) for k in keywordslist])
        return response

    def list_lbs(self, request, context):
        print("Handling list_lbs call")
        config = Kconfig()
        lbslist = []
        for lb in config.list_loadbalancers():
            lbname, ip, protocol, ports, target = lb
            lbslist.append({'lb': lbname, 'ip': ip, 'protocol': protocol, 'ports': ports, 'target': target})
        response = kcli_pb2.lbslist(lbs=[kcli_pb2.lb(**l) for l in lbslist])
        return response

    def list_repos(self, request, context):
        print("Handling list_repos call")
        baseconfig = Kbaseconfig()
        repos = baseconfig.list_repos()
        reposlist = []
        for r in repos:
            reposlist.append({'repo': r, 'url': repos[r]})
        response = kcli_pb2.reposlist(repos=[kcli_pb2.repo(**r) for r in reposlist])
        return response

    def list_products(self, request, context):
        print("Handling list_products call")
        repo = request.repo if request.repo != '' else None
        group = request.group if request.group != '' else None
        baseconfig = Kbaseconfig()
        products = baseconfig.list_products(group=group, repo=repo)
        productslist = []
        for product in products:
            productname = product['name']
            repo = product['repo']
            group = product['group']
            numvms = str(product.get('numvms', 'N/A'))
            memory = str(product.get('memory', 'N/A'))
            description = product.get('description', 'N/A')
            productslist.append({'product': productname, 'numvms': numvms, 'memory': memory, 'description': description,
                                 'repo': repo, 'group': group})
        response = kcli_pb2.productslist(products=[kcli_pb2.product(**r) for r in productslist])
        return response

    def restart_container(self, request, context):
        print("Handling restart_container call for:\n%s" % request)
        config = Kconfig()
        cont = Kcontainerconfig(config).cont
        result = cont.restart_container(request.container)
        response = kcli_pb2.result(**result)
        return response

    def start_container(self, request, context):
        print("Handling start_container call for:\n%s" % request)
        config = Kconfig()
        cont = Kcontainerconfig(config).cont
        result = cont.start_container(request.container)
        response = kcli_pb2.result(**result)
        return response

    def stop_container(self, request, context):
        print("Handling stop_container call for:\n%s" % request)
        config = Kconfig()
        cont = Kcontainerconfig(config).cont
        result = cont.stop_container(request.container)
        response = kcli_pb2.result(**result)
        return response

    def autostart_plan(self, request, context):
        print("Handling autostart_plan call for:\n%s" % request)
        config = Kconfig()
        config.plan(request.plan, autostart=True)
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def noautostart_plan(self, request, context):
        print("Handling autostart_plan call for:\n%s" % request)
        config = Kconfig()
        config.plan(request.plan, noautostart=True)
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def start_plan(self, request, context):
        print("Handling start_plan call for:\n%s" % request)
        config = Kconfig()
        config.plan(request.plan, start=True)
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def stop_plan(self, request, context):
        print("Handling stop_plan call for:\n%s" % request)
        config = Kconfig()
        config.plan(request.plan, stop=True)
        result = {'result': 'success'}
        response = kcli_pb2.result(**result)
        return response

    def switch_host(self, request, context):
        print("Handling switch_host call for:\n%s" % request)
        baseconfig = Kbaseconfig()
        result = baseconfig.switch_host(request.client)
        response = kcli_pb2.result(**result)
        return response


def main():
    print('Starting server. Listening on port 50051.')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    kcli_pb2_grpc.add_KcliServicer_to_server(KcliServicer(), server)
    kcli_pb2_grpc.add_KconfigServicer_to_server(KconfigServicer(), server)
    try:
        from grpc_reflection.v1alpha import reflection
        SERVICE_NAMES = (
            kcli_pb2.DESCRIPTOR.services_by_name['Kcli'].full_name,
            kcli_pb2.DESCRIPTOR.services_by_name['Kconfig'].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(SERVICE_NAMES, server)
    except Exception as e:
        print(f"Hit {e} when enabling reflection")
        pass
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    main()
