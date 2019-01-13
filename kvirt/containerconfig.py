#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvirt containerconfig class
"""


class Kcontainerconfig():
    """

    """
    def __init__(self, config):
            if config.type == 'kubevirt':
                from kvirt.kubernetes import Kubernetes
                cont = Kubernetes(host=config.k.host, user=config.k.user, port=config.k.port, token=config.k.token,
                                  ca_file=config.k.ca_file, context=config.k.context, namespace=config.k.namespace,
                                  readwritemany=config.k.readwritemany)
            elif config.type in ['kvm', 'fake']:
                from kvirt.docker import Kdocker
                cont = Kdocker(config.host)
            elif config.type == 'gcp':
                print("instantiate gke")
            elif config.type == 'aws':
                print("instantiate aks")
            self.cont = cont
