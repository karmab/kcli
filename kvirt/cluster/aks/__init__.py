from azure.identity import ClientSecretCredential
from azure.mgmt.containerservice import ContainerServiceClient
from kvirt.common import success, info2, pprint, error, get_ssh_pub_key, warning, fix_typos
import os
import yaml

resource_group = 'kcli'


def project_init(config):
    admin_username = config.options.get('admin_username', 'superadmin')
    location = config.options.get('location', 'westus')
    subscription_id = config.options.get('subscription_id')
    app_id = config.options.get('app_id')
    tenant_id = config.options.get('tenant_id')
    secret = config.options.get('secret')
    return admin_username, location, subscription_id, app_id, tenant_id, secret


def get_kubeconfig(config, cluster, zonal=True):
    admin_username, location, subscription_id, app_id, tenant_id, secret = project_init(config)
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=secret)
    containerservice_client = ContainerServiceClient(credential, subscription_id)
    results = containerservice_client.managed_clusters.list_cluster_admin_credentials(resource_group, cluster)
    kubeconfig = results.kubeconfigs[0].value
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    with open(f"{clusterdir}/auth/kubeconfig", 'wb') as f:
        f.write(kubeconfig)


def scale(config, cluster, overrides):
    data = {'workers': 2,
            'network': 'default',
            'disk_size': 0,
            'flavor': 'Standard_E2ds_v4',
            'autoscaling': True,
            'version': None}
    data.update(overrides)
    cluster = overrides.get('cluster') or cluster or 'myeks'
    version = data['version']
    workers = data['workers']
    disk_size = data['disk_size']
    flavor = data['flavor']
    admin_username, location, subscription_id, app_id, tenant_id, secret = project_init(config)
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=secret)
    containerservice_client = ContainerServiceClient(credential, subscription_id)
    cluster_data = containerservice_client.managed_clusters.get(resource_group, cluster)
    pprint(f"Updating cluster {cluster}")
    if cluster_data.agent_pool_profiles.count != workers:
        cluster_data.agent_pool_profiles.count = workers
        cluster_data.agent_pool_profiles.min_count = workers
    if version is not None and cluster_data.kubernetes_version != version:
        cluster_data.kubernetes_version = version
    if flavor is not None and cluster_data.agent_pool_profiles.vm_size != flavor:
        cluster_data.agent_pool_profiles.vm_size = flavor
    if flavor is not None and cluster_data.agent_pool_profiles.osDiskSizeGB != disk_size:
        cluster_data.agent_pool_profiles.osDiskSizeGB = disk_size
    response = containerservice_client.managed_clusters.begin_create_or_update(resource_group, cluster, cluster_data)
    if config.debug:
        print(response.result())
    return {'result': 'success'}


