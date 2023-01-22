#!/bin/bash

NAMESPACE={{ namespace }}-{{ cluster }}
NODEPOOL={{ nodepool }}
CLUSTERDIR={{ clusterdir }} 
SECRET=$(oc -n $NAMESPACE get secret | grep user-data-$NODEPOOL | head -1 | awk '{print $1}')
TOKEN=$(oc -n $NAMESPACE get secret $SECRET -o jsonpath='{.data.value}' | base64 -d | awk -F "Bearer " '{print $2}' | awk -F "\"" '{print "Bearer " $1}')

{% if nodeport|default(False) %}
IP=$(oc get node -o wide --selector='node-role.kubernetes.io/master' | grep -v NAME|  head -1 | awk '{print $6}')
PORT=$(oc -n $NAMESPACE get svc ignition-server -o jsonpath={.spec.ports[0].nodePort})
curl -k -H "Authorization: $TOKEN" https://$IP:$PORT/ignition > $CLUSTERDIR/$NODEPOOL.ign
{% else %}
MANAGEMENT_INGRESS_DOMAIN={{ management_ingress_domain }}
curl -k -H "Authorization: $TOKEN" https://ignition-server-$NAMESPACE.$MANAGEMENT_INGRESS_DOMAIN/ignition > $CLUSTERDIR/$NODEPOOL.ign
{% endif %}
