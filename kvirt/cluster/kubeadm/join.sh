#!/usr/bin/env bash

API_IP={{ "api.%s.%s" % (cluster, domain) if config_type in ['aws', 'gcp', 'ibm'] else "api.%s.sslip.io" % api_ip.replace('.', '-').replace(':', '-') if sslip else api_ip }}
TOKEN={{ token }}
CTLPLANES="{{ '--control-plane --certificate-key %s' % cert_key if 'ctlplane' in name else '' }}"

kubeadm join ${API_IP}:6443 --token $TOKEN --discovery-token-unsafe-skip-ca-verification $CTLPLANES
