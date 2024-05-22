import base64
from kubernetes import client, watch
import kopf
from kvirt.config import Kconfig
from logging import info as pprint, error
import os
from re import sub
import threading
import yaml

DOMAIN = "kcli.karmalabs.local"
VERSION = "v1"


def watch_configmaps():
    v1 = client.CoreV1Api()
    namespace = 'kcli-infra'
    config_maps = ['kcli-conf', 'kcli-ssh']
    while True:
        stream = watch.Watch().stream(v1.list_namespaced_config_map, namespace, timeout_seconds=10)
        for event in stream:
            obj = event["object"]
            obj_dict = obj.to_dict()
            current_config_map_name = obj_dict['metadata']['name']
            if current_config_map_name in config_maps and event["type"] == 'MODIFIED':
                print("Exiting as configmap was changed")
                os._exit(1)


@kopf.on.startup()
def startup(logger, **kwargs):
    pprint("Injecting crds if needed")
    os.popen("kubectl apply -f /crd.yml").read()


@kopf.on.resume(DOMAIN, VERSION, 'vms')
def handle_configmaps(spec, **_):
    pprint("Starting configmap watches in the background")
    threading.Thread(target=watch_configmaps).start()


@kopf.on.create(DOMAIN, VERSION, 'vms')
def create_vm(meta, spec, status, namespace, logger, **kwargs):
    name = meta.get('name')
    pprint(f"Handling create on vm {name}")
    config = Kconfig(client=spec.get('client'), quiet=True)
    exists = config.k.exists(name)
    if not exists:
        profile = spec.get("profile") or spec.get('image') or name
        pprint(f"Creating vm {name}")
        if profile is not None:
            result = config.create_vm(name, profile, overrides=dict(spec))
            if result['result'] != 'success':
                return result
    info = config.k.info(name)
    image = info.get('image')
    if image is not None and 'ip' not in info:
        raise kopf.TemporaryError("Waiting to populate ip", delay=10)
    return info


@kopf.on.delete(DOMAIN, VERSION, 'vms')
def delete_vm(meta, spec, namespace, logger, **kwargs):
    name = meta.get('name')
    pprint(f"Handling delete on vm {name}")
    keep = spec.get("keep", False)
    if not keep:
        config = Kconfig(client=spec.get('client'), quiet=True)
        exists = config.k.exists(name)
        if exists:
            pprint(f"Deleting vm {name}")
            return config.k.delete(name)


@kopf.on.update(DOMAIN, VERSION, 'vms')
def update_vm(meta, spec, namespace, old, new, diff, **kwargs):
    name = meta.get('name')
    pprint(f"Handling update on vm {name}")
    config = Kconfig(client=spec.get('client'), quiet=True)
    for entry in diff:
        if entry[0] not in ['add', 'change']:
            continue
        arg = entry[1][1]
        value = entry[3]
        overrides = {arg: value}
        config.update_vm(name, overrides)
        info = config.k.info(name)
        return info


@kopf.on.create(DOMAIN, VERSION, 'plans')
def create_plan(meta, spec, status, namespace, logger, **kwargs):
    plan = meta.get('name')
    pprint(f"Handling create on plan {plan}")
    pprint(f"Creating/Updating plan {plan}")
    overrides = spec.get('parameters', {})
    workdir = spec.get('workdir', '/workdir')
    inputstring = spec.get('plan')
    if inputstring is None:
        error("Plan %s not created because of missing plan spec" % plan)
        return {'result': 'failure', 'reason': 'missing plan spec'}
    else:
        inputstring = sub(r"origin:( *)", r"origin:\1%s/" % workdir, inputstring)
        config = Kconfig(client=spec.get('client'), quiet=True)
        return config.plan(plan, inputstring=inputstring, overrides=overrides)


@kopf.on.delete(DOMAIN, VERSION, 'plans')
def delete_plan(meta, spec, namespace, logger, **kwargs):
    plan = meta.get('name')
    if spec.get('plan') is not None:
        pprint(f"Handling delete on plan {plan}")
        config = Kconfig(client=spec.get('client'), quiet=True)
        return config.delete_plan(plan)


@kopf.on.update(DOMAIN, VERSION, 'plans')
def update_plan(meta, spec, status, namespace, logger, **kwargs):
    plan = meta.get('name')
    pprint(f"Handling update on plan {plan}")
    overrides = spec.get('parameters', {})
    workdir = spec.get('workdir', '/workdir')
    inputstring = spec.get('plan')
    if inputstring is None:
        error("Plan %s not updated because of missing plan spec" % plan)
        return {'result': 'failure', 'reason': 'missing plan spec'}
    else:
        inputstring = sub(r"origin:( *)", r"origin:\1%s/" % workdir, inputstring)
        config = Kconfig(client=spec.get('client'), quiet=True)
        return config.plan(plan, inputstring=inputstring, overrides=overrides, update=True)


