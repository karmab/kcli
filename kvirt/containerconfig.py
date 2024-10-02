# -*- coding: utf-8 -*-
"""
Kvirt containerconfig class
"""

from kvirt.common import error
import os
import sys


class Kcontainerconfig():
    """

    """
    def __init__(self, config, client=None, namespace=None):
        k8s = False
        default_k8s = False
        debug = config.debug
        insecure = config.insecure
        client = config.client if client is None else client
        if client == 'local':
            currentconfig = {'host': '127.0.0.1'}
        elif client == 'kubernetes':
            currentconfig = {}
            default_k8s = True
        else:
            currentconfig = config.ini[client]
            if 'containerclient' in currentconfig:
                if currentconfig['containerclient'] not in config.ini:
                    error("No section found for containerclient %s. Leaving" % currentconfig['containerclient'])
                    sys.exit(1)
                else:
                    currentconfig = config.ini[currentconfig['containerclient']]
        if 'type' in currentconfig and currentconfig['type'] == 'kubevirt':
            default_k8s = True
        k8s = currentconfig.get('k8s', default_k8s)
        host = currentconfig.get('host', '127.0.0.1')
        if not k8s:
            from kvirt.container import Kcontainer
            engine = currentconfig.get('containerengine', 'podman')
            cont = Kcontainer(host, engine=engine, debug=debug, insecure=insecure)
        else:
            kubeconfig_file = currentconfig.get('kubeconfig')
            if kubeconfig_file is None:
                error("Missing kubeconfig in the configuration. Leaving")
                sys.exit(1)
            elif not os.path.exists(os.path.expanduser(kubeconfig_file)):
                error("Kubeconfig file path doesn't exist. Leaving")
                sys.exit(1)
            namespace = currentconfig.get('namespace') if namespace is None else namespace
            context = currentconfig.get('context')
            readwritemany = currentconfig.get('readwritemany', False)
            from kvirt.kubernetes import Kubernetes
            cont = Kubernetes(kubeconfig_file, host=host, context=context, namespace=namespace,
                              readwritemany=readwritemany, debug=debug, insecure=insecure)
        self.cont = cont
