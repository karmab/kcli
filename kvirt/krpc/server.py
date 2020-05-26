import grpc
from grpc_reflection.v1alpha import reflection
from concurrent import futures
import time
import kvirt.krpc.kcli_pb2 as kcli_pb2
import kvirt.krpc.kcli_pb2_grpc as kcli_pb2_grpc

from kvirt.config import Kconfig, Kbaseconfig
from kvirt import common
from kvirt import version
from kvirt.defaults import VERSION
import os


class KcliServicer(kcli_pb2_grpc.KcliServicer):

    def get_lastvm(self, request, context):
        print("Handling get_lastvm for:\n%s" % request)
        config = Kconfig()
        name = common.get_lastvm(config.client if request.client == '' else request.client)
        response = kcli_pb2.vm(name=name)
        return response

    def delete(self, request, context):
        print("Handling delete call for:\n%s" % request)
        config = Kconfig()
        result = config.k.delete(request.name, snapshots=request.snapshots)
        response = kcli_pb2.result(**result)
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

    def get_version(self, request, context):
        print("Handling get_version call")
        versiondir = os.path.dirname(version.__file__)
        git_version = open('%s/git' % versiondir).read().rstrip() if os.path.exists('%s/git' % versiondir) else 'N/A'
        ver = {'version': VERSION, 'git_version': git_version}
        response = kcli_pb2.version(**ver)
        return response

    def get_config(self, request, context):
        print("Handling list_profiles call")
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


def main():
    print('Starting server. Listening on port 50051.')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    kcli_pb2_grpc.add_KcliServicer_to_server(KcliServicer(), server)
    kcli_pb2_grpc.add_KconfigServicer_to_server(KconfigServicer(), server)
    SERVICE_NAMES = (
        kcli_pb2.DESCRIPTOR.services_by_name['Kcli'].full_name,
        kcli_pb2.DESCRIPTOR.services_by_name['Kconfig'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    main()
