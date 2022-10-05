#!/bin/bash
NAMESPACE={{ namespace }}-{{ cluster }}
CLUSTER={{ cluster }}
BASEDOMAIN={{ base_domain }}
CLUSTERDIR={{ clusterdir }} 
SECRET=$(oc -n $NAMESPACE get secret | grep user-data-$CLUSTER | head -1 | awk '{print $1}')
TOKEN=$(oc -n $NAMESPACE get secret $SECRET -o jsonpath='{.data.value}' | base64 -d | awk -F "Bearer " '{print $2}' | awk -F "\"" '{print "Bearer " $1}')
PORT=$(oc -n $NAMESPACE get svc ignition-server -o jsonpath={.spec.ports[0].nodePort})
curl -k -H "Authorization: $TOKEN" https://api.$BASEDOMAIN:$PORT/ignition > $CLUSTERDIR/worker.ign
