#!/usr/bin/env bash
export IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
export TILLER_NAMESPACE=helm
export MONOCULAR_API_URL="monocular-api.$IP.xip.io"
export MONOCULAR_UI_URL="monocular.$IP.xip.io"
export MONOCULAR_NAMESPACE="monocular"
oc project $MONOCULAR_NAMESPACE
oc adm policy add-scc-to-user anyuid -z default -n $MONOCULAR_NAMESPACE
sleep 20
helm repo add monocular https://kubernetes-helm.github.io/monocular
helm install --name monocular --set api.config.releasesEnabled=true,ui.backendHostname=http://$MONOCULAR_API_URL,api.config.cors.allowed_origins={http://$MONOCULAR_UI_URL},api.config.tillerNamespace=helm,mongodb.persistence.enabled=false monocular/monocular
oc expose svc monocular-monocular-api --hostname=$MONOCULAR_API_URL
oc expose svc monocular-monocular-ui --hostname=$MONOCULAR_UI_URL
