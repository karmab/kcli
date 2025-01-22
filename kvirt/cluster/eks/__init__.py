import boto3
from kvirt.common import success, info2, pprint, error, fix_typos, warning, pretty_print
import os
import re
import yaml
from yaml import safe_dump, safe_load

supported_versions = ['1.20', '1.21', '1.22', '1.23', '1.24', '1.25', '1.26', '1.27']

CTLPLANE_POLICIES = [
    'arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy',
    'AmazonEC2ContainerRegistryReadOnly',
    'AmazonEKSBlockStoragePolicy',
    'AmazonEKSClusterPolicy',
    'AmazonEKS_CNI_Policy',
    'AmazonEKSComputePolicy',
    'AmazonEKSLoadBalancingPolicy',
    'AmazonEKSNetworkingPolicy'
]

WORKER_POLICIES = [
    'arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy',
    'AmazonEC2ContainerRegistryPullOnly',
    'AmazonEC2ContainerRegistryReadOnly',
    'AmazonEKSBlockStoragePolicy',
    'AmazonEKS_CNI_Policy',
    'AmazonEKSWorkerNodeMinimalPolicy',
    'AmazonEKSWorkerNodePolicy'
]


def get_cluster_name():
    kclidir = os.path.expanduser('~/.kcli/clusters')
    return re.sub(f'{kclidir}/(.*)/auth/kubeconfig', r'\1', os.environ.get('KUBECONFIG'))


def project_init(config):
    access_key_id = config.options.get('access_key_id')
    access_key_secret = config.options.get('access_key_secret')
    session_token = config.options.get('session_token')
    region = config.options.get('region')
    return access_key_id, access_key_secret, session_token, region


