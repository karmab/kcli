#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kvirt containerconfig class
"""


class Kcontainerconfig():
    """

    """
    def __init__(self, _type='kvm', k=None):
            if _type == 'gcp':
                print("instantiate gke")
            elif _type == 'aws':
                print("instantiate aks")
            elif _type == 'kubevirt':
                from kvirt.kubernetes import Kubernetes
                cont = Kubernetes(host=k.host, user=k.user, port=k.port, token=k.token, ca_file=k.ca_file,
                                  context=k.context, namespace=k.namespace, readwritemany=k.readwritemany)
            elif _type in ['kvm', 'fake']:
                from kvirt.docker import Kdocker
                cont = Kdocker(k.host)
            self.cont = cont
