#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
kubernetes utilites
"""

import os
from kvirt.kubecommon import Kubecommon
from kvirt.common import pprint
from kubernetes import client
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Kubernetes():
    """

    """

    def __init__(self, host='127.0.0.1', user='root', port=443, token=None, ca_file=None, context=None,
                 namespace='default', readwritemany=False):
        Kubecommon.__init__(self, token=token, ca_file=ca_file, context=context, host=host, port=port,
                            namespace=namespace, readwritemany=readwritemany)
        self.host = host
        self.user = user
        self.port = port

    def create_container(self, name, image, nets=None, cmd=None, ports=[], volumes=[], environment=[], label=None):
        """
        :param self:
        :param name:
        :param image:
        :param nets:
        :param cmd:
        :param ports:
        :param volumes:
        :param environment:
        :param label:
        :return:
        """
        namespace = self.namespace
        if ':' not in image:
            image = '%s:latest' % image
        replicas = 2
        annotations = {'kcli/plan': 'kvirt'}
        if label is not None:
            if isinstance(label, str) and len(label.split('=')) == 2:
                key, value = label.split('=')
                labels = {key: value}
            elif isinstance(label, dict):
                labels = label
        else:
            labels = {}
        labels = {'kcli/deploy': name}
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
        deploy = {'apiVersion': 'extensions/v1beta1', 'kind': 'Deployment', 'metadata': {'annotations': annotations,
                                                                                         'labels': labels,
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
            self.v1beta.delete_namespaced_deployment(name, self.namespace, client.V1DeleteOptions())
            for rs in self.v1beta.list_namespaced_replica_set(self.namespace).items:
                if 'kcli/deploy' in rs.metadata.labels and rs.metadata.labels['kcli/deploy'] == name:
                    self.v1beta.delete_namespaced_replica_set(rs.metadata.name, self.namespace,
                                                              client.V1DeleteOptions())
            for pod in self.core.list_namespaced_pod(self.namespace).items:
                if 'kcli/deploy' in pod.metadata.labels and pod.metadata.labels['kcli/deploy'] == name:
                    self.core.delete_namespaced_pod(pod.metadata.name, self.namespace, client.V1DeleteOptions())
        except client.rest.ApiException:
            try:
                self.core.delete_namespaced_pod(name, self.namespace, client.V1DeleteOptions())
            except client.rest.ApiException:
                pprint("Container %s not found" % name)
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
            command = pod.spec.containers[0].command
            if command is not None:
                command = ' '.join(command)
            portinfo = pod.spec.node_name
            containers.append([name, state, source, plan, command, portinfo])
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
