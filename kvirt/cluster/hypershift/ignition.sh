#!/bin/bash

BASE={{ namespace }}
CLUSTER={{ cluster }}
NODEPOOL={{ nodepool|default(cluster) }}
NAMESPACE=${BASE}-${CLUSTER}
CLUSTERDIR=$HOME/.kcli/clusters/$CLUSTER

SECRET=$(oc -n $NAMESPACE get secret -o jsonpath="{range .items[?(@.metadata.annotations.hypershift\.openshift\.io/nodePool==\"$BASE/$NODEPOOL\")]}{.metadata.name}{'\n'}{end}" | grep token)
oc -n $NAMESPACE get secret $SECRET -o jsonpath={'.data.payload'} | base64 -d > $CLUSTERDIR/nodepool_$NODEPOOL.ign

[ -s $CLUSTERDIR/nodepool_$NODEPOOL.ign ] || rm -f $CLUSTERDIR/nodepool_$NODEPOOL.ign
