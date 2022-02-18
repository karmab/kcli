#!/bin/bash
NAMESPACE={{ namespace }}-{{ cluster }}
CLUSTER={{ cluster }}
CLUSTERDIR={{ clusterdir }} 
SECRET=$(oc -n $NAMESPACE get secret | grep token-$CLUSTER | awk '{print $1}')
TOKEN=$(oc -n $NAMESPACE get secret $SECRET -o jsonpath={.data.token})
IP=$(oc get node -o wide | grep master | head -1 | awk '{print $6}')
PORT=$(oc -n $NAMESPACE get svc ignition-server -o jsonpath={.spec.ports[0].nodePort})
curl -k -H "Authorization: Bearer $TOKEN" https://$IP:$PORT/ignition > $CLUSTERDIR/worker.ign
