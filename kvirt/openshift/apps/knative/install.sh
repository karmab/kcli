oc create -f install.yml
sleep 20
oc create namespace knative-serving
oc create -f serving.yml
oc create namespace knative-eventing
oc create -f eventing.yml