@kopf.on.create(DOMAIN, VERSION, 'clusters')
def create_cluster(meta, spec, status, namespace, logger, **kwargs):
    cluster = meta.get('name')
    clusterdir = f"{os.environ['HOME']}/.kcli/clusters/{cluster}"
    pprint(f"Handling create on cluster {cluster}")
    config = Kconfig(client=spec.get('client'), quiet=True)
    if os.path.exists(clusterdir):
        return {'importedcluster': True}
    pprint(f"Creating cluster {cluster}")
    overrides = dict(spec)
    kubetype = overrides.get('kubetype', 'generic')
    result = config.create_kube(cluster, kubetype, overrides=overrides)
    kubeconfig = open(f"{clusterdir}/auth/kubeconfig").read()
    kubeconfig = base64.b64encode(kubeconfig.encode()).decode("UTF-8")
    result = {'kubeconfig': kubeconfig}
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml") as install:
            installparam = yaml.safe_load(install)
            if 'auth_pass' in installparam:
                auth_pass = installparam['auth_pass']
                result['auth_pass'] = base64.b64encode(auth_pass.encode()).decode("UTF-8")
            if 'virtual_router_id' in installparam:
                result['virtual_router_id'] = installparam['virtual_router_id']
            if 'plan' in installparam:
                result['plan'] = installparam['plan']
    return result


@kopf.on.delete(DOMAIN, VERSION, 'clusters')
def delete_cluster(meta, spec, namespace, logger, **kwargs):
    cluster = meta.get('name')
    pprint(f"Handling delete on cluster {cluster}")
    config = Kconfig(client=spec.get('client'), quiet=True)
    pprint(f"Deleting cluster {cluster}")
    return config.delete_kube(cluster)


@kopf.on.update(DOMAIN, VERSION, 'clusters')
def update_cluster(meta, spec, status, namespace, logger, **kwargs):
    cluster = meta.get('name')
    pprint(f"Handling update on cluster {cluster}")
    overrides = dict(spec)
    kubetype = overrides.get('kubetype', 'generic')
    data = {'kube': cluster, 'kubetype': kubetype}
    plan = None
    clusterdir = os.path.expanduser(f"~/.kcli/clusters/{cluster}")
    if not os.path.exists(clusterdir):
        msg = f"Cluster directory {clusterdir} not found..."
        error(msg)
        return {'result': 'failure', 'reason': msg}
    if os.path.exists(f"{clusterdir}/kcli_parameters.yml"):
        with open(f"{clusterdir}/kcli_parameters.yml") as install:
            installparam = yaml.safe_load(install)
            data.update(installparam)
            plan = installparam.get('plan', plan)
    data.update(overrides)
    data['plan'] = plan or cluster
    config = Kconfig(client=spec.get('client'), quiet=True)
    config.update_kube(cluster, kubetype, overrides=data)


@kopf.timer(DOMAIN, VERSION, 'clusters', interval=60, field='spec.autoscale', value=kopf.PRESENT)
def autoscale_cluster(meta, spec, patch, status, namespace, logger, **kwargs):
    cluster = meta['name']
    kubeconfig = f"{os.environ['HOME']}/.kcli/clusters/{cluster}/auth/kubeconfig"
    threshold = int(os.environ.get('AUTOSCALE_MAXIMUM', 10000))
    if threshold > 9999:
        pprint(f"Skipping autoscaling up checks for cluster {cluster} as per threshold {threshold}")
        return
    idle = int(os.environ.get('AUTOSCALE_MINIMUM', 2))
    if idle < 1:
        pprint(f"Skipping autoscaling down checks for cluster {cluster} as per idle {idle}")
        return
    workers = spec.get('workers', 0)
    if not os.path.exists(kubeconfig):
        pprint(f"Skipping autoscaling checks on {cluster} as kubeconfig is missing")
        return
    pprint(f"Checking non scheduled pods count on cluster {cluster}")
    os.environ['KUBECONFIG'] = kubeconfig
    currentcmd = "kubectl get node --selector='!node-role.kubernetes.io/master,node-role.kubernetes.io/worker'"
    currentcmd += " | grep ' Ready'"
    currentnodes = os.popen(currentcmd).readlines()
    if len(currentnodes) != workers:
        pprint(f"Ongoing scaling operation on cluster {cluster}")
        return
    pendingcmd = "kubectl get pods -A --field-selector=status.phase=Pending -o yaml"
    pending_pods = yaml.safe_load(os.popen(pendingcmd).read())['items']
    if len(pending_pods) > threshold:
        pprint(f"Triggering scaling up for cluster {cluster} as there are {len(pending_pods)} pending pods")
        data = dict(spec)
        workers += 1
        data['workers'] = workers
        patch.spec['workers'] = workers
        return f"Scaling up cluster {cluster} to {workers} workers"
    nodes = {}
    currentcmd = "kubectl get pod -A -o yaml"
    allpods = yaml.safe_load(os.popen(currentcmd).read())['items']
    for pod in allpods:
        nodename = pod['spec']['nodeName']
        status = pod['status']['phase']
        if status != 'Running':
            continue
        if nodename not in nodes:
            nodes[nodename] = 1
        else:
            nodes[nodename] += 1
    todelete = 0
    for node in nodes:
        if nodes[node] < idle:
            todelete += 1
    if todelete > 0:
        pprint(f"Triggering scaling down for cluster {cluster} as there are {todelete} idle nodes")
        data = dict(spec)
        patch.spec['workers'] = workers - todelete
        return f"Scaling down cluster {cluster} to {workers} workers"
