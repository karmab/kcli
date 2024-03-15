#!/bin/bash

NAMESPACE={{ namespace }}-{{ cluster }}
CLUSTER={{ cluster }}
CLUSTERDIR={{ clusterdir }} 
SECRET=$(oc -n $NAMESPACE get secret | grep user-data-$CLUSTER | head -1 | awk '{print $1}')
TOKEN=$(oc -n $NAMESPACE get secret $SECRET -o jsonpath='{.data.value}' | base64 -d | awk -F "Bearer " '{print $2}' | awk -F "\"" '{print "Bearer " $1}')

{% if nodeport|default(False) %}
IP=$(oc get node -o wide --selector='node-role.kubernetes.io/master' | grep -v NAME|  head -1 | awk '{print $6}')
PORT=$(oc -n $NAMESPACE get svc ignition-server-proxy -o jsonpath={.spec.ports[0].nodePort})
curl -k -H "Authorization: $TOKEN" https://$IP:$PORT/ignition > $CLUSTERDIR/nodepool.ign
{% else %}
MANAGEMENT_INGRESS_DOMAIN={{ management_ingress_domain }}
curl -k -H "Authorization: $TOKEN" https://ignition-server-$NAMESPACE.$MANAGEMENT_INGRESS_DOMAIN/ignition > $CLUSTERDIR/nodepool.ign
{% endif %}

if [ ! -s $CLUSTERDIR/nodepool.ign ] || [ "$(grep 'Token not found' $CLUSTERDIR/nodepool.ign)" != "" ] || [ "$(grep '503 Service Unavailable' $CLUSTERDIR/nodepool.ign)" != "" ] ; then
  rm -f $CLUSTERDIR/nodepool.ign
fi
