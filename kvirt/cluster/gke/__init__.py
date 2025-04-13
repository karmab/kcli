from google.cloud import container_v1
from kvirt.common import error, success, info2, pprint, fix_typos
import os
from time import sleep
import sys
from yaml import safe_dump, safe_load


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
            pprint("Waiting 5s for operation to complete")
            sleep(5)
            timeout += 5
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
                                                                                        'ca_cert': ca_cert,
                                                                                        'client': config.client})
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    with open(f"{clusterdir}/auth/kubeconfig", 'w') as f:
        f.write(rendered)


def project_init(config):
    if config.type != 'gcp':
        error("This is only available for gcp provider")
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
    region = config.options.get('region')
    zone = config.options.get('zone')
    if region is None and zone is None:
        error("Missing project in the configuration. Leaving")
        sys.exit(1)
    elif region is not None and zone is None:
        zone = f'{region}-b'
    elif region is None and zone is not None:
        region = zone[:-2]
    return project, region, zone


def scale(config, plandir, cluster, overrides):
    data = {'workers': 2}
    data.update(overrides)
    workers = data['workers']
    cluster = overrides.get('cluster', cluster or 'mygke')
    project, region, zone = project_init(config)
    client = container_v1.ClusterManagerClient()
    zonal = overrides.get('zonal', True)
    nodepool = f"projects/{project}/locations/{zone if zonal else region}/clusters/{cluster}/nodepools/{cluster}"
    request = container_v1.SetNodePoolSizeRequest(name=nodepool, node_count=workers)
    operation = client.set_node_pool_size(request=request)
    _wait_for_operation(client, operation.self_link)
    return {'result': 'success'}


def create(config, plandir, cluster, overrides, dnsconfig=None):
    data = safe_load(open(f'{plandir}/kcli_default.yml'))
    data.update(overrides)
    fix_typos(data)
    workers = data['workers']
    zonal = data['zonal']
    autopilot = data['autopilot']
    autoscaling = data['autoscaling']
    beta_apis = data['beta_apis']
    spot = data['spot']
    secureboot = data['secureboot']
    confidential = data['confidential']
    preemptible = data['preemptible']
    disk_type = data['disk_type']
    plan = cluster
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
            safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    project, region, zone = project_init(config)
    clusterspec = {'name': cluster, 'enable_kubernetes_alpha': data['alpha']}
    clusterspec['resource_labels'] = {'plan': cluster, 'kube': cluster, 'kubetype': 'gke'}
    network = data['network']
    create_subnetwork = False
    networks = config.k.list_networks()
    if network != 'default':
        subnets = config.k.list_subnets()
        if network in networks:
            clusterspec['network'] = network
            legacy = networks[network]['cidr'] != ''
        elif network in subnets:
            subnet_data = config.k.info_subnet(network)
            clusterspec['network'] = subnet_data['network']
            clusterspec['subnetwork'] = network
            legacy = 'secondary_cidrs' not in subnet_data
        else:
            msg = f'Invalid subnet {network}'
            return {'result': 'failure', 'reason': msg}
    elif 'default' in networks:
        clusterspec['network'] = network
        legacy = networks[network]['cidr'] != ''
    else:
        msg = f'Invalid network {network}'
        return {'result': 'failure', 'reason': msg}
    native = data['native']
    cluster_network_ipv4, service_network_ipv4 = data['cluster_network_ipv4'], data['service_network_ipv4']
    if native:
        ip_allocation_policy = {'use_ip_aliases': True,
                                'create_subnetwork': create_subnetwork,
                                'cluster_ipv4_cidr_block': cluster_network_ipv4,
                                'services_ipv4_cidr_block': service_network_ipv4}
        clusterspec['ip_allocation_policy'] = ip_allocation_policy
    elif legacy:
        clusterspec['ip_allocation_policy'] = {'use_ip_aliases': False}
    if 'version' in overrides:
        clusterspec['initial_cluster_version'] = overrides['version']
    if beta_apis:
        clusterspec['enable_k8s_beta_apis'] = True
    if autopilot:
        clusterspec['autopilot'] = True
    nodepool = {'name': cluster, 'initial_node_count': workers}
    worker_version = data['worker_version']
    if worker_version is not None:
        nodepool['version'] = overrides['worker_version']
    if autoscaling:
        min_node_count = data['autoscaling_minimum']
        max_node_count = data['autoscaling_maximum']
        nodepool['autoscaling'] = {'enable_node_autoprovisioning': True, 'min_node_count': min_node_count,
                                   'max_node_count': max_node_count}
    nodepool_config = {'preemptible': preemptible, 'spot': spot, 'disk_type': disk_type}
    integrity_monitoring = data['integrity_monitoring']
    if secureboot or integrity_monitoring:
        nodepool_config['shielded_instance_config'] = {'enable_secure_boot': secureboot,
                                                       'enable_integrity_monitoring': integrity_monitoring}
    if confidential:
        nodepool_config['confidential_nodes'] = {'enabled': True}
    flavor = data['flavor']
    if flavor is not None:
        nodepool_config['machine_type'] = flavor
    disk_size = data['disk_size']
    if disk_size is not None:
        nodepool_config['disk_size_gb'] = disk_size
    image = data.get('image') or data.get('image_type')
    if image is not None:
        nodepool_config['image_type'] = image.upper()
    local_ssd_count = data['local_ssd_count']
    if local_ssd_count is not None:
        nodepool_config['local_ssd_count'] = local_ssd_count
    nodepool['config'] = nodepool_config
    clusterspec['node_pools'] = [nodepool]
    client = container_v1.ClusterManagerClient()
    parent = f'projects/{project}/locations/{zone if zonal else region}'
    request = container_v1.CreateClusterRequest(parent=parent, cluster=clusterspec)
    if config.debug:
        print(clusterspec)
    operation = client.create_cluster(request=request)
    if config.debug:
        print(operation)
    _wait_for_operation(client, operation.self_link)
    kubeconfig = f'{clusterdir}/auth/kubeconfig'
    while not os.path.exists(kubeconfig):
        get_kubeconfig(config, cluster, zonal=zonal)
        sleep(5)
    success(f"Kubernetes cluster {cluster} deployed!!!")
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


def info_service(config, zonal=True):
    project, region, zone = project_init(config)
    client = container_v1.ClusterManagerClient()
    name = f"projects/{project}/locations/{zone if zonal else region}"
    request = container_v1.GetServerConfigRequest(name=name)
    response = client.get_server_config(request=request)
    default_image_type = response.default_image_type
    print(f"default_image_type: {default_image_type}")
    valid_image_types = response.valid_image_types
    print(f"valid_image_types: {valid_image_types}")
    default_cluster_version = response.default_cluster_version
    print(f"default_cluster_version: {default_cluster_version}")
    valid_master_versions = response.valid_master_versions
    print(f"valid_cluster_versions: {valid_master_versions}")
    valid_node_versions = response.valid_node_versions
    print(f"valid_worker_versions: {valid_node_versions}")
    return {}