def create(config, cluster, overrides, dnsconfig=None):
    data = {'workers': 2,
            'network': None,
            'network_type': None,
            'disk_size': 0,
            'flavor': 'Standard_E2ds_v4',
            'autoscaling': True,
            'fips': False,
            'version': None}
    data.update(overrides)
    fix_typos(data)
    network = data['network']
    version = data['version']
    workers = data['workers']
    autoscaling = data['autoscaling']
    disk_size = data['disk_size']
    flavor = data['flavor']
    network_type = data['network_type']
    fips = data['fips']
    pub_key = data.get('pub_key') or get_ssh_pub_key()
    keys = data.get('keys', [])
    if pub_key is None:
        if keys:
            warning("Using first key from your keys array")
            pub_key = keys[0]
        else:
            msg = "No usable public key found, which is required for the deployment. Create one using ssh-keygen"
            return {'result': 'failure', 'reason': msg}
    pub_key = os.path.expanduser(pub_key)
    if not pub_key.startswith('ssh-') and os.path.exists(pub_key):
        pub_key = open(pub_key).read().strip()
    else:
        msg = f"Publickey file {pub_key} not found"
        return {'result': 'failure', 'reason': msg}
    clustervalue = overrides.get('cluster') or cluster or 'myaks'
    plan = cluster if cluster is not None else clustervalue
    tags = {'plan': clustervalue, 'kube': clustervalue, 'kubetype': 'aks'}
    cluster_data = {'name': clustervalue, 'tags': tags}
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{clustervalue}")
    if os.path.exists(clusterdir):
        return {'result': 'failure', 'reason': f"Remove existing directory {clusterdir} or use --force"}
    else:
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['cluster'] = clustervalue
            installparam['kubetype'] = 'aks'
            installparam['client'] = config.client
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    tags = {'plan': clustervalue, 'kube': clustervalue, 'kubetype': 'aks'}
    admin_username, location, subscription_id, app_id, tenant_id, secret = project_init(config)
    agent_pool = {'name': clustervalue, 'vm_size': flavor, 'count': workers, 'min_count': workers, 'max_count': 30,
                  'enable_auto_scaling': autoscaling, 'mode': 'System', 'osDiskSizeGB': disk_size,
                  'enableFIPS': fips}
    if network is not None:
        agent_pool['vnetSubnetID'] = network
    service_principal_profile = {'client_id': app_id, 'secret': secret}
    linux_profile = {'admin_username': admin_username, 'ssh': {'public_keys': [{'key_data': pub_key}]}}
    cluster_data = {'location': location, 'dns_prefix': clustervalue, 'tags': tags,
                    'service_principal_profile': service_principal_profile,
                    'agent_pool_profiles': [agent_pool],
                    'linux_profile': linux_profile, 'enable_rbac': True}
    if version is not None:
        cluster_data['kubernetes_version'] = version
    network_profile = {}
    if network_type is not None:
        if network_type not in ['azure', 'kubenet']:
            return {'result': 'failure', 'reason': "Invalid network_type. Choose beetwen azure and kubenet"}
        network_profile['network_plugin'] = network_profile
    if network_profile:
        cluster_data['network_profile'] = network_profile
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=secret)
    containerservice_client = ContainerServiceClient(credential, subscription_id)
    response = containerservice_client.managed_clusters.begin_create_or_update(resource_group, clustervalue,
                                                                               cluster_data)
    if config.debug:
        print(response.result())
    pprint(f"Waiting for cluster {clustervalue} to be created")
    response.wait()
    get_kubeconfig(config, clustervalue)
    success(f"Kubernetes cluster {clustervalue} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{clustervalue}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
    return {'result': 'success'}


def delete(config, cluster, zonal=True):
    admin_username, location, subscription_id, app_id, tenant_id, secret = project_init(config)
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=secret)
    containerservice_client = ContainerServiceClient(credential, subscription_id)
    try:
        response = containerservice_client.managed_clusters.begin_delete(resource_group, cluster)
        if config.debug:
            print(response.result())
        pprint(f"Waiting for cluster {cluster} to be deleted")
        response.wait()
    except Exception as e:
        error(f"Hit Issue when getting {cluster}: {e}")
        return {'result': 'failure', 'reason': 'Hit issue'}
    return {'result': 'success'}


def list(config):
    results = {}
    admin_username, location, subscription_id, app_id, tenant_id, secret = project_init(config)
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=secret)
    containerservice_client = ContainerServiceClient(credential, subscription_id)
    response = containerservice_client.managed_clusters.list()
    for cluster in response:
        plan = cluster.tags.get('plan')
        results[cluster.name] = {'type': 'aks', 'plan': plan, 'vms': []}
    return results


def info(config, cluster, debug=False):
    results = {}
    admin_username, location, subscription_id, app_id, tenant_id, secret = project_init(config)
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=secret)
    containerservice_client = ContainerServiceClient(credential, subscription_id)
    try:
        response = containerservice_client.managed_clusters.get(resource_group, cluster)
        if debug:
            print(response)
    except Exception as e:
        error(e)
        return {}
    results = {'nodes': [], 'version': response.kubernetes_version}
    return results


def info_service(config, zonal=True):
    return {}
