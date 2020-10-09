oc create -f install.yml
{{ 'knativeeventing'| waitcrd }}
oc create namespace knative-serving
oc create -f serving.yml
oc create namespace knative-eventing
oc create -f eventing.yml
