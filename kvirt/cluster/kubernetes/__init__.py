# -*- coding: utf-8 -*-

from kvirt.common import error
from kvirt.kubecommon import _create_resource, _delete_resource, _get_resource, _get_all_resources
from kubernetes import client
import os
from shutil import which
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Kubernetes():
    def __init__(self, kubeconfig_file, host='127.0.0.1', context=None,
                 namespace='default', readwritemany=False, debug=False, insecure=False):
        self.namespace = namespace or 'default'
        self.kubectl = which('kubectl') or which('oc')
        if self.kubectl is None:
            error("Kubectl is required. Use kcli download kubectl and put in your path")
            self.conn = None
            return
        elif context is not None:
            self.kubectl += f' --context {context}'
        os.environ['KUBECONFIG'] = os.path.expanduser(kubeconfig_file)
        self.host = host
        self.debug = debug
        self.insecure = insecure

    def create_container(self, name, image, nets=None, cmds=[], ports=[], volumes=[], environment=[], label=None,
                         overrides={}):
        """
        :param self:
        :param name:
        :param image:
        :param nets:
        :param cmds:
        :param ports:
        :param volumes:
        :param environment:
        :param label:
        :param overrides:
        :return:
        """
        kubectl = self.kubectl
        namespace = self.namespace
        if ':' not in image:
            image = f'{image}:latest'
        replicas = overrides.get('replicas', 1)
        if label is not None:
            if isinstance(label, str) and len(label.split('=')) == 2:
                key, value = label.split('=')
                labels = {key: value}
            elif isinstance(label, dict):
                labels = label
        else:
            labels = {}
        labels['kcli/plan'] = overrides.get('plan', 'kvirt')
        containers = [{'image': image, 'name': name, 'imagePullPolicy': 'IfNotPresent', 'ports': ports}]
        if cmds:
            containers[0]['command'] = cmds
        if volumes:
            vols = []
            containers[0]['volumeMounts'] = []
            for i, volume in enumerate(volumes):
                if isinstance(volume, str):
                    if len(volume.split(':')) == 2:
                        origin, destination = volume.split(':')
                        # mode = 'rw'
                    else:
                        origin, destination = volume, volume
                        # mode = 'rw'
                elif isinstance(volume, dict):
                    path = volume.get('path')
                    origin = volume.get('origin')
                    destination = volume.get('destination')
                    # mode = volume.get('mode', 'rw')
                    if (origin is None or destination is None) and path is None:
                        continue
                newvolmount = {'mountPath': destination, 'name': origin}
                containers[0]['volumeMounts'].append(newvolmount)
                newvol = {'name': origin, 'persistentVolumeClaim': {'claimName': origin}}
                vols.append(newvol)
        if ports:
            finalports = []
            for port in ports:
                finalports.append({'containerPort': port, 'name': f'port-{port}', 'protocol': 'TCP'})
            ports = finalports
        if environment:
            containers[0]['env'] = []
            for env in enumerate(environment):
                if isinstance(env, str):
                    if len(env.split(':')) == 2:
                        key, value = env.split(':')
                    else:
                        continue
                elif isinstance(env, dict):
                    if len(list(env)) == 1:
                        key = env.keys[0]
                        value = env[key]
                    else:
                        continue
                newenv = {'name': key, 'value': value}
                containers[0]['env'].append(newenv)
        deploy = {'apiVersion': 'extensions/v1beta1', 'kind': 'Deployment', 'metadata': {'labels': labels,
                                                                                         'name': name,
                                                                                         'namespace': self.namespace},
                  'spec': {'replicas': replicas, 'selector': {'matchLabels': labels},
                           'strategy': {'rollingUpdate': {'maxSurge': 1, 'maxUnavailable': 1}, 'type': 'RollingUpdate'},
                           'template': {'metadata': {'labels': labels}, 'spec': {'containers': containers,
                                                                                 'dnsPolicy': 'ClusterFirst',
                                                                                 'restartPolicy': 'Always'}}}}
        if volumes:
            deploy['spec']['template']['spec']['volumes'] = vols
        _create_resource(kubectl, deploy, namespace)

        return {'result': 'success'}

    def delete_container(self, name):
        kubectl = self.kubectl
        namespace = self.namespace
        try:
            pods = []
            rsname = None
            items = _get_all_resources(kubectl, 'rs', namespace)
            for rs in items:
                owner_references = rs['metadata']['ownerReferences']
                if owner_references is None:
                    continue
                ownerkind = owner_references[0]['kind']
                ownername = owner_references[0]['name']
                if ownerkind == 'Deployment' and ownername == name:
                    rsname = rs['metadata']['name']
                    items = _get_all_resources(kubectl, 'pod', namespace)
                    for pod in items:
                        owner_references = pod['metadata']['ownerReferences']
                        if owner_references is None:
                            continue
                        ownerkind = owner_references[0]['kind']
                        ownername = owner_references[0]['name']
                        if ownerkind == 'ReplicaSet' and ownername == rsname:
                            pods.append(pod['metadata']['name'])
            _delete_resource(kubectl, 'deploy', name, namespace)
            if rsname is not None:
                _delete_resource(kubectl, 'rs', name, rs['metadata']['name'])
            for pod in pods:
                _delete_resource(kubectl, 'pod', pod, namespace)
        except client.rest.ApiException:
            try:
                _delete_resource(kubectl, 'pod', pod, namespace)
            except client.rest.ApiException:
                error(f"Container {name} not found")
                return {'result': 'failure', 'reason': "Missing template"}
        return {'result': 'success'}

    def start_container(self, name):
        return {'result': 'success'}

    def stop_container(self, name):
        kubectl = self.kubectl
        namespace = self.namespace
        _delete_resource(kubectl, 'pod', name, namespace)
        return {'result': 'success'}

    def console_container(self, name):
        kubectl = self.kubectl
        os.system(f"{kubectl} exec -it {name} /bin/sh")
        return {'result': 'success'}

    def list_containers(self):
        kubectl = self.kubectl
        namespace = self.namespace
        containers = []
        items = _get_all_resources(kubectl, 'pod', namespace)
        for pod in items:
            name = pod['metadata']['name']
            state = pod['status']['phase']
            source = pod['spec']['containers'][0].image
            plan = ''
            labels = pod['metadata']['labels']
            if labels is not None and 'kcli/plan' in labels:
                plan = pod['metadata']['labels']['kcli/plan']
            command = pod['spec']['containers'][0]['command']
            if command is not None:
                command = ' '.join(command)
            portinfo = pod['spec']['nodeName']
            owner_references = pod['metadata']['ownerReferences']
            deploy = ''
            if owner_references is not None:
                ownerkind = owner_references[0]['kind']
                ownername = owner_references[0]['name']
                if ownerkind == 'ReplicaSet':
                    rs = _get_resource(kubectl, 'rs', ownername, namespace)
                    owner_references = rs['metadata']['ownerReferences']
                    if owner_references is not None:
                        ownerkind = owner_references[0]['kind']
                        ownername = owner_references[0]['name']
                        if ownerkind == 'Deployment':
                            deploy = ownername
            containers.append([name, state, source, plan, command, portinfo, deploy])
        return containers

    def exists_container(self, name):
        kubectl = self.kubectl
        namespace = self.namespace
        items = _get_all_resources(kubectl, 'pod', namespace)
        for pod in items:
            if pod['metadata']['name'] == name:
                return True
        return False

    def list_images(self):
        images = []
        return sorted(images)