def get_role_policies(config, name):
    role_policies = []
    access_key_id, access_key_secret, session_token, region = project_init(config)
    iam = boto3.client('iam', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    try:
        policies = iam.list_attached_role_policies(RoleName=name)['AttachedPolicies']
    except:
        error(f"Role {name} not found")
        return {}
    for attached_policy in policies:
        attached_policy_name = attached_policy['PolicyName']
        role_policies.append(attached_policy_name)
    return sorted(role_policies)


def get_kubeconfig(config, cluster, zonal=True):
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    cluster_data = eks.describe_cluster(name=cluster)
    cluster_cert = str(cluster_data["cluster"]["certificateAuthority"]["data"])
    cluster_ep = str(cluster_data["cluster"]["endpoint"])
    cluster_arn = cluster_data["cluster"]["arn"]
    cluster_config = {"apiVersion": "v1", "kind": "Config",
                      "clusters": [{"cluster": {"server": cluster_ep, "certificate-authority-data": cluster_cert},
                                    "name": cluster_arn}], "contexts": [{"context": {"cluster": cluster_arn,
                                                                                     "user": cluster_arn},
                                                                         "name": cluster_arn}],
                      "current-context": cluster_arn, "preferences": {},
                      "users": [{"name": cluster_arn, "user": {"exec": {
                          "apiVersion": "client.authentication.k8s.io/v1beta1", "command": "ekstoken",
                          "interactiveMode": "Never", "args": [config.client, cluster]}}}]}
    config_text = safe_dump(cluster_config, default_flow_style=False)
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    with open(f"{clusterdir}/auth/kubeconfig", 'w') as f:
        f.write(config_text)


def process_apps(config, clusterdir, apps, overrides):
    if not apps:
        return
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    for app in apps:
        base_data = overrides.copy()
        if isinstance(app, str):
            app = {'name': app}
        app_data = app
        appname = app.get('name')
        if appname is None:
            error(f"Missing name in dict {app}. Skipping")
            continue
        app_data.update(base_data)
        pprint(f"Adding app {appname}")
        result = config.create_app_eks(appname, app_data)
        if result != 0:
            error(f"Issue adding app {appname}")


def scale(config, plandir, cluster, overrides):
    data = {'workers': 2,
            'network': 'default',
            'role': None,
            'disk_size': None,
            'flavor': None,
            'ami_type': None,
            'capacity_type': None,
            'version': None}
    data.update(overrides)
    cluster = overrides.get('cluster', cluster or 'myeks')
    version = data['version']
    workers = data['workers']
    disk_size = data['disk_size']
    flavor = data['flavor']
    ami_type = data['ami_type']
    capacity_type = data['capacity_type']
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    pprint(f"Updating nodegroup {cluster}")
    nodegroup_data = {'clusterName': cluster, 'nodegroupName': cluster,
                      'scalingConfig': {'minSize': workers, 'maxSize': 50, 'desiredSize': workers}}
    if version is not None:
        nodegroup_data['version'] = version
    if disk_size is not None:
        nodegroup_data['diskSize'] = disk_size
    if flavor is not None:
        nodegroup_data['instanceTypes'] = [flavor]
    if ami_type is not None:
        nodegroup_data['amiType'] = ami_type
    if capacity_type is not None:
        nodegroup_data['capacityType'] = capacity_type
    response = eks.update_nodegroup_config(**nodegroup_data)
    if config.debug:
        print(response)
    return {'result': 'success'}


def create(config, plandir, cluster, overrides, dnsconfig=None):
    data = safe_load(open(f'{plandir}/kcli_default.yml'))
    data.update(overrides)
    fix_typos(data)
    k = config.k
    version = data['version']
    apps = overrides.get('apps', [])
    workers = data['workers']
    ctlplane_role = data['ctlplane_role']
    worker_role = data['worker_role']
    disk_size = data['disk_size']
    flavor = data['flavor']
    ami_type = data['ami_type']
    capacity_type = data['capacity_type']
    network = data['subnet'] or data['network']
    extra_networks = data['extra_subnets'] or data['extra_networks']
    sgid = data['security_group']
    plan = cluster
    tags = {'plan': cluster, 'kube': cluster, 'kubetype': 'eks'}
    cluster_data = {'name': cluster, 'tags': tags}
    auto_mode = data['auto_mode']
    if not data['default_addons']:
        warning("Disabling network add-ons (and automode)")
        cluster_data['bootstrapSelfManagedAddons'] = False
        auto_mode = False
    extended_support = data['extended_support']
    if not extended_support:
        cluster_data['upgradePolicy'] = {'supportType': 'STANDARD'}
    zonal_shift = data['zonal_shift']
    if zonal_shift:
        cluster_data['zonalShiftConfig'] = {'enabled': True}
    logging = data['logging']
    if logging:
        logging_data = []
        for _type in data['logging_types']:
            logging_data.append({'type': _type, 'enabled': True})
        cluster_data['logging'] = {'clusterLogging': logging_data}
    if version is not None:
        version = str(version)
        if version not in supported_versions:
            msg = f"Version needs to be one of those: {(',').join(supported_versions)}"
            return {'result': 'failure', 'reason': msg}
        cluster_data['version'] = version
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if os.path.exists(clusterdir):
        return {'result': 'failure', 'reason': f"Remove existing directory {clusterdir} or use --force"}
    else:
        os.makedirs(clusterdir)
        os.mkdir(f"{clusterdir}/auth")
        with open(f"{clusterdir}/kcli_parameters.yml", 'w') as p:
            installparam = overrides.copy()
            installparam['plan'] = plan
            installparam['cluster'] = cluster
            installparam['kubetype'] = 'eks'
            installparam['client'] = config.client
            yaml.safe_dump(installparam, p, default_flow_style=False, encoding='utf-8', allow_unicode=True)
    access_key_id, access_key_secret, session_token, region = project_init(config)
    account_id = k.get_account_id()
    if ctlplane_role is not None:
        pprint(f"Assuming ctlplane_role {ctlplane_role} has the correct policies")
        ctlplane_role = f'arn:aws:iam::{account_id}:role/{ctlplane_role}'
    else:
        ctlplane_role_name = 'kcli-eks-ctlplane'
        if ctlplane_role_name not in k.list_roles():
            pprint(f"Creating ctlplane role {ctlplane_role_name}")
            k.create_eks_role(ctlplane_role_name, CTLPLANE_POLICIES)
        ctlplane_role = f'arn:aws:iam::{account_id}:role/{ctlplane_role_name}'
    pprint(f"Using ctlplane role {os.path.basename(ctlplane_role)}")
    cluster_data['roleArn'] = ctlplane_role
    if worker_role is not None:
        pprint(f"Assuming worker_role {worker_role} has the correct policies")
        worker_role = f'arn:aws:iam::{account_id}:role/{worker_role}'
    else:
        worker_role_name = 'kcli-eks-worker'
        if worker_role_name not in k.list_roles():
            pprint(f"Creating worker role {worker_role_name}")
            k.create_eks_role(worker_role_name, WORKER_POLICIES)
        worker_role = f'arn:aws:iam::{account_id}:role/{worker_role_name}'
    pprint(f"Using worker role {os.path.basename(worker_role)}")
    subnetids = []
    total_subnets = [network] + extra_networks
    for index, n in enumerate(total_subnets):
        vpcid, subnetid, az = k.eks_get_network(n)
        if index == 0:
            sgid = k.get_security_group_id(n, vpcid) if sgid is not None else k.get_default_security_group_id(vpcid)
            if sgid is None:
                return {'result': 'failure', 'reason': "Couldn't find a valid security group"}
        subnetids.append(subnetid)
    if len(total_subnets) == 1:
        subnets = k.list_subnets()
        subnetid = None
        for subnetname in subnets:
            subnet = subnets[subnetname]
            if subnet['network'] == vpcid and subnet['id'] != subnetid and subnet['az'] != az:
                subnetid = subnet['id']
                break
        if subnetid is None:
            return {'result': 'failure', 'reason': "Couldn't find a valid subnet in the same vpc but with other az"}
        else:
            pprint(f"Using subnet {subnetid} as extra subnet")
            subnetids.append(subnetid)
    cluster_data['resourcesVpcConfig'] = {'subnetIds': subnetids, 'securityGroupIds': [sgid]}
    if auto_mode:
        auto_mode_dict = {'storageConfig': {'blockStorage': {'enabled': True}},
                          'kubernetesNetworkConfig': {'elasticLoadBalancing': {'enabled': True}},
                          'computeConfig': {'enabled': True, 'nodePools': ['general-purpose', 'system'],
                                            'nodeRoleArn': worker_role},
                          'accessConfig': {'authenticationMode': 'API'}}
        cluster_data.update(auto_mode_dict)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    response = eks.create_cluster(**cluster_data)
    if config.debug:
        print(response)
    pprint(f"Waiting for cluster {cluster} to be created")
    waiter = eks.get_waiter("cluster_active")
    waiter.wait(name=cluster)
    get_kubeconfig(config, cluster)
    if not auto_mode:
        nodegroup_data = {'clusterName': cluster, 'nodegroupName': cluster, 'scalingConfig':
                          {'minSize': workers, 'maxSize': 50, 'desiredSize': workers}, 'subnets': subnetids,
                          'tags': tags, 'nodeRole': worker_role}
        keypair = config.options.get('keypair')
        if keypair is not None:
            nodegroup_data['remoteAccess'] = {'ec2SshKey': keypair, 'sourceSecurityGroups': [sgid]}
        if version is not None:
            nodegroup_data['version'] = version
        if disk_size is not None:
            nodegroup_data['diskSize'] = disk_size
        if flavor is not None:
            nodegroup_data['instanceTypes'] = [flavor]
        if ami_type is not None:
            nodegroup_data['amiType'] = ami_type
        if capacity_type is not None:
            nodegroup_data['capacityType'] = capacity_type
        pprint(f"Creating nodegroup {cluster}")
        response = eks.create_nodegroup(**nodegroup_data)
        if config.debug:
            print(response)
        waiter = eks.get_waiter("cluster_active")
        waiter.wait(name=cluster)
    success(f"Kubernetes cluster {cluster} deployed!!!")
    info2(f"export KUBECONFIG=$HOME/.kcli/clusters/{cluster}/auth/kubeconfig")
    info2("export PATH=$PWD:$PATH")
    os.environ['KUBECONFIG'] = f"{clusterdir}/auth/kubeconfig"
    process_apps(config, clusterdir, apps, overrides)
    handle_oidc_provider(eks, cluster, overrides)
    return {'result': 'success'}


def delete(config, cluster, zonal=True):
    fail = False
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    nodegroups = eks.list_nodegroups(clusterName=cluster).get('nodegroups', [])
    if cluster in nodegroups:
        try:
            response = eks.delete_nodegroup(clusterName=cluster, nodegroupName=cluster)
            if config.debug:
                print(response)
            pprint(f"Waiting for nodegroup {cluster} to be deleted")
            waiter = eks.get_waiter("nodegroup_deleted")
            waiter.wait(clusterName=cluster, nodegroupName=cluster)
        except Exception as e:
            fail = True
            error(f"Hit Issue when deleting nodegroup {cluster}: {e}")
    try:
        response = eks.delete_cluster(name=cluster)
        if config.debug:
            print(response)
        pprint(f"Waiting for cluster {cluster} to be deleted")
        waiter = eks.get_waiter("cluster_deleted")
        waiter.wait(name=cluster)
    except Exception as e:
        fail = True
        error(f"Hit Issue when deleting {cluster}: {e}")
    if fail:
        return {'result': 'failure', 'reason': 'Hit issue'}
    else:
        return {'result': 'success'}


def list(config):
    results = {}
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    for cluster in eks.list_clusters()['clusters']:
        results[cluster] = {'type': 'eks', 'plan': None, 'vms': []}
    return results


def info(config, cluster, debug=False):
    results = {}
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    try:
        response = eks.describe_cluster(name=cluster)['cluster']
        if debug:
            print(response)
    except Exception as e:
        error(e)
        return {}
    results = {'nodes': [], 'version': response['version']}
    return results


def info_service(config, zonal=True):
    return {}


def list_apps(config, quiet=False, installed=False):
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    if installed:
        cluster = get_cluster_name()
        return eks.list_addons(clusterName=cluster).get('addons', [])
    else:
        return [i['addonName'] for i in eks.describe_addon_versions().get('addons', [])]


def create_app(config, app, overrides={}):
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    cluster = get_cluster_name()
    data = {'clusterName': cluster, 'addonName': app}
    if 'version' in overrides:
        data['addonVersion'] = overrides['version']
    eks.create_addon(**data)


def delete_app(config, app, overrides={}):
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    cluster = get_cluster_name()
    eks.delete_addon(clusterName=cluster, addonName=app)


def info_app(config, app):
    access_key_id, access_key_secret, session_token, region = project_init(config)
    eks = boto3.client('eks', aws_access_key_id=access_key_id, aws_secret_access_key=access_key_secret,
                       region_name=region, aws_session_token=session_token)
    data = eks.describe_addon_versions(addonName=app).get('addons', [])
    if data:
        pretty_print(data[0])
    else:
        error(f"App {app} not found")


def handle_oidc_provider(eks, cluster, overrides):
    name = overrides.get('oidc_name', 'oidc-config')
    issuer_url = overrides.get('oidc_issuer_url')
    client_id = overrides.get('oidc_client_id')
    username_claim = overrides.get('oidc_username_claim', 'email')
    group_claim = overrides.get('oidc_group_claim', 'cognito:groups')
    if issuer_url is None or client_id is None:
        return
    pprint(f"Creating oidc config {name}")
    pprint(f"Using {username_claim} as username claim")
    pprint(f"Using {group_claim} as group claim")
    oidc = {'identityProviderConfigName': name, 'issuerUrl': issuer_url, 'clientId': client_id,
            'usernameClaim': username_claim, 'groupsClaim': group_claim}
    eks.associate_identity_provider_config(clusterName=cluster, oidc=oidc)
