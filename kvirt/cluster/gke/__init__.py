#!/usr/bin/env python

from google.cloud import container_v1
from kvirt.common import error, success, info2, pprint
import os
from time import sleep
import sys
import yaml


def _wait_for_operation(client, location):
    location = location.replace('https://container.googleapis.com/v1/', '')
    done = False
    timeout = 0
    while not done:
        if timeout > 60:
            return
        request = container_v1.GetOperationRequest(name=location)
        operation = client.get_operation(request=request)
        if str(operation.status) == 'Status.DONE':
            done = True
        else:
            sleep(5)
            timeout += 5
            pprint("Waiting for operation to complete")
        if operation.error.message != '':
            error(f"Got Error {operation.error.message}")
            break
    return


def get_kubeconfig(config, cluster, zonal=True):
    plandir = os.path.dirname(project_init.__code__.co_filename)
    project, region, zone = project_init(config)
    client = container_v1.ClusterManagerClient()
    request = {"name": f"projects/{project}/locations/{zone if zonal else region}/clusters/{cluster}"}
    response = client.get_cluster(request=request)
    endpoint = response.endpoint
    if endpoint == '':
        return
    ca_cert = response.master_auth.cluster_ca_certificate
    rendered = config.process_inputfile(cluster, f"{plandir}/kubeconfig.j2", overrides={'endpoint': endpoint,
                                                                                        'ca_cert': ca_cert})
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    with open(f"{clusterdir}/auth/kubeconfig", 'w') as f:
        f.write(rendered)


def project_init(config):
    if config.type != 'gcp':
        error("This workflow is only available for gcp provider")
        sys.exit(1)
    credentials = config.options.get('credentials')
    if credentials is not None:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser(credentials)
    elif 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        error("set GOOGLE_APPLICATION_CREDENTIALS variable.Leaving...")
        sys.exit(1)
    project = config.options.get('project')
    if project is None:
        error("Missing project in the configuration. Leaving")
        sys.exit(1)
    zone = config.options.get('zone', 'europe-west1-b')
    region = config.options.get('region', zone[:-2])
    return project, region, zone


def scale(config, cluster, overrides):
    data = {'workers': 2}
    data.update(overrides)
    workers = data['workers']
    cluster = overrides.get('cluster', cluster or 'mygke')
    project, region, zone = project_init(config)
    client = container_v1.ClusterManagerClient()
    request = container_v1.SetNodePoolSizeRequest(node_count=workers)
    operation = client.set_node_pool_size(request=request)
    _wait_for_operation(client, operation.self_link)
    return {'result': 'success'}


def create(config, cluster, overrides, dnsconfig=None):
    data = {'workers': 2,
            'autoscaling': True,
            'beta_apis': [],
            'network': 'default',
            'flavor': None,
            'disk_size': None,
            'image_type': None,
            'disk_type': None,
            'alpha': False,
            'beta': False,
            'zonal': True,
            'version': None}
    data.update(overrides)
    workers = data['workers']
    zonal = data['zonal']
    beta_apis = data['beta_apis']
    clustervalue = overrides.get('cluster') or cluster or 'mygke'
    plan = cluster if cluster is not None else clustervalue
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        msg = f"Remove existing directory {clusterdir} or use --force"
        return {'result': 'failure', 'reason': msg}
    else:
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['cluster'] = cluster
            installparam['kubetype'] = 'gke'
            installparam['zonal'] = zonal
            installparam['client'] = config.client
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    project, region, zone = project_init(config)
    clusterspec = {'name': cluster, 'enable_kubernetes_alpha': data['alpha']}
    if beta_apis:
        clusterspec['enable_k8s_beta_apis'] = beta_apis
    clusterspec['resource_labels'] = {'plan': cluster, 'kube': cluster, 'kubetype': 'gke'}
    network = data['network']
    if network != 'default':
        if network in config.k.list_networks():
            clusterspec['network'] = network
        elif network in config.k.list_subnets():
            clusterspec['subnetwork'] = network
        else:
            msg = f'Invalid network {network}'
            return {'result': 'failure', 'reason': msg}
    client = container_v1.ClusterManagerClient()
    parent = f'projects/{project}/locations/{zone if zonal else region}'
    node_pools = {'name': cluster, 'initial_node_count': workers}
    if 'version' in overrides:
        node_pools['initial_cluster_version'] = overrides['version']
    nodepool_config = {}
    flavor = data['flavor']
    if flavor is not None:
        nodepool_config['machine_type'] = flavor
    disk_size = data['disk_size']
    if disk_size is not None:
        nodepool_config['disk_size_gb'] = disk_size
    disk_type = data['disk_type']
    if disk_type is not None:
        nodepool_config['disk_type'] = disk_type
    image_type = data['image_type']
    if image_type is not None:
        nodepool_config['image_type'] = image_type
    if config:
        node_pools['config'] = nodepool_config
    clusterspec['node_pools'] = [node_pools]
    request = container_v1.CreateClusterRequest(parent=parent, cluster=clusterspec)
    operation = client.create_cluster(request=request)
    if config.debug:
        print(operation)
    _wait_for_operation(client, operation.self_link)
    kubeconfig = f'{clusterdir}/auth/kubeconfig'
    while not os.path.exists(kubeconfig):
        get_kubeconfig(config, cluster, zonal=zonal)
        sleep(5)
    success(f"Kubernetes cluster {cluster} deployed!!!")
    info2(f"export GOOGLE_APPLICATION_CREDENTIALS={os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
    return {'result': 'success'}


def delete(config, cluster, zonal=True):
    project, region, zone = project_init(config)
    client = container_v1.ClusterManagerClient()
    cluster = f"projects/{project}/locations/{zone if zonal else region}/clusters/{cluster}"
    request = container_v1.DeleteClusterRequest(name=cluster)
    try:
        operation = client.delete_cluster(request=request)
    except Exception as e:
        error(f"Hit Issue when getting {cluster}: {e}")
        return {'result': 'failure', 'reason': e}
    _wait_for_operation(client, operation.self_link)
    return {'result': 'success'}


def list(config):
    results = {}
    project, region, zone = project_init(config)
    client = container_v1.ClusterManagerClient()
    parent = f"projects/{project}/locations/-/clusters"
    request = container_v1.ListClustersRequest(parent=parent)
    clusters = client.list_clusters(request=request).clusters
    for cluster in clusters:
        results[cluster.name] = {'type': 'gke', 'plan': None, 'vms': []}
    return results


def info(config, cluster, debug=False):
    project, region, zone = project_init(config)
    client = container_v1.ClusterManagerClient()
    clusterdir = os.path.expanduser(f'~/.kcli/clusters/{cluster}')
    kubeconfig = f'{clusterdir}/auth/kubeconfig'
    cluster = f"projects/{project}/locations/{zone}/clusters/{cluster}"
    request = container_v1.GetClusterRequest(name=cluster)
    try:
        clusterinfo = client.get_cluster(request=request)
    except Exception as e:
        error(f"Hit Issue when getting {cluster}: {e}")
        return {}
    if debug:
        print(clusterinfo)
    if os.path.exists(kubeconfig):
        results = config.info_specific_kube(cluster)
    else:
        # nodes = [f'node-{index}' for index in range(clusterinfo.current_node_count)]
        results = {'nodes': [], 'version': clusterinfo.node_pools[0].version}
    return results
