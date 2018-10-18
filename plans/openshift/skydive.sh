oc new-project skydive
oc adm policy add-scc-to-user privileged -z default -n skydive
oc create -f https://raw.githubusercontent.com/skydive-project/skydive/master/contrib/kubernetes/skydive.yaml
