#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
kubernetes utilites
"""

import os
from kvirt.kubecommon import Kubecommon
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
        annotations = {'kcli/plan': 'kvirt'}
        pod = {'kind': 'Pod', 'spec': {'restartPolicy': 'Never', 'containers': [{'image': image,
                                                                                 'volumeMounts': [],
                                                                                 'name': name,
                                                                                 'env': []}],
                                       'volumes': []}, 'apiVersion': 'v1', 'metadata': {'name': name,
                                                                                        'annotations': annotations}}
        if volumes is not None:
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
                newvol = {'name': origin, 'persistentVolumeClaim': {'claimName': origin}}
                newvolmount = {'mountPath': destination, 'name': origin}
                pod['spec']['volumes'].append(newvol)
                pod['spec']['containers'][0]['volumeMounts'].append(newvolmount)
        # if ports is not None:
        #    ports = {'%s/tcp' % k: k for k in ports}
        if label is not None and isinstance(label, str) and len(label.split('=')) == 2:
            key, value = label.split('=')
            pod['metadata'][key] = value
        if environment is not None:
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
                pod['spec']['containers'][0]['env'].append(newenv)
        self.core.create_namespaced_pod(namespace, pod)
        return {'result': 'success'}

    def delete_container(self, name):
        """
        :param self:
        :param name:
        :return:
        """
        try:
            self.core.delete_namespaced_pod(name, self.namespace, client.V1DeleteOptions())
        except client.rest.ApiException as e:
            print(e)
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
