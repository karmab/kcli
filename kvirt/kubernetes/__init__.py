#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
kubernetes utilites
"""

import os
from kvirt.kubecommon import Kubecommon
from kvirt.common import error
from kubernetes import client
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Kubernetes():
    """

    """

    def __init__(self, host='127.0.0.1', user='root', port=443, token=None, ca_file=None, context=None,
                 namespace='default', readwritemany=False, debug=False, insecure=False):
        Kubecommon.__init__(self, token=token, ca_file=ca_file, context=context, host=host, port=port,
                            namespace=namespace, readwritemany=readwritemany)
        self.host = host
        self.user = user
        self.port = port
        self.debug = debug
        self.insecure = insecure

    def create_container(self, name, image, nets=None, cmd=[], ports=[], volumes=[], environment=[], label=None,
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
        namespace = self.namespace
        if ':' not in image:
            image = '%s:latest' % image
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
        if cmd is not None:
            containers[0]['command'] = cmd.split(' ')
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
                finalports.append({'containerPort': port, 'name': 'port-%s' % port, 'protocol': 'TCP'})
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
        self.v1beta.create_namespaced_deployment(namespace=namespace, body=deploy)
        return {'result': 'success'}

    def delete_container(self, name):
        """
        :param self:
        :param name:
        :return:
        """
        try:
            pods = []
            rsname = None
            for rs in self.v1beta.list_namespaced_replica_set(self.namespace).items:
                owner_references = rs.metadata.owner_references
                if owner_references is None:
                    continue
                ownerkind = owner_references[0].kind
                ownername = owner_references[0].name
                if ownerkind == 'Deployment' and ownername == name:
                    rsname = rs.metadata.name
                    for pod in self.core.list_namespaced_pod(self.namespace).items:
                        owner_references = pod.metadata.owner_references
                        if owner_references is None:
                            continue
                        ownerkind = owner_references[0].kind
                        ownername = owner_references[0].name
                        if ownerkind == 'ReplicaSet' and ownername == rsname:
                            pods.append(pod.metadata.name)
            self.v1beta.delete_namespaced_deployment(name, self.namespace, client.V1DeleteOptions())
            if rsname is not None:
                self.v1beta.delete_namespaced_replica_set(rs.metadata.name, self.namespace, client.V1DeleteOptions())
            for pod in pods:
                self.core.delete_namespaced_pod(pod, self.namespace, client.V1DeleteOptions())
        except client.rest.ApiException:
            try:
                self.core.delete_namespaced_pod(name, self.namespace, client.V1DeleteOptions())
            except client.rest.ApiException:
                error("Container %s not found" % name)
                return {'result': 'failure', 'reason': "Missing template"}
        return {'result': 'success'}

    def start_container(self, name):
        """
        :param self:
        :param name:

        :return:
        """
        return {'result': 'success'}

    def stop_container(self, name):
        """
        :param self:
        :param name:
        :return:
        """
        self.core.delete_namespaced_pod(name, self.namespace, client.V1DeleteOptions())
        return {'result': 'success'}

    def console_container(self, name):
        """
        :param self:
        :param name:
        :return:
        """
        command = "kubectl exec -it %s /bin/sh" % name
        os.system(command)
        return {'result': 'success'}

    def list_containers(self):
        """
        :param self:
        :return:
        """
        containers = []
        for pod in self.core.list_namespaced_pod(self.namespace).items:
            name = pod.metadata.name
            state = pod.status.phase
            source = pod.spec.containers[0].image
            plan = ''
            labels = pod.metadata.labels
            if labels is not None and 'kcli/plan' in labels:
                plan = pod.metadata.labels['kcli/plan']
            command = pod.spec.containers[0].command
            if command is not None:
                command = ' '.join(command)
            portinfo = pod.spec.node_name
            owner_references = pod.metadata.owner_references
            deploy = ''
            if owner_references is not None:
                ownerkind = owner_references[0].kind
                ownername = owner_references[0].name
                if ownerkind == 'ReplicaSet':
                    rs = self.v1beta.read_namespaced_replica_set(ownername, self.namespace)
                    owner_references = rs.metadata.owner_references
                    if owner_references is not None:
                        ownerkind = owner_references[0].kind
                        ownername = owner_references[0].name
                        if ownerkind == 'Deployment':
                            deploy = ownername
            containers.append([name, state, source, plan, command, portinfo, deploy])
        return containers

    def exists_container(self, name):
        """
        :param self:
        :param name:
        :return:
        """
        for pod in self.core.list_namespaced_pod(self.namespace).items:
            if pod.metadata.name == name:
                return True
        return False

    def list_images(self):
        """
        :param self:
        :return:
        """
        images = []
        return sorted(images)
