#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kubecommon Base Class
"""

from kubernetes import client, config
import os


class Kubecommon(object):
    """

    """
    def __init__(self, token=None, ca_file=None, context=None, host='127.0.0.1', port=443, user='root', debug=False,
                 namespace=None, readwritemany=False, kubeconfig_file=None):
        self.host = host
        self.port = port
        self.user = user
        self.ca_file = ca_file
        self.readwritemany = readwritemany
        self.context = context
        self.accessmode = 'ReadWriteMany' if readwritemany else 'ReadWriteOnce'
        self.conn = 'OK'
        self.namespace = namespace
        self.contextname = None
        self.token = token
        api_client = None
        if kubeconfig_file is not None:
            kubeconfig_file = os.path.expanduser(kubeconfig_file)
            config.load_kube_config(config_file=kubeconfig_file, context=context)
        elif host is not None and port is not None and token is not None:
            configuration = client.Configuration()
            configuration.host = "https://%s:%s" % (host, port)
            configuration.api_key = {"authorization": "Bearer " + token}
            if ca_file is not None:
                configuration.ssl_ca_cert = ca_file
            else:
                configuration.verify_ssl = False
            api_client = client.ApiClient(configuration)
        elif 'KUBERNETES_PORT' in os.environ and 'KUBECONFIG' not in os.environ:
            config.load_incluster_config()
        else:
            contexts, current = config.list_kube_config_contexts()
            if context is not None:
                contexts = [entry for entry in contexts if entry['name'] == context]
                if contexts:
                    context = contexts[0]
                    contextname = context['name']
                else:
                    self.conn = None
            else:
                context = current
                contextname = current['name']
            self.contextname = contextname
            config.load_kube_config(context=contextname)
            if namespace is None and 'namespace' in context['context']:
                self.namespace = context['context']['namespace']
            if 'cluster' in context['context'] and ':' in context['context']['cluster']:
                self.host = context['context']['cluster'].split(':')[0].replace('-', '.')
        self.core = client.CoreV1Api(api_client=api_client)
        try:
            self.appsv1 = client.AppsV1Api(api_client=api_client)
        except:
            self.appsv1 = client.ExtensionsV1beta1Api(api_client=api_client)
        self.storageapi = client.StorageV1Api(api_client=api_client)
        self.batch_v1 = client.BatchV1Api(api_client=api_client)
        self.api_client = api_client
        self.debug = debug
        if self.namespace is None:
            self.namespace = 'default'
        return
